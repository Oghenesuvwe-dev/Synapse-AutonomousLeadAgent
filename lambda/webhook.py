import json
import os
import boto3
import re
from typing import Dict, Any, Optional, Tuple
from aws_lambda_powertools import Logger, Tracer
from urllib.parse import unquote_plus

logger = Logger()
tracer = Tracer()
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """Enhanced webhook handler supporting multiple trigger types (email/Slack/generic)."""
    logger.info("Received event: %s", json.dumps(event, default=str))

    try:
        # Determine trigger type and extract content
        trigger_type, processed_content = determine_trigger_type_and_extract_content(event)
        logger.info(f"Detected trigger type: {trigger_type}")
        
        if not processed_content:
            logger.warning("No content extracted from webhook payload")
            return {"statusCode": 400, "body": "No content found in webhook payload"}

        # Get agent configuration
        agent_id = os.environ.get("AGENT_ID")
        agent_alias_id = os.environ.get("AGENT_ALIAS_ID")

        if not agent_id or not agent_alias_id:
            logger.error("Agent ID or Alias ID not configured")
            return {"statusCode": 500, "body": "Agent not configured"}

        # Generate unique session ID based on trigger type and content
        session_id = generate_session_id(trigger_type, event)
        
        logger.info(f"Invoking agent {agent_id}/{agent_alias_id} with session {session_id}")
        
        # Invoke Bedrock agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=processed_content,
        )

        # Process agent response
        completion = ""
        for event_chunk in response.get("completion", []):
            if "chunk" in event_chunk:
                chunk = event_chunk["chunk"]
                if "bytes" in chunk:
                    completion += chunk["bytes"].decode()

        logger.info(f"Agent response: {completion}")

        # Format response based on trigger type
        formatted_response = format_response_for_trigger(trigger_type, completion, processed_content)
        
        return {
            "statusCode": 200, 
            "body": json.dumps(formatted_response) if isinstance(formatted_response, dict) else formatted_response,
            "headers": {
                "Content-Type": "application/json" if trigger_type == "slack" else "text/plain"
            }
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": f"Error processing webhook: {str(e)}"
        }


def determine_trigger_type_and_extract_content(event: Dict[str, Any]) -> Tuple[str, str]:
    """Determine the trigger type and extract relevant content."""
    
    # Check path to determine trigger type
    path = event.get("path", "")
    if "/webhook/email" in path:
        return "email", extract_email_content(event)
    elif "/webhook/slack" in path:
        return "slack", extract_slack_content(event)
    else:
        return "generic", extract_generic_content(event)


def extract_email_content(event: Dict[str, Any]) -> str:
    """Extract content from email webhook payload."""
    try:
        body = event.get("body", "")
        if isinstance(body, str):
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                # Handle URL-encoded form data
                payload = parse_form_data(body)
        else:
            payload = body or {}

        # Common email webhook formats
        content_fields = [
            "text", "plain", "body-plain", "stripped-text",
            "subject", "from", "sender", "message", "content"
        ]
        
        extracted_parts = []
        
        # Extract subject
        subject = payload.get("subject", "")
        if subject:
            extracted_parts.append(f"Subject: {subject}")
        
        # Extract sender
        sender = payload.get("from", payload.get("sender", ""))
        if sender:
            extracted_parts.append(f"From: {sender}")
        
        # Extract main content
        for field in content_fields:
            if field in payload and payload[field]:
                content = payload[field]
                if isinstance(content, str) and content.strip():
                    extracted_parts.append(f"Content: {content.strip()}")
                    break
        
        # If no structured content found, try to extract from raw body
        if not extracted_parts and isinstance(body, str):
            extracted_parts.append(f"Raw content: {body}")
        
        result = "\n".join(extracted_parts)
        logger.info(f"Extracted email content: {result[:200]}...")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting email content: {str(e)}")
        return str(event.get("body", ""))


def extract_slack_content(event: Dict[str, Any]) -> str:
    """Extract content from Slack webhook payload."""
    try:
        body = event.get("body", "")
        if isinstance(body, str):
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                # Handle URL-encoded form data (Slack often sends this way)
                payload = parse_form_data(body)
        else:
            payload = body or {}

        # Handle Slack slash commands
        if "command" in payload:
            command = payload.get("command", "")
            text = payload.get("text", "")
            user = payload.get("user_name", "")
            return f"Slack command {command} from {user}: {text}"
        
        # Handle Slack events API
        if "event" in payload:
            event_data = payload["event"]
            event_type = event_data.get("type", "")
            text = event_data.get("text", "")
            user = event_data.get("user", "")
            return f"Slack {event_type} from {user}: {text}"
        
        # Handle direct message format
        text_fields = ["text", "message", "content"]
        for field in text_fields:
            if field in payload and payload[field]:
                user = payload.get("user_name", payload.get("user", ""))
                content = payload[field]
                return f"Slack message from {user}: {content}"
        
        # Fallback to raw content
        return str(body)
        
    except Exception as e:
        logger.error(f"Error extracting Slack content: {str(e)}")
        return str(event.get("body", ""))


def extract_generic_content(event: Dict[str, Any]) -> str:
    """Extract content from generic webhook payload."""
    try:
        body = event.get("body", "")
        
        if isinstance(body, str):
            try:
                payload = json.loads(body)
                # Look for common text fields
                text_fields = ["text", "message", "content", "body", "description"]
                for field in text_fields:
                    if field in payload and payload[field]:
                        return str(payload[field])
                # If no text field found, return the JSON as string
                return json.dumps(payload, indent=2)
            except json.JSONDecodeError:
                # Return as plain text
                return body
        elif isinstance(body, dict):
            # Direct dictionary payload
            text_fields = ["text", "message", "content", "body", "description"]
            for field in text_fields:
                if field in body and body[field]:
                    return str(body[field])
            return json.dumps(body, indent=2)
        else:
            return str(body)
            
    except Exception as e:
        logger.error(f"Error extracting generic content: {str(e)}")
        return str(event)


def parse_form_data(body: str) -> Dict[str, str]:
    """Parse URL-encoded form data."""
    try:
        pairs = body.split('&')
        result = {}
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                result[unquote_plus(key)] = unquote_plus(value)
        return result
    except Exception as e:
        logger.error(f"Error parsing form data: {str(e)}")
        return {}


def generate_session_id(trigger_type: str, event: Dict[str, Any]) -> str:
    """Generate a unique session ID based on trigger type and event data."""
    import hashlib
    import time
    
    # Create a unique identifier based on trigger type and some event data
    identifier_parts = [trigger_type, str(int(time.time()))]
    
    # Add trigger-specific identifiers
    if trigger_type == "email":
        body = event.get("body", "")
        if isinstance(body, str):
            try:
                payload = json.loads(body)
                sender = payload.get("from", payload.get("sender", ""))
                if sender:
                    identifier_parts.append(sender)
            except:
                pass
    elif trigger_type == "slack":
        body = event.get("body", "")
        if isinstance(body, str):
            try:
                payload = json.loads(body)
                user = payload.get("user_name", payload.get("user", ""))
                if user:
                    identifier_parts.append(user)
            except:
                pass
    
    # Create hash of identifier parts
    identifier = "-".join(identifier_parts)
    session_hash = hashlib.md5(identifier.encode()).hexdigest()[:8]
    
    return f"{trigger_type}-{session_hash}"


def send_email_notification(agent_response: str, original_content: str) -> None:
    """Send email notification using AWS SES."""
    ses_from_email = os.environ.get("SES_FROM_EMAIL")
    ses_to_email = os.environ.get("SES_TO_EMAIL")
    
    if not ses_from_email or not ses_to_email:
        logger.info("SES email addresses not configured, skipping email notification")
        return
    
    try:
        ses_client = boto3.client('ses')
        agent_data = json.loads(agent_response)
        
        priority = agent_data.get("priority", "Medium")
        summary = agent_data.get("summary", "Lead processed")
        company = agent_data.get("extracted_data", {}).get("company", "Unknown")
        contact_name = agent_data.get("extracted_data", {}).get("contact_name", "Unknown")
        contact_email = agent_data.get("extracted_data", {}).get("contact_email", "Unknown")
        
        subject = f"🎯 New {priority} Priority Lead: {company}"
        
        body = f"""
New lead processed by Synapse AI Agent:

Company: {company}
Contact: {contact_name}
Email: {contact_email}
Priority: {priority}

Summary: {summary}

Original Input: {original_content[:200]}...

View full details in AWS CloudWatch logs.
        """
        
        response = ses_client.send_email(
            Source=ses_from_email,
            Destination={'ToAddresses': [ses_to_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        
        logger.info(f"Email notification sent successfully: {response['MessageId']}")
        
    except Exception as e:
        logger.error(f"Error sending email notification: {str(e)}")


def send_slack_notification(agent_response: str, original_content: str) -> None:
    """Send notification to Slack webhook."""
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        logger.info("Slack webhook URL not configured, skipping notification")
        return
    
    try:
        agent_data = json.loads(agent_response)
        priority = agent_data.get("priority", "Medium")
        summary = agent_data.get("summary", "Lead processed")
        action = agent_data.get("action", "unknown")
        company = agent_data.get("extracted_data", {}).get("company", "Unknown")
        
        color = "good" if priority == "High" else "warning" if priority == "Medium" else "#cccccc"
        
        payload = {
            "text": "🎯 New Lead Processed by Synapse",
            "attachments": [{
                "color": color,
                "fields": [
                    {"title": "Company", "value": company, "short": True},
                    {"title": "Priority", "value": priority, "short": True},
                    {"title": "Action", "value": action, "short": True},
                    {"title": "Summary", "value": summary, "short": False}
                ]
            }]
        }
        
        import requests
        response = requests.post(slack_webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Slack notification sent successfully")
        else:
            logger.error(f"Slack notification failed: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error sending Slack notification: {str(e)}")


def format_response_for_trigger(trigger_type: str, agent_response: str, original_content: str) -> Any:
    """Format the agent response based on the trigger type."""
    
    # Send notifications for all successful responses
    if agent_response and not agent_response.startswith("Error"):
        send_slack_notification(agent_response, original_content)
        send_email_notification(agent_response, original_content)
    
    if trigger_type == "slack":
        # Slack expects specific response format
        try:
            # Try to parse agent response as JSON
            agent_data = json.loads(agent_response)
            summary = agent_data.get("summary", "Lead processed")
            priority = agent_data.get("priority", "Medium")
            action = agent_data.get("action", "unknown")
            
            return {
                "response_type": "in_channel",
                "text": f"🎯 Lead Processed",
                "attachments": [
                    {
                        "color": "good" if priority == "High" else "warning" if priority == "Medium" else "#cccccc",
                        "fields": [
                            {
                                "title": "Summary",
                                "value": summary,
                                "short": False
                            },
                            {
                                "title": "Priority",
                                "value": priority,
                                "short": True
                            },
                            {
                                "title": "Action",
                                "value": action,
                                "short": True
                            }
                        ]
                    }
                ]
            }
        except json.JSONDecodeError:
            # Fallback to simple text response
            return {
                "response_type": "in_channel",
                "text": f"Lead processed: {agent_response[:200]}..."
            }
    
    elif trigger_type == "email":
        # Email webhook might expect plain text or JSON
        try:
            agent_data = json.loads(agent_response)
            summary = agent_data.get("summary", "Lead processed")
            priority = agent_data.get("priority", "Medium")
            return f"Lead processed with {priority} priority: {summary}"
        except json.JSONDecodeError:
            return f"Lead processed: {agent_response}"
    
    else:
        # Generic webhook - return agent response as-is
        return agent_response
