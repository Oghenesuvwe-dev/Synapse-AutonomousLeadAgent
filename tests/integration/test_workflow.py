import os
import requests
import boto3
import time
import pytest
from moto import mock_aws

API_ENDPOINT = os.environ.get("API_ENDPOINT")
SCRAPER_BUCKET = os.environ.get("SCRAPER_BUCKET")
AWS_REGION = os.environ.get("AWS_REGION")
SUITECRM_SECRET_ID = "synapse/dev/suitecrm"


@pytest.mark.skipif(not API_ENDPOINT, reason="API_ENDPOINT environment variable not set")
@pytest.mark.skipif(not SCRAPER_BUCKET, reason="SCRAPER_BUCKET environment variable not set")
@pytest.mark.skipif(not AWS_REGION, reason="AWS_REGION environment variable not set")
def test_end_to_end_flow_with_url():
    """Tests the end-to-end flow from webhook to agent to scraper to S3."""
    s3 = boto3.client("s3", region_name=AWS_REGION)

    # A known URL for a simple page
    url_to_scrape = "https://example.com/"

    # Send a POST request to the webhook
    response = requests.post(API_ENDPOINT, json={"text": f"New lead from {url_to_scrape}"})
    assert response.status_code == 200

    # Wait for the agent and scraper to run
    time.sleep(10)

    # Check if the scraped file exists in S3
    file_key = f"scraped/{hash(url_to_scrape)}.html"
    try:
        response = s3.get_object(Bucket=SCRAPER_BUCKET, Key=file_key)
        content = response["Body"].read().decode("utf-8")
        assert "Example Domain" in content
    except Exception as e:
        pytest.fail(f"File not found in S3 or content is incorrect: {e}")

    # Clean up the file from S3
    s3.delete_object(Bucket=SCRAPER_BUCKET, Key=file_key)


@pytest.mark.skipif(not API_ENDPOINT, reason="API_ENDPOINT environment variable not set")
@pytest.mark.skipif(not SCRAPER_BUCKET, reason="SCRAPER_BUCKET environment variable not set")
@pytest.mark.skipif(not AWS_REGION, reason="AWS_REGION environment variable not set")
def test_end_to_end_flow_no_url():
    """Tests that the agent does not scrape when no URL is provided."""
    s3 = boto3.client("s3", region_name=AWS_REGION)

    # Send a POST request to the webhook without a URL
    response = requests.post(API_ENDPOINT, json={"text": "New lead from Acme Corp"})
    assert response.status_code == 200

    # Wait for the agent to run
    time.sleep(10)

    # Check that no file was created in S3
    response = s3.list_objects_v2(Bucket=SCRAPER_BUCKET, Prefix="scraped/")
    assert "Contents" not in response


@mock_aws
@pytest.mark.skipif(not API_ENDPOINT, reason="API_ENDPOINT environment variable not set")
def test_end_to_end_flow_crm(mocker):
    """Tests the end-to-end flow from webhook to agent to CRM."""
    secretsmanager = boto3.client("secretsmanager", region_name=AWS_REGION)
    secretsmanager.create_secret(
        Name=SUITECRM_SECRET_ID,
        SecretString='{"url": "https://example.com", "client_id": "test", "client_secret": "test"}',
    )

    mock_suite_crm = mocker.patch("pysuitecrm.SuiteCRM")

    # Send a POST request to the webhook that should trigger a CRM action
    response = requests.post(
        API_ENDPOINT, json={"text": "New lead: John Smith from Acme Corp. Email: john.smith@acme.com"}
    )
    assert response.status_code == 200

    # Wait for the agent and crm lambda to run
    time.sleep(10)

    # Assert that the SuiteCRM client was called with the correct data
    mock_suite_crm.return_value.leads.create.assert_called_with(
        {
            "first_name": "John",
            "last_name": "Smith",
            "email1": "john.smith@acme.com",
            "account_name": "Acme Corp",
        }
    )
