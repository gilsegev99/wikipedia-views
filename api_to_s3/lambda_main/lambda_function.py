
import boto3
import botocore
import requests
import os
import logging
import json
from datetime import datetime, timedelta, timezone


VIEWS_BASE_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/"
WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": os.environ["USER_AGENT_STRING"]}

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
S3_BUCKET = os.environ["BUCKET_NAME"]

def get_pageviews(datestring):
    response = requests.get(url=f"{VIEWS_BASE_URL}{datestring}", headers=HEADERS)

    if response.ok:
        response_json = response.json()
    else:
        response_json = None
        logger.info(f"Page views API call returned None for {datestring}.")
    return response_json

def get_categories(article):
    params = {
        'action': 'query',
        'titles': article,
        'prop': 'categories',
        'format': 'json',
        'cllimit': 'max'
    }

    response = requests.get(url=f"{WIKIPEDIA_BASE_URL}", headers=HEADERS, params=params)

    if response.ok:
        response_json = response.json()
    else:
        response_json = None
        logger.info(f"Categories API call returned None for {article}.")
    return response_json

def check_key_exists_and_up_to_date(bucket, key):
    try:
        one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
        s3_client.head_object(Bucket=bucket, Key=key, IfModifiedSince=one_year_ago)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            logger.info(f"Object '{key}' not found in {bucket}")
            return False
        elif e.response["Error"]["Code"] == "304":
            logger.info(f"Object '{key}' contains old data")
            return False
        else:
            logger.error(f"Error {e.response["Error"]["Code"]} checking for {key}: {e.response["Error"]["Message"]}")
            raise
    else:
        return True
    
def put_data_in_s3(data, key:str, object:str):
    if data is not None:
        try:
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=json.dumps(data)
            )
            logger.info(f"Successfully uploaded {object} views data to S3.")
        except Exception as e:
            logger.error(f"Failed to upload {object} views data to S3: {str(e)}")
            raise
    
def lambda_handler(event, context):
    date_str = event.get("date")

    if not date_str:
        # Default to UTC "yesterday" if not provided
        date = datetime.now(timezone.utc) - timedelta(days=1)
    else:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD."
            )
    
    date_dash_fmt = date.strftime('%Y-%m-%d')
    date_slash_fmt = date.strftime('%Y/%m/%d')

    views_key = f"raw/views_data/{date_dash_fmt}.json"

    if check_key_exists_and_up_to_date(S3_BUCKET, views_key):
        return {
            "statusCode": 200,
            "message": f"{date_slash_fmt} data already exists"
        }
    else:
        views_data = get_pageviews(date_slash_fmt)

        if views_data:

            put_data_in_s3(views_data, views_key, date_slash_fmt)
            
            article_titles = [article['article'] for article in views_data['items'][0]['articles']]

            for article in article_titles:        
                cat_key = f"raw/category_data/{article}.json"
                key_exists = check_key_exists_and_up_to_date(S3_BUCKET, cat_key)

                if not key_exists:
                    article_categories = get_categories(article)

                    put_data_in_s3(article_categories, cat_key, article)

            return {
                    "statusCode": 200,
                    "message": f"{date_slash_fmt} data processed successfully"
                }        
        else:
            return {
                "statusCode": 204,
                "message": f"Request for {date_slash_fmt} data returned None"
            }
