import json
import os
import boto3
from aws_lambda_powertools import Logger, Tracer
from PySuiteCRM.SuiteCRM import SuiteCRM

logger = Logger()
tracer = Tracer()
secrets_manager = boto3.client("secretsmanager")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """Creates a lead in SuiteCRM."""
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

    try:
        # Change to /tmp directory for file operations
        os.chdir('/tmp')
        
        crm = SuiteCRM(
            url=crm_credentials["url"],
            client_id=crm_credentials["client_id"],
            client_secret=crm_credentials["client_secret"],
        )
    except Exception as e:
        logger.exception("Error connecting to SuiteCRM")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 500,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": "Error connecting to CRM"})
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
                lead_data = properties.get('lead_data')
            else:
                # Handle direct JSON format
                body_data = json.loads(request_body) if isinstance(request_body, str) else request_body
                lead_data = body_data.get('lead_data')
        else:
            # Fallback for direct invocation
            lead_data = event.get("lead_data")
            
        if not lead_data:
            raise KeyError("lead_data not found in event")
            
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Could not parse lead_data from event: {e}")
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
        lead = crm.leads.create(lead_data)
        logger.info(f"Created lead: {lead['id']}")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"id": lead.get('id'), "status": "created"})
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
                    "body": json.dumps({"error": "Error creating lead"})
                }
            }
        }
