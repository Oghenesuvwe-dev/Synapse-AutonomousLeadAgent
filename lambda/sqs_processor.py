import json
import boto3
import os
from aws_lambda_powertools import Logger

logger = Logger()
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")
ses = boto3.client('ses')

def handler(event, context):
    """Process leads from SQS queue"""
    
    for record in event['Records']:
        try:
            # Parse lead data from SQS message
            lead_data = json.loads(record['body'])
            
            # Process lead with full workflow
            result = process_lead_complete(lead_data['text'])
            
            # Send notifications
            send_notifications(result, lead_data['text'])
            
            logger.info(f"Successfully processed lead: {lead_data['text'][:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to process SQS record: {str(e)}")
            # Message will go to DLQ after retries

def process_lead_complete(lead_text):
    """Complete lead processing workflow"""
    
    # Invoke Bedrock agent
    response = bedrock_agent_runtime.invoke_agent(
        agentId=os.environ['AGENT_ID'],
        agentAliasId=os.environ['AGENT_ALIAS_ID'],
        sessionId=f"sqs-{hash(lead_text) % 10000}",
        inputText=lead_text
    )
    
    # Process response
    completion = ""
    for event_chunk in response.get("completion", []):
        if "chunk" in event_chunk:
            chunk = event_chunk["chunk"]
            if "bytes" in chunk:
                completion += chunk["bytes"].decode()
    
    return completion or "Lead processed via SQS"

def send_notifications(result, original_content):
    """Send email and Slack notifications"""
    
    # Email notification
    try:
        ses.send_email(
            Source=os.environ['SES_FROM_EMAIL'],
            Destination={'ToAddresses': [os.environ['SES_TO_EMAIL']]},
            Message={
                'Subject': {'Data': 'Lead Processed via SQS Queue'},
                'Body': {'Text': {'Data': f"Result: {result}\n\nOriginal: {original_content}"}}
            }
        )
        logger.info("Email sent successfully")
    except Exception as e:
        logger.error(f"Email failed: {str(e)}")
    
    # Slack notification
    try:
        import requests
        webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        if webhook_url:
            requests.post(webhook_url, json={
                'text': f"🎯 Lead Processed (SQS)\n\nResult: {result[:100]}...\n\nOriginal: {original_content[:100]}..."
            }, timeout=10)
            logger.info("Slack sent successfully")
    except Exception as e:
        logger.error(f"Slack failed: {str(e)}")