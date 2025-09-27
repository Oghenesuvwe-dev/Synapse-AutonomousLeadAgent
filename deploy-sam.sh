#!/bin/bash
set -e

echo "🚀 Starting Synapse Project Deployment with SAM..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Create a temporary S3 bucket for deployment artifacts if it doesn't exist
BUCKET_NAME="synapse-deployment-$(date +%s)-$(openssl rand -hex 4)"
REGION="us-east-1"

echo "📦 Creating deployment bucket: $BUCKET_NAME"
aws s3 mb s3://$BUCKET_NAME --region $REGION

echo "🔨 Building SAM application..."
sam build -t infra/template.yaml

echo "🚀 Deploying SAM application..."
sam deploy \
    --stack-name synapse-project \
    --s3-bucket $BUCKET_NAME \
    --capabilities CAPABILITY_IAM \
    --region $REGION \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "📋 Stack outputs:"
    aws cloudformation describe-stacks --stack-name synapse-project --query 'Stacks[0].Outputs' --output table
else
    echo "❌ Deployment failed!"
    exit 1
fi

echo "🧹 Deleting deployment bucket..."
aws s3 rb s3://$BUCKET_NAME --force

echo "🎉 Deployment complete!"