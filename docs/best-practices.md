# Synapse Project: Best Practices

## Architecture Best Practices

### AWS Lambda
- Use environment variables for configuration (stored in SSM Parameter Store)
- Keep functions focused (single responsibility)
- Implement proper error handling and logging
- Use Lambda Layers for shared dependencies
- Set appropriate memory and timeout values
- Use AWS X-Ray for tracing
```yaml
# Example SAM template configuration
Functions:
  WebhookFunction:
    Tracing: Active
    Environment:
      Variables:
        LOG_LEVEL: INFO
        POWERTOOLS_SERVICE_NAME: webhook
    Layers:
      - !Ref LambdaUtilsLayer
```

### API Gateway
- Use API keys and usage plans
- Implement request validation
- Enable CloudWatch logging
- Use custom domains with ACM certificates
- Implement CORS if needed
```yaml
# Example API Gateway configuration
ApiGatewayApi:
  Auth:
    ApiKeyRequired: true
  Models:
    WebhookRequest:
      type: object
      required: ['text']
```

### Bedrock Agent
- Version control your prompts
- Use example-driven prompt engineering
- Implement robust input validation
- Add comprehensive logging of agent decisions
- Use action group timeouts appropriately
```python
# Example action group definition
{
    "actionGroupName": "EnrichmentActions",
    "actionGroupExecutor": "enrichment_lambda",
    "actionGroupDescription": "Actions for enriching lead data",
    "apiSchema": {
        "openapi": "3.0.0",
        "paths": {...}
    },
    "timeoutInSeconds": 10
}
```

### Security Best Practices

### IAM & Permissions
- Use least privilege access
- Create separate roles per function
- Scope S3 bucket policies tightly
- Rotate credentials regularly
```yaml
# Example IAM role with least privilege
WebhookFunctionRole:
  Properties:
    Policies:
      - PolicyName: MinimalSQSAccess
        PolicyDocument:
          Statement:
            - Effect: Allow
              Action: 
                - sqs:SendMessage
              Resource: !GetAtt LeadQueue.Arn
```

### Secrets Management
- Use AWS Secrets Manager for API keys
- Encrypt environment variables
- Implement secret rotation
- Use separate secrets per environment
```python
# Example secrets retrieval
def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])
```

### Data Protection
- Encrypt data at rest (S3, SQS)
- Use HTTPS/TLS for all API calls
- Implement request signing
- Sanitize all inputs
```yaml
# Example S3 bucket encryption
ScraperBucket:
  Properties:
    BucketEncryption:
      ServerSideEncryptionConfiguration:
        - ServerSideEncryptionByDefault:
            SSEAlgorithm: AES256
```

## Development Best Practices

### Code Organization
```
synapse/
├── lambda/
│   ├── common/           # Shared utilities
│   ├── webhook/         
│   └── scraper/
├── agent/
│   ├── prompts/
│   └── schemas/
├── infra/
│   ├── env/             # Environment-specific configs
│   └── modules/         # Reusable CloudFormation
└── tests/
    ├── unit/
    └── integration/
```

### Testing
- Write unit tests for all Lambda functions
- Use moto for AWS service mocking
- Implement integration tests
- Use LocalStack for local testing
```python
# Example test with moto
@mock_s3
def test_scraper_saves_to_s3():
    s3 = boto3.client('s3')
    s3.create_bucket(Bucket='test-bucket')
    
    event = {"url": "http://example.com"}
    response = scraper.handler(event, None)
    
    assert response['statusCode'] == 200
```

### CI/CD Pipeline
- Use AWS SAM pipeline
- Implement environment promotion
- Run security scans
- Automated testing
```yaml
# Example buildspec.yml
phases:
  build:
    commands:
      - sam build
      - pytest tests/
      - bandit -r lambda/
  post_build:
    commands:
      - sam deploy --stack-name ${STACK_NAME}
```

### Monitoring & Observability
- Set up CloudWatch alarms
- Use custom metrics
- Implement structured logging
- Create dashboards
```python
# Example structured logging
logger.info("Processing lead", extra={
    "lead_source": event["source"],
    "correlation_id": context.aws_request_id
})
```

### Error Handling
- Implement proper retry mechanisms
- Use Dead Letter Queues
- Set up error notifications
- Log error context
```python
try:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    logger.error("Failed to fetch URL", exc_info=e)
    raise
```

## Documentation Best Practices

### README Structure
```markdown
# Project Name

## Overview
Brief description and architecture diagram

## Prerequisites
Required tools and permissions

## Setup
Step-by-step installation guide

## Development
Local development instructions

## Testing
How to run tests

## Deployment
Deployment process for each environment

## Monitoring
Links to dashboards and metrics

## Troubleshooting
Common issues and solutions
```

### Architecture Documentation
- Include diagrams (draw.io/PlantUML)
- Document design decisions
- Keep configuration examples
- Maintain runbooks