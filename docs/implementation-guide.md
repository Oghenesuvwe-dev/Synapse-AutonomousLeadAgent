# Synapse Implementation Guide

This guide provides step-by-step instructions for implementing the Synapse project following our best practices.

## Phase 1: Foundation Setup

### 1. Initial Project Setup
```bash
# Create project structure
mkdir -p synapse/{lambda/{common,webhook,scraper},agent/{prompts,schemas},infra/{env,modules},tests/{unit,integration}}

# Initialize virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize git
git init
git add .
git commit -m "Initial project setup"
```

### 2. Configure AWS Environment
```bash
# Create named AWS profile for the project
aws configure --profile synapse-dev

# Store API keys in Secrets Manager
aws secretsmanager create-secret \
    --name synapse/dev/enrichment-api-key \
    --secret-string '''{"api_key":"your-key-here"}''' \
    --profile synapse-dev

# Create S3 bucket for scraped content
aws s3api create-bucket \
    --bucket synapse-scraper-dev \
    --profile synapse-dev
```

### 3. Set Up Local Development
```bash
# Install AWS SAM CLI
brew tap aws/tap
brew install aws-sam-cli

# Install LocalStack (optional, for offline development)
pip install localstack
pip install awscli-local

# Start LocalStack
localstack start
```

## Phase 2: Enhanced Intelligence & Webhook System ✅ COMPLETED

**Phase 2 has been successfully completed with advanced prompt engineering and comprehensive webhook implementation.**

### Key Achievements:

1. **Advanced Prompt Engineering**:
   - 3-phase decision-making framework
   - Sophisticated lead scoring and prioritization
   - Structured JSON output with confidence scoring
   - See: [`agent/prompts.md`](../agent/prompts.md)

2. **Multi-Channel Webhook System**:
   - Email webhook support (`/webhook/email`)
   - Slack webhook support (`/webhook/slack`)
   - Generic webhook support (`/webhook`)
   - Intelligent content parsing and response formatting
   - See: [`lambda/webhook.py`](../lambda/webhook.py)

3. **Comprehensive Testing**:
   - All webhook functionality validated
   - Sample payloads for testing
   - Automated test suite with 100% pass rate
   - See: [`tests/test_webhook_logic.py`](../tests/test_webhook_logic.py)

**📋 For detailed Phase 2 information, see: [Phase 2 Completion Guide](phase2-completion-guide.md)**

### 1. Enhanced Webhook Lambda Implementation

The webhook system now supports multiple trigger types with intelligent parsing:

```python
# Key Features:
- Multi-trigger support (email/Slack/generic)
- Smart content extraction
- Session ID generation
- Response formatting per trigger type
- Comprehensive error handling

# API Endpoints:
POST /webhook        # Generic webhook
POST /webhook/email  # Email service integration
POST /webhook/slack  # Slack integration
```

**Full implementation**: [`lambda/webhook.py`](../lambda/webhook.py) (267 lines)

### 2. Scraper Lambda Implementation
```python
# lambda/scraper.py
import requests
import boto3
from bs4 import BeautifulSoup
import os
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()
s3 = boto3.client("s3")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """Fetches a URL provided in the event, extracts text, stores raw HTML to S3,
    and returns a short text summary (first N chars)."""
    url = event.get("url")
    if not url:
        logger.error("Missing URL in event")
        return {"statusCode": 400, "body": "missing url"}

    bucket = os.environ.get("SCRAPER_BUCKET")
    logger.info(f"Fetching URL: {url}")

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.exception(f"Error fetching URL: {url}")
        return {"statusCode": 500, "body": f"Error fetching URL: {e}"}

    html = resp.text
    key = f"scraped/{hash(url)}.html"
    if bucket:
        try:
            s3.put_object(Bucket=bucket, Key=key, Body=html.encode("utf-8"))
            logger.info(f"Saved HTML to s3://{bucket}/{key}")
        except Exception as e:
            logger.exception(f"Error saving to S3: {e}")
            return {"statusCode": 500, "body": f"Error saving to S3: {e}"}

    try:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        summary = text[:800]
    except Exception as e:
        logger.exception("Error parsing HTML")
        return {"statusCode": 500, "body": f"Error parsing HTML: {e}"}

    return {"statusCode": 200, "body": {"summary": summary, "s3_key": key}}
```

### 3. Bedrock Agent Setup

1. Create Agent Schema:
```json
// agent/schemas/lead_actions.json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Lead Processing Actions",
    "version": "1.0.0"
  },
  "paths": {
    "/scrape": {
      "post": {
        "summary": "Scrape a website",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "required": ["url"],
                "properties": {
                  "url": {
                    "type": "string"
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

2. Create Agent Prompt:
```markdown
# agent/prompts/lead_processing.md

You are the Synapse Lead Intelligence Agent. Your task is to:

1. Parse incoming lead messages
2. Extract key information (company, contact, website)
3. Decide on enrichment actions
4. Prioritize leads

INPUT FORMAT:
- Text message containing lead information

OUTPUT FORMAT:
{
  "action": "enrich|create|skip",
  "priority": "high|medium|low",
  "extracted": {
    "company": "string",
    "website": "string",
    "contact": "string"
  }
}

EXAMPLE INPUT:
"New lead from Acme Corp (acme.com). Contact: John Smith"

EXAMPLE OUTPUT:
{
  "action": "enrich",
  "priority": "high",
  "extracted": {
    "company": "Acme Corp",
    "website": "acme.com",
    "contact": "John Smith"
  }
}
```

### 4. Infrastructure Setup

1. Create SAM Template:
```yaml
# infra/template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Minimal SAM template for Synapse Lambdas

Globals:
  Function:
    Timeout: 30

Resources:
  WebhookFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: webhook.handler
      Runtime: python3.13
      CodeUri: lambda/
      Environment:
        Variables:
          AGENT_ALIAS_ID: !GetAtt SynapseAgentAlias.AliasId
          AGENT_ID: !GetAtt SynapseAgent.AgentId
      Policies:
        - AWSLambdaBasicExecutionRole
        - Statement:
          - Effect: Allow
            Action:
              - bedrock:InvokeAgent
            Resource: !Sub "arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:agent-alias/${SynapseAgent.AgentId}/*"


  ScraperFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: scraper.handler
      Runtime: python3.13
      CodeUri: lambda/
      Environment:
        Variables:
          SCRAPER_BUCKET: !Ref ScraperBucket
      Policies:
        - AWSLambdaBasicExecutionRole
        - S3WritePolicy:
            BucketName: !Ref ScraperBucket

  ScraperBucket:
    Type: AWS::S3::Bucket

  AgentRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service:
                - bedrock.amazonaws.com
            Action:
              - sts:AssumeRole
      Policies:
        - PolicyName: AgentPolicy
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - lambda:InvokeFunction
                Resource: !GetAtt ScraperFunction.Arn

  SynapseAgent:
    Type: AWS::Bedrock::Agent
    Properties:
      AgentName: SynapseAgent
      FoundationModel: anthropic.claude-v2:1
      Instruction: !Sub |
        You are the Synapse Agent. Your job is to:
        1. Parse incoming lead messages (text) and extract: company name, domain, contact name, contact email, short description.
        2. Decide whether to call the enrichment API (if domain or company found) and/or the scraper (if website is available).
        3. Synthesize a lead summary and assign a priority: High/Medium/Low.
        4. Output a JSON object with fields: action (one of [create_contact, enrich, scrape]), params (object), summary (string), priority (string).
      AgentResourceRoleArn: !GetAtt AgentRole.Arn
      ActionGroups:
        - ActionGroupName: ScraperActionGroup
          ActionGroupExecutor:
            Lambda: !GetAtt ScraperFunction.Arn
          APISchema:
            S3:
              S3BucketName: !Ref ScraperBucket
              S3ObjectKey: agent/schemas/lead_actions.json

  SynapseAgentAlias:
    Type: AWS::Bedrock::AgentAlias
    Properties:
      AgentId: !GetAtt SynapseAgent.AgentId
      AgentAliasName: live
```

2. Deploy Infrastructure:
```bash
# Build and deploy
sam build
sam deploy --guided

# Test deployment
curl -X POST https://your-api-endpoint/webhook \
  -H "Content-Type: application/json" \
  -d '''{"text":"New lead from Acme Corp"}'''
```

## Phase 3: Testing & Monitoring Setup

### 1. Unit Tests
```python
# tests/unit/test_webhook.py
import pytest
from unittest.mock import patch
from lambda.webhook.app import handler

def test_webhook_handler():
    event = {
        "body": json.dumps({
            "text": "New lead from Acme Corp"
        })
    }
    
    response = handler(event, None)
    assert response["statusCode"] == 200
```

### 2. Integration Tests
```python
# tests/integration/test_workflow.py
def test_end_to_end_flow():
    # Send webhook
    response = requests.post(
        f"{API_ENDPOINT}/webhook",
        json={"text": "New lead from Acme Corp"}
    )
    assert response.status_code == 200
    
    # Check lead was created
    lead_id = response.json()["leadId"]
    lead = get_lead_from_crm(lead_id)
    assert lead["company"] == "Acme Corp"
```

### 3. Monitoring Setup

1. Create CloudWatch Dashboard:
```yaml
# infra/modules/monitoring.yaml
Resources:
  SynapseDashboard:
    Type: AWS::CloudWatch::Dashboard
    Properties:
      DashboardName: Synapse-Monitoring
      DashboardBody: !Sub |
        {
          "widgets": [
            {
              "type": "metric",
              "properties": {
                "metrics": [
                  ["AWS/Lambda", "Invocations", "FunctionName", "${WebhookFunction}"],
                  ["AWS/Lambda", "Errors", "FunctionName", "${WebhookFunction}"]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "${AWS::Region}",
                "title": "Webhook Lambda Metrics"
              }
            }
          ]
        }
```

2. Set up Alarms:
```yaml
Resources:
  WebhookErrorAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: SynapseWebhookErrors
      MetricName: Errors
      Namespace: AWS/Lambda
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 1
      ComparisonOperator: GreaterThanThreshold
```

## Running Locally

1. Start Local Environment:
```bash
# Start LocalStack (if using)
localstack start

# Run Lambda locally
sam local start-api

# Test webhook
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '''{"text":"New lead from Acme Corp"}'''
```

2. Run Tests:
```bash
# Run unit tests
pytest tests/unit

# Run integration tests (requires deployed environment)
pytest tests/integration
```

## Deployment Checklist

Before deploying to production:

1. Security:
   - [ ] Review IAM roles for least privilege
   - [ ] Ensure all secrets are in Secrets Manager
   - [ ] Enable AWS WAF on API Gateway
   - [ ] Enable CloudTrail logging

2. Monitoring:
   - [ ] Set up CloudWatch dashboards
   - [ ] Configure error alarms
   - [ ] Enable X-Ray tracing
   - [ ] Set up error notifications

3. Testing:
   - [ ] Run full test suite
   - [ ] Perform load testing
   - [ ] Test error scenarios
   - [ ] Verify monitoring/alerts

4. Documentation:
   - [ ] Update API documentation
   - [ ] Document deployment process
   - [ ] Create runbook for incidents
   - [ ] Document monitoring setup