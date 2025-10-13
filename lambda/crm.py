import json
import os
import boto3
import requests
import re
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()
secrets_manager = boto3.client("secretsmanager")


def get_suitecrm_token(url, client_id, client_secret):
    """Get OAuth2 access token from SuiteCRM."""
    token_url = f"{url.rstrip('/')}/Api/access_token"
    
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    logger.info(f"Requesting token from: {token_url}")
    
    response = requests.post(
        token_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("access_token")
    else:
        logger.error(f"Token request failed: {response.status_code} - {response.text}")
        raise Exception(f"Failed to get access token: {response.status_code}")


def create_suitecrm_lead(url, access_token, lead_data):
    """Create a lead in SuiteCRM using direct API calls."""
    api_url = f"{url.rstrip('/')}/Api/V8/module"
    
    # Format lead data for SuiteCRM API
    suitecrm_lead = {
        "data": {
            "type": "Leads",
            "attributes": {
                "first_name": lead_data.get("first_name", ""),
                "last_name": lead_data.get("last_name", ""),
                "email1": lead_data.get("email1", ""),
                "account_name": lead_data.get("account_name", ""),
                "description": lead_data.get("description", ""),
                "lead_source": "Synapse AI Agent",
                "status": "New"
            }
        }
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    logger.info(f"Creating lead at: {api_url}")
    logger.info(f"Lead data: {json.dumps(suitecrm_lead, indent=2)}")
    
    response = requests.post(
        api_url,
        json=suitecrm_lead,
        headers=headers,
        timeout=30
    )
    
    if response.status_code in [200, 201]:
        result = response.json()
        logger.info(f"Lead created successfully: {result}")
        return result.get("data", {})
    else:
        logger.error(f"Lead creation failed: {response.status_code} - {response.text}")
        raise Exception(f"Failed to create lead: {response.status_code} - {response.text}")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """Creates a lead in SuiteCRM - REAL IMPLEMENTATION with direct API calls."""
    logger.info("Received event: %s", json.dumps(event))

    try:
        secret = secrets_manager.get_secret_value(SecretId=os.environ.get("SUITECRM_SECRET_ID"))
        crm_credentials = json.loads(secret["SecretString"])
    except Exception as e:
        logger.exception("Error getting SuiteCRM credentials from Secrets Manager")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 500,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": "Error getting credentials"})
                }
            }
        }

    # Parse lead data from Bedrock Agent event format
    try:
        if 'requestBody' in event and 'content' in event['requestBody']:
            request_body = event['requestBody']['content']['application/json']
            if 'properties' in request_body:
                # Handle properties format
                properties = {prop['name']: prop['value'] for prop in request_body['properties']}
                lead_data_str = properties.get('lead_data')
                
                # Handle both JSON and XML formats
                if isinstance(lead_data_str, str):
                    if lead_data_str.strip().startswith('<'):
                        # Parse XML format
                        import re
                        lead_data = {}
                        # Extract data from XML tags
                        patterns = {
                            'first_name': r'<first_name>(.*?)</first_name>',
                            'last_name': r'<last_name>(.*?)</last_name>',
                            'email1': r'<email1>(.*?)</email1>',
                            'account_name': r'<account_name>(.*?)</account_name>',
                            'description': r'<description>(.*?)</description>'
                        }
                        for field, pattern in patterns.items():
                            match = re.search(pattern, lead_data_str, re.DOTALL)
                            if match:
                                lead_data[field] = match.group(1).strip()
                        logger.info(f"Parsed XML lead data: {lead_data}")
                    else:
                        # Parse JSON string
                        lead_data = json.loads(lead_data_str)
                else:
                    lead_data = lead_data_str
            else:
                # Handle direct JSON format
                body_data = json.loads(request_body) if isinstance(request_body, str) else request_body
                lead_data = body_data.get('lead_data')
        else:
            # Fallback for direct invocation
            lead_data = event.get("lead_data")
            
        if not lead_data:
            raise KeyError("lead_data not found in event")
            
    except (KeyError, IndexError, json.JSONDecodeError, Exception) as e:
        logger.error(f"Could not parse lead_data from event: {e}")
        logger.error(f"Event content: {json.dumps(event, default=str)}")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 400,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": "missing lead_data"})
                }
            }
        }

    try:
        # Get OAuth2 access token
        access_token = get_suitecrm_token(
            crm_credentials["url"],
            crm_credentials["client_id"],
            crm_credentials["client_secret"]
        )
        
        # Create lead using direct API calls
        lead = create_suitecrm_lead(
            crm_credentials["url"],
            access_token,
            lead_data
        )
        
        lead_id = lead.get('id', 'unknown')
        logger.info(f"Created real SuiteCRM lead: {lead_id}")
        
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({
                        "id": lead_id, 
                        "status": "created",
                        "real_crm": True,
                        "lead_name": f"{lead_data.get('first_name', '')} {lead_data.get('last_name', '')}",
                        "company": lead_data.get('account_name', ''),
                        "email": lead_data.get('email1', ''),
                        "suitecrm_url": crm_credentials["url"]
                    })
                }
            }
        }
    except Exception as e:
        logger.exception("Error creating lead in SuiteCRM")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 500,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": f"Error creating lead: {str(e)}"})
                }
            }
        }
