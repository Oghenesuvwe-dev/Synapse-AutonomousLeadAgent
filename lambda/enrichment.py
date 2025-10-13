import json
import os
import boto3
import requests
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()
secrets_manager = boto3.client("secretsmanager")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """Enriches lead data using Hunter.io and other APIs."""
    logger.info("Received event: %s", json.dumps(event))

    try:
        # Parse enrichment request from Bedrock Agent event format
        if 'requestBody' in event and 'content' in event['requestBody']:
            request_body = event['requestBody']['content']['application/json']
            if 'properties' in request_body:
                properties = {prop['name']: prop['value'] for prop in request_body['properties']}
                domain = properties.get('domain')
                email = properties.get('email')
            else:
                body_data = json.loads(request_body) if isinstance(request_body, str) else request_body
                domain = body_data.get('domain')
                email = body_data.get('email')
        else:
            domain = event.get("domain")
            email = event.get("email")
            
        if not domain:
            raise KeyError("domain not found in event")
            
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Could not parse enrichment request from event: {e}")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 400,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": "missing domain parameter"})
                }
            }
        }

    try:
        # Get Hunter.io API key from Secrets Manager
        secret = secrets_manager.get_secret_value(SecretId="Synapse/Enrichment")
        enrichment_credentials = json.loads(secret["SecretString"])
        hunter_api_key = enrichment_credentials.get("hunter_api_key")
        
        enriched_data = {}
        
        # Hunter.io domain search
        if hunter_api_key:
            try:
                hunter_response = requests.get(
                    "https://api.hunter.io/v2/domain-search",
                    params={
                        "domain": domain,
                        "api_key": hunter_api_key,
                        "limit": 5
                    },
                    timeout=10
                )
                
                if hunter_response.status_code == 200:
                    hunter_data = hunter_response.json()
                    enriched_data["hunter_data"] = {
                        "organization": hunter_data.get("data", {}).get("organization"),
                        "emails_found": len(hunter_data.get("data", {}).get("emails", [])),
                        "additional_contacts": hunter_data.get("data", {}).get("emails", [])[:3]
                    }
                    logger.info(f"Hunter.io enrichment successful for {domain}")
                else:
                    logger.warning(f"Hunter.io API returned status {hunter_response.status_code}")
                    
            except Exception as e:
                logger.error(f"Hunter.io enrichment failed: {str(e)}")
        
        # Email verification if email provided
        if email and hunter_api_key:
            try:
                verify_response = requests.get(
                    "https://api.hunter.io/v2/email-verifier",
                    params={
                        "email": email,
                        "api_key": hunter_api_key
                    },
                    timeout=10
                )
                
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    enriched_data["email_verification"] = {
                        "result": verify_data.get("data", {}).get("result"),
                        "score": verify_data.get("data", {}).get("score"),
                        "deliverable": verify_data.get("data", {}).get("result") in ["deliverable", "risky"]
                    }
                    logger.info(f"Email verification successful for {email}")
                    
            except Exception as e:
                logger.error(f"Email verification failed: {str(e)}")
        
        # Add basic domain intelligence
        enriched_data["domain_info"] = {
            "domain": domain,
            "tld": domain.split('.')[-1] if '.' in domain else None,
            "is_business_domain": not any(domain.endswith(tld) for tld in ['.gmail.com', '.yahoo.com', '.hotmail.com', '.outlook.com'])
        }
        
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({
                        "enriched_data": enriched_data,
                        "status": "success",
                        "domain": domain
                    })
                }
            }
        }
        
    except Exception as e:
        logger.exception("Error during data enrichment")
        return {
            "actionGroup": event.get('actionGroup', ''),
            "apiPath": event.get('apiPath', ''),
            "httpMethod": event.get('httpMethod', ''),
            "httpStatusCode": 500,
            "responseBody": {
                "application/json": {
                    "body": json.dumps({"error": "Error during enrichment"})
                }
            }
        }