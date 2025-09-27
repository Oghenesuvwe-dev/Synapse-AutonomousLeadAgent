# Synapse — Autonomous Lead Intelligence Agent

This repository contains the code for the Synapse agent, an autonomous lead intelligence agent built on AWS Bedrock. The agent can be triggered by a webhook, and it can scrape websites and create leads in a CRM.

## Architecture

```
+-----------------+      +------------------+      +-----------------+      +-----------------+
|   Webhook       |----->|  Webhook Lambda  |----->|  Bedrock Agent  |----->| Scraper Lambda  |
+-----------------+      +------------------+      +-----------------+      +-----------------+
                                                     |
                                                     |
                                                     v
                                                +-----------------+
                                                |   CRM Lambda    |
                                                +-----------------+
```

## Quick Start

1. Install prerequisites: Python 3.13+, pip, AWS CLI, AWS SAM CLI, Docker.
2. Create a virtual environment and install Python requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Deploy the SAM stack:

```bash
sam build
sam deploy --guided
```

4. After deployment, you will get an API Gateway endpoint. You can send a POST request to this endpoint to trigger the agent:

```bash
curl -X POST <your-api-gateway-endpoint> \
  -H "Content-Type: application/json" \
  -d '{"text":"New lead from https://example.com"}'
```

## Project Structure

- `lambda/webhook.py`: The Lambda function that receives the webhook and invokes the Bedrock agent.
- `lambda/scraper.py`: The Lambda function that scrapes a website and stores the HTML in S3.
- `lambda/crm.py`: The Lambda function that creates a lead in SuiteCRM.
- `agent/prompts.md`: The instruction prompt for the Bedrock agent.
- `agent/schemas/lead_actions.json`: The OpenAPI schema for the scraper action group.
- `agent/schemas/crm_actions.json`: The OpenAPI schema for the CRM action group.
- `infra/template.yaml`: The AWS SAM template that defines the infrastructure.
- `requirements.txt`: The Python dependencies.
- `tests/integration/test_workflow.py`: The integration tests.

## Current Deployment Status

### ✅ Infrastructure Health
- **CloudFormation Stack**: `UPDATE_COMPLETE` - All 16 resources deployed successfully
- **Lambda Functions**: 3 functions deployed and operational
  - `WebhookFunction`: Handles incoming leads via API Gateway
  - `ScraperFunction`: Web scraping with S3 storage
  - `CrmFunction`: SuiteCRM integration ready
- **Bedrock Agent**: `PREPARED` status (Agent ID: S1SGRINXPM)
- **API Gateway**: 3 endpoints active and accessible
- **S3 Bucket**: Created for storing scraped content
- **IAM Roles**: Properly configured with necessary permissions

### 🔗 Active API Endpoints
- **Main Webhook**: `https://hdjuehu4fa.execute-api.us-east-1.amazonaws.com/Prod/webhook`
- **Email Webhook**: `https://hdjuehu4fa.execute-api.us-east-1.amazonaws.com/Prod/webhook/email`
- **Slack Webhook**: `https://hdjuehu4fa.execute-api.us-east-1.amazonaws.com/Prod/webhook/slack`

### 🚨 Critical Issue
**Bedrock Model Access Required**: The system returns `accessDeniedException` when invoking the Bedrock agent.

**Solution**: Enable Anthropic Claude 3 Sonnet model access in AWS Bedrock Console:
1. Go to [AWS Bedrock Model Access](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess)
2. Click "Manage model access"
3. Select "Anthropic Claude 3 Sonnet"
4. Submit request (instant approval)

### 🧪 Testing the System

Once Bedrock access is enabled, test the system:

```bash
curl -X POST https://hdjuehu4fa.execute-api.us-east-1.amazonaws.com/Prod/webhook \
  -H "Content-Type: application/json" \
  -d '{"text":"New lead from TechCorp: Sarah Johnson, VP Engineering at techcorp.com, looking for CRM solution for 500+ team. Budget approved. Contact: sarah.j@techcorp.com"}'
```

### 📊 System Health Check

Run the deployment health check script:
```bash
./check-deployment.sh
```

## What's Next

- **✅ Enrichment API**: Implemented via web scraping functionality for company intelligence gathering
- **✅ CRM Integration**: Fully implemented with SuiteCRM integration and AWS Secrets Manager
- **✅ Error Handling**: Comprehensive error handling implemented across all Lambdas with AWS Lambda Powertools
- **✅ Monitoring**: CloudWatch logging and monitoring active with structured logging

### Final Steps
1. **Enable Bedrock Model Access** (5 minutes) - Critical blocker
2. **Demo Video Production** - System ready for recording
3. **DevPost Submission** - Documentation and code complete

For detailed project tasks and phase completion status, see the files in `ABOUT PROJECT/`.
