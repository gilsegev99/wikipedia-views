import sys
import boto3
import json
import pyarrow as pa
import pyarrow.parquet as pq

bucket = "wikimedia-data-bucket"
prefix = "raw/category_data/"

s3 = boto3.client('s3')
paginator = s3.get_paginator('list_objects_v2')
page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)

titles, categories = [], []
for page in page_iterator:
    for obj in page.get('Contents', []):
        response = s3.get_object(Bucket=bucket, Key=obj["Key"])
        data = json.loads(response["Body"].read())
        titles.append(data["query"].get("normalized", [{}])[0].get("from", "UNKNOWN_TITLE"))

        article_data = data["query"]["pages"]
        for item in article_data.values():
            categories.append([c["title"] for c in item.get("categories", [])])

        print(f"{titles[-1]} categories read in")

table = pa.table([titles, categories], names=["article_title", "article_categories"])

output_file = "/tmp/category_data.parquet"
pq.write_table(table, output_file, compression="SNAPPY")
s3.upload_file(output_file, bucket, "processed/category_data/category_data.parquet")