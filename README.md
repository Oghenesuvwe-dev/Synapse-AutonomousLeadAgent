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

## What’s Next

- **Enrichment API:** Implement an action group to call an enrichment API (e.g., Hunter.io, Clearbit) to get more information about a lead.
- **CRM Integration:** The CRM integration is currently mocked in the tests. To make it fully functional, you need to deploy a SuiteCRM instance and configure the credentials in AWS Secrets Manager.
- **Error Handling:** Improve the error handling in the Lambdas and the agent.
- **Monitoring:** Set up more detailed monitoring and alerting.

For detailed project tasks see the files in `ABOUT PROJECT/`.
