import boto3
import json
import pyarrow as pa
import pyarrow.parquet as pq
import io
import logging
from typing import Union, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Configuration ────────────────────────────────────────────────────────────
BUCKET = "wikimedia-data-bucket"
SOURCE_PREFIX = "raw/category_data/"
DEST_KEY      = "processed/category_data/category_data.parquet"

MAX_WORKERS        = 10    # parallel S3 read threads
FILES_PER_PARTITION = 10_000  # write a new parquet part every N files (memory control)
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

s3 = boto3.client("s3")


def list_all_keys(bucket: str, prefix: str) -> list[str]:
    """Return every key under bucket/prefix using pagination."""
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    log.info("Found %d keys", len(keys))
    return keys


def parse_json(raw: bytes) -> Union[Dict, None]:
    """Extract (title, categories) from one raw JSON file."""
    try:
        data  = json.loads(raw)
        query = data.get("query", {})

        # "title" column: normalized[0]["from"]
        normalized = query.get("normalized", [])
        title = normalized[0]["from"] if normalized else None

        # "categories" column: list of category titles from the single page
        pages = query.get("pages", {})
        if not pages:
            return None
        page = next(iter(pages.values()))   # only one page per file
        categories = [c["title"] for c in page.get("categories", [])]

        if title is None:
            return None
        return {"title": title, "categories": categories}
    except Exception as exc:
        log.warning("Parse error: %s", exc)
        return None


def fetch_and_parse(key: str) -> Union[Dict, None]:
    """Download one S3 object and parse it."""
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        return parse_json(obj["Body"].read())
    except Exception as exc:
        log.warning("Failed to fetch %s: %s", key, exc)
        return None


def rows_to_parquet_bytes(rows: list[dict]) -> bytes:
    """Serialise a list of row dicts to an in-memory Parquet file."""
    schema = pa.schema([
        pa.field("title",      pa.string()),
        pa.field("categories", pa.list_(pa.string())),
    ])
    titles     = [r["title"]      for r in rows]
    categories = [r["categories"] for r in rows]
    table = pa.table({"title": titles, "categories": categories}, schema=schema)

    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()


def upload_parquet(data: bytes, dest_key: str) -> None:
    s3.put_object(Bucket=BUCKET, Key=dest_key, Body=data)
    log.info("Uploaded s3://%s/%s  (%d bytes)", BUCKET, dest_key, len(data)) #String formatting more performant in logging


def main():
    keys = list_all_keys(BUCKET, SOURCE_PREFIX)

    rows        = []
    part_index  = 0
    total_rows  = 0
    failed      = 0

    # Build the base key name (strip .parquet suffix so we can add part numbers)
    base_key = DEST_KEY[:-len(".parquet")] if DEST_KEY.endswith(".parquet") else DEST_KEY

    def flush(rows: list[dict], part: int) -> str:
        """Write accumulated rows to S3 as one Parquet part."""
        suffix   = f"_part{part:04d}.parquet"
        dest_key = base_key + suffix
        upload_parquet(rows_to_parquet_bytes(rows), dest_key)
        return dest_key

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_and_parse, k): k for k in keys}
        done    = 0

        for future in as_completed(futures): #as_completed() means tasks are processed as they complete
            done += 1
            result = future.result()

            if result is None:
                failed += 1
            else:
                rows.append(result)

            # Flush to S3 every FILES_PER_PARTITION rows to keep memory bounded
            if len(rows) >= FILES_PER_PARTITION:
                flush(rows, part_index)
                total_rows += len(rows)
                part_index += 1
                rows = []

            if done % 10_000 == 0:
                log.info("Progress: %d / %d files processed", done, len(keys))

    # Final partial batch
    if rows:
        flush(rows, part_index)
        total_rows += len(rows)
        part_index += 1

    log.info(
        "Done. %d parquet part(s) written, %d rows total, %d files failed/skipped.",
        part_index, total_rows, failed,
    )

main()