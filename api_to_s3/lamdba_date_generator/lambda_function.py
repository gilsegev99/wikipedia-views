import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    start = datetime.fromisoformat(event["start_date"])
    end = datetime.fromisoformat(event["end_date"])

    dates = []
    current = start

    while current <= end:
        dates.append({"date": current.strftime("%Y-%m-%d")})
        current += timedelta(days=1)

    return {
        "dates": dates
    }
