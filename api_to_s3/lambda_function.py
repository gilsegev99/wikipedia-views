
import boto3
import requests
import os
import logging
import json
from datetime import datetime, timedelta, timezone


VIEWS_BASE_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/"
WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "Page views analysis (https://github.com/gilsegev99)"}

yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y/%m/%d')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")

def get_pageviews(datestring):

    response = requests.get(url=f"{VIEWS_BASE_URL}{datestring}", headers=HEADERS)

    if response.ok:
        response_json = response.json()
    else:
        response_json = None
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
    return response_json


def lambda_handler(event, context):

    views_data = get_pageviews(yesterday)
    views_key = f"raw/views_data/{yesterday}.json"

    if views_data is not None:
        try:
            s3_client.put_object(
                Bucket=os.getenv("BUCKET"),
                Key=views_key,
                Body=json.dumps(views_data)
            )

            logger.info(f"Successfully uploaded {yesterday} views data to S3.")
        except Exception as e:
            logger.error(f"Failed to upload {yesterday} views data to S3: {str(e)}")
            raise
    
    article_titles = [article['article'] for article in views_data['items'][0]['articles']]

    for article in article_titles:
        article_categories = get_categories(article)
        cat_key = f"raw/category_data/{article}.json"

        if article_categories is not None:
            try:
                s3_client.put_object(
                    Bucket=os.getenv("BUCKET"),
                    Key=cat_key,
                    Body=json.dumps(article_categories)
                )
                logger.info(f"Successfully uploaded {article} categories data to S3.")
            except Exception as e:
                logger.error(f"Failed to upload {article} categories data to S3: {str(e)}")
                raise

    return {
            "statusCode": 200,
            "message": f"{yesterday} data processed successfully"
        }
