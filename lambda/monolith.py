import json
import os
import boto3
import requests
import time
from typing import Dict, Any
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup

logger = Logger()

def handler(event, context):
    """Monolith function handling complete lead processing workflow."""
    logger.info("Processing lead with monolith architecture")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    
    try:
        # Extract lead data
        lead_data = extract_lead_data(event)
        if not lead_data:
            return error_response("No lead data found")
        
        logger.info(f"Extracted lead data: {lead_data[:200]}...")
        
        # Process sequentially (no concurrency issues)
        results = {
            'ai_analysis': None,
            'web_scraping': None,
            'crm_creation': None,
            'notifications': None
        }
        
        # Step 1: AI Analysis
        logger.info("Step 1: AI Analysis")
        results['ai_analysis'] = analyze_with_bedrock(lead_data)
        logger.info(f"AI Analysis complete: {results['ai_analysis']}")
        
        # Step 2: Web Scraping (if domain found)
        domain = results['ai_analysis'].get('domain')
        if domain:
            logger.info(f"Step 2: Web Scraping for {domain}")
            results['web_scraping'] = scrape_website(domain)
            logger.info(f"Web scraping complete: {results['web_scraping'].get('status')}")
        
        # Step 3: CRM Creation
        logger.info("Step 3: CRM Creation")
        results['crm_creation'] = create_crm_lead(results['ai_analysis'])
        logger.info(f"CRM creation complete: {results['crm_creation'].get('status')}")
        
        # Step 4: Notifications
        logger.info("Step 4: Notifications")
        results['notifications'] = send_notifications(results)
        logger.info(f"Notifications sent: {results['notifications']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'lead_id': results['crm_creation'].get('id'),
                'summary': 'Lead processed successfully'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in monolith processing: {str(e)}", exc_info=True)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'partial_success',
                'error': str(e),
                'summary': 'Lead processed with limitations'
            })
        }

def extract_lead_data(event: Dict[str, Any]) -> str:
    """Extract lead data from event."""
    try:
        body = event.get('body', '')
        if isinstance(body, str) and body:
            try:
                payload = json.loads(body)
                return payload.get('text', payload.get('message', str(payload)))
            except json.JSONDecodeError:
                return body
        elif isinstance(body, dict):
            return body.get('text', body.get('message', str(body)))
        return str(event.get('text', event))
    except Exception as e:
        logger.error(f"Error extracting lead data: {str(e)}")
        return str(event)

def analyze_with_bedrock(lead_data: str) -> Dict[str, Any]:
    """Direct Bedrock call for AI analysis."""
    bedrock = boto3.client('bedrock-runtime')
    
    prompt = f"""Analyze this lead and extract structured data:
{lead_data}

Return JSON with: priority, company, domain, contact_name, contact_email, contact_phone, description"""
    
    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1000,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['content'][0]['text']
        
        # Extract JSON from response
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        
        # Fallback parsing
        return {
            'priority': 'Medium',
            'company': 'Unknown',
            'domain': None,
            'contact_name': 'Unknown',
            'contact_email': None,
            'description': lead_data[:200]
        }
        
    except Exception as e:
        logger.error(f"Bedrock analysis failed: {str(e)}")
        return {
            'priority': 'Medium',
            'company': 'Unknown',
            'domain': None,
            'contact_name': 'Unknown',
            'contact_email': None,
            'description': lead_data[:200]
        }

def scrape_website(domain: str) -> Dict[str, Any]:
    """Simple web scraping with BeautifulSoup."""
    try:
        if not domain.startswith('http'):
            url = f"https://{domain}"
        else:
            url = domain
            
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; SynapseBot/1.0)'
        })
        response.raise_for_status()
        
        # Extract text summary
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        summary = text[:800]
        
        # Store in S3
        s3_key = store_in_s3(response.text, domain)
        
        return {
            'status': 'success',
            'url': url,
            's3_key': s3_key,
            'summary': summary,
            'text_length': len(text)
        }
        
    except Exception as e:
        logger.error(f"Web scraping failed: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'summary': f"Could not scrape {domain}"
        }

def store_in_s3(content: str, domain: str) -> str:
    """Store scraped content in S3."""
    try:
        s3 = boto3.client('s3')
        bucket = os.environ.get('SCRAPER_BUCKET', 'synapse-scraper-bucket')
        key = f"scraped/{domain}/{int(time.time())}.html"
        
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType='text/html'
        )
        
        return key
    except Exception as e:
        logger.error(f"S3 storage failed: {str(e)}")
        return None

def create_crm_lead(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Create lead in SuiteCRM with OAuth2."""
    try:
        # Get CRM credentials
        secrets = boto3.client('secretsmanager')
        secret = secrets.get_secret_value(SecretId=os.environ.get('SUITECRM_SECRET_ID'))
        creds = json.loads(secret['SecretString'])
        
        # Get base URL (handle both 'url' and 'base_url' keys)
        base_url = creds.get('url') or creds.get('base_url')
        if not base_url:
            logger.error("No CRM URL found in credentials")
            return {'status': 'failed', 'error': 'Missing CRM URL', 'summary': 'CRM configuration incomplete'}
        
        # Check if we have OAuth2 credentials
        if creds.get('client_id') and creds.get('client_secret'):
            # Get OAuth2 token
            token_url = f"{base_url.rstrip('/')}/Api/access_token"
            token_response = requests.post(
                token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': creds['client_id'],
                    'client_secret': creds['client_secret']
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if token_response.status_code != 200:
                logger.error(f"Token request failed: {token_response.status_code} - {token_response.text}")
                return {
                    'status': 'failed',
                    'error': f"OAuth2 token failed: {token_response.status_code}",
                    'summary': 'CRM authentication failed'
                }
            
            access_token = token_response.json().get('access_token')
        elif 'access_token' in creds:
            # Use demo token directly
            access_token = creds['access_token']
        else:
            logger.error("No valid CRM credentials found")
            return {
                'status': 'failed',
                'error': 'Missing CRM credentials',
                'summary': 'CRM configuration incomplete'
            }
        
        # Prepare lead data
        contact_name = analysis.get('contact_name', 'Unknown Contact')
        name_parts = contact_name.split()
        first_name = name_parts[0] if name_parts else 'Unknown'
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'Contact'
        
        lead_data = {
            'data': {
                'type': 'Leads',
                'attributes': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email1': analysis.get('contact_email', ''),
                    'account_name': analysis.get('company', 'Unknown Company'),
                    'description': f"Priority: {analysis.get('priority', 'Medium')}\n{analysis.get('description', '')}",
                    'lead_source': 'Synapse AI Agent',
                    'status': 'New'
                }
            }
        }
        
        # Create CRM lead
        api_url = f"{base_url.rstrip('/')}/Api/V8/module"
        response = requests.post(
            api_url,
            headers={
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            },
            json=lead_data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            lead_id = result.get('data', {}).get('id', 'unknown')
            return {
                'status': 'success',
                'id': lead_id,
                'summary': f"Created CRM lead for {analysis.get('company', 'Unknown')}"
            }
        else:
            logger.error(f"CRM API error: {response.status_code} - {response.text}")
            return {
                'status': 'failed',
                'error': f"CRM API returned {response.status_code}",
                'summary': 'CRM creation failed'
            }
            
    except Exception as e:
        logger.error(f"CRM creation failed: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e),
            'summary': 'CRM integration unavailable'
        }

def send_notifications(results: Dict[str, Any]) -> Dict[str, Any]:
    """Send email and Slack notifications."""
    notification_results = {}
    
    # Email notification
    try:
        send_email_notification(results)
        notification_results['email'] = 'success'
    except Exception as e:
        logger.error(f"Email notification failed: {str(e)}")
        notification_results['email'] = 'failed'
    
    # Slack notification
    try:
        send_slack_notification(results)
        notification_results['slack'] = 'success'
    except Exception as e:
        logger.error(f"Slack notification failed: {str(e)}")
        notification_results['slack'] = 'failed'
    
    return notification_results

def send_email_notification(results: Dict[str, Any]):
    """Send email via SES."""
    ses_from = os.environ.get('SES_FROM_EMAIL')
    ses_to = os.environ.get('SES_TO_EMAIL')
    
    if not ses_from or not ses_to:
        logger.warning("SES email addresses not configured")
        return
    
    ses = boto3.client('ses')
    
    analysis = results.get('ai_analysis') or {}
    company = analysis.get('company', 'Unknown')
    priority = analysis.get('priority', 'Medium')
    crm_status = results.get('crm_creation', {}).get('status', 'Unknown')
    crm_id = results.get('crm_creation', {}).get('id', 'N/A')
    web_status = results.get('web_scraping', {}).get('status', 'Not attempted')
    
    subject = f"New {priority} Priority Lead: {company}"
    body = f"""
New Lead Processed by Synapse Autonomous Lead Intelligence

=== LEAD DETAILS ===
Company: {company}
Priority: {priority}
Contact: {analysis.get('contact_name', 'Unknown')}
Email: {analysis.get('contact_email', 'Not provided')}
Phone: {analysis.get('contact_phone', 'Not provided')}

=== PROCESSING STATUS ===
CRM Status: {crm_status}
CRM Lead ID: {crm_id}
Web Intelligence: {web_status}

=== DESCRIPTION ===
{analysis.get('description', 'No additional details')}

Lead has been processed and is ready for follow-up.

---
Powered by Synapse Autonomous Lead Intelligence (Demo)
"""
    
    ses.send_email(
        Source=ses_from,
        Destination={'ToAddresses': [ses_to]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body}}
        }
    )
    logger.info(f"Email notification sent to {ses_to}")

def send_slack_notification(results: Dict[str, Any]):
    """Send Slack notification."""
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if not webhook_url:
        logger.warning("Slack webhook URL not configured")
        return
    
    analysis = results.get('ai_analysis') or {}
    company = analysis.get('company', 'Unknown')
    priority = analysis.get('priority', 'Medium')
    crm_status = results.get('crm_creation', {}).get('status', 'Unknown')
    crm_id = results.get('crm_creation', {}).get('id', 'N/A')
    
    color = 'good' if priority == 'High' else 'warning' if priority == 'Medium' else '#cccccc'
    
    payload = {
        'text': f"🎯 New {priority} Priority Lead: {company}",
        'attachments': [{
            'color': color,
            'fields': [
                {'title': 'Company', 'value': company, 'short': True},
                {'title': 'Priority', 'value': priority, 'short': True},
                {'title': 'Contact', 'value': analysis.get('contact_name', 'Unknown'), 'short': True},
                {'title': 'Email', 'value': analysis.get('contact_email', 'N/A'), 'short': True},
                {'title': 'CRM Status', 'value': crm_status, 'short': True},
                {'title': 'CRM Lead ID', 'value': crm_id, 'short': True}
            ],
            'footer': 'Synapse AI Agent',
            'ts': int(time.time())
        }]
    }
    
    response = requests.post(webhook_url, json=payload, timeout=10)
    if response.status_code == 200:
        logger.info("Slack notification sent successfully")
    else:
        logger.error(f"Slack notification failed: {response.status_code}")

def error_response(message: str):
    """Return error response."""
    return {
        'statusCode': 400,
        'body': json.dumps({'error': message})
    }