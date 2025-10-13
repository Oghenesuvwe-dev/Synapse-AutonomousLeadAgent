import requests
import boto3
from bs4 import BeautifulSoup
import os
import json
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()
s3 = boto3.client("s3")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """Fetches a URL provided in the event, extracts text, stores raw HTML to S3,
    and returns a short text summary (first N chars)."""
    logger.info("Received event: %s", json.dumps(event))
    
    try:
        # Handle Bedrock Agent event format
        if 'requestBody' in event and 'content' in event['requestBody']:
            # Parse the request body from Bedrock Agent
            request_body = event['requestBody']['content']['application/json']
            if 'properties' in request_body:
                # Handle properties format
                properties = {prop['name']: prop['value'] for prop in request_body['properties']}
                url = properties.get('url')
            else:
                # Handle direct JSON format
                body_data = json.loads(request_body) if isinstance(request_body, str) else request_body
                url = body_data.get('url')
        else:
            # Fallback for direct invocation
            url = event.get('url')
            
        if not url:
            raise KeyError("URL not found in event")
            
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Could not parse URL from event: {e}")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 400,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": "Could not parse URL from event"})
                }
            }
        }

    bucket = os.environ.get("SCRAPER_BUCKET")
    logger.info(f"Fetching URL: {url}")

    bucket = os.environ.get("SCRAPER_BUCKET")
    logger.info(f"Fetching URL: {url}")

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.exception(f"Error fetching URL: {url}")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 500,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": f"Error fetching URL: {e}"})
                }
            }
        }

    html = resp.text
    key = f"scraped/{hash(url)}.html"
    if bucket:
        try:
            s3.put_object(Bucket=bucket, Key=key, Body=html.encode("utf-8"))
            logger.info(f"Saved HTML to s3://{bucket}/{key}")
        except Exception as e:
            logger.exception(f"Error saving to S3: {e}")
            return {
                "actionGroup": event.get('actionGroup', ''),
                "apiPath": event.get('apiPath', ''),
                "httpMethod": event.get('httpMethod', ''),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({"error": f"Error saving to S3: {e}"})
                    }
                }
            }

    try:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        summary = text[:800]
    except Exception as e:
        logger.exception("Error parsing HTML")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 500,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": f"Error parsing HTML: {e}"})
                }
            }
        }

    response = {
        "actionGroup": event.get('actionGroup', ''),
        "apiPath": event.get('apiPath', ''),
        "httpMethod": event.get('httpMethod', ''),
        "httpStatusCode": 200,
        "responseBody": {
            "application/json": {
                "body": json.dumps({"summary": summary, "s3_key": key})
            }
        }
    }
    return response
