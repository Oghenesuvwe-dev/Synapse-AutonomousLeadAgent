#!/bin/bash

# Synapse Project Deployment Script
set -e

echo "🚀 Starting Synapse Project Deployment..."

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

# Package the Lambda functions
echo "📦 Packaging Lambda functions..."
cd lambda
zip -r ../lambda-package.zip . -x "*.pyc" "__pycache__/*"
cd ..

# Upload Lambda package to S3
echo "⬆️  Uploading Lambda package to S3..."
aws s3 cp lambda-package.zip s3://$BUCKET_NAME/lambda-package.zip

# Update the CloudFormation template to use the S3 package
echo "🔧 Updating template with S3 references..."
sed "s|CodeUri: ../lambda/|CodeUri: s3://$BUCKET_NAME/lambda-package.zip|g" infra/template.yaml > infra/template-deploy.yaml

# Deploy the CloudFormation stack
echo "🚀 Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file infra/template-deploy.yaml \
    --stack-name synapse-project \
    --capabilities CAPABILITY_IAM \
    --region $REGION \
    --disable-rollback \
    --parameter-overrides DeploymentBucket=$BUCKET_NAME

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "📋 Stack outputs:"
    aws cloudformation describe-stacks --stack-name synapse-project --query 'Stacks[0].Outputs' --output table
else
    echo "❌ Deployment failed!"
    exit 1
fi

# Clean up
echo "🧹 Cleaning up temporary files..."
rm -f lambda-package.zip infra/template-deploy.yaml

echo "🎉 Deployment complete!"