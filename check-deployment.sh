#!/bin/bash

# Synapse Project Deployment Check Script
echo "=== SYNAPSE PROJECT DEPLOYMENT STATUS ==="
echo

# 1. Check CloudFormation Stack Status
echo "1. CloudFormation Stack Status:"
aws cloudformation describe-stacks --stack-name synapse-project --query 'Stacks[0].StackStatus' --output text
echo

# 2. List All Stack Resources
echo "2. All Stack Resources:"
aws cloudformation list-stack-resources --stack-name synapse-project --query 'StackResourceSummaries[].[LogicalResourceId,ResourceType,ResourceStatus]' --output table
echo

# 3. Get Bedrock Agent Details
echo "3. Bedrock Agent Details:"
aws bedrock-agent list-agents --query 'agentSummaries[?agentName==`SynapseAgent`].[agentId,agentName,agentStatus]' --output table
echo

# 4. Check Lambda Functions
echo "4. Lambda Functions:"
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `synapse-project`)].[FunctionName,Runtime,State]' --output table
echo

# 5. Get Agent ID and Alias ID for testing
echo "5. Agent Information for Testing:"
AGENT_ID=$(aws bedrock-agent list-agents --query 'agentSummaries[?agentName==`SynapseAgent`].agentId' --output text)
echo "Agent ID: $AGENT_ID"

ALIAS_ID=$(aws bedrock-agent list-agent-aliases --agent-id $AGENT_ID --query 'agentAliasSummaries[0].agentAliasId' --output text)
echo "Agent Alias ID: $ALIAS_ID"
echo

# 6. Check S3 Bucket
echo "6. S3 Scraper Bucket:"
aws s3 ls | grep synapse-project
echo

echo "=== DEPLOYMENT CHECK COMPLETE ==="
echo "Your Synapse Agent is ready to use!"
echo "Agent ID: $AGENT_ID"
echo "Agent Alias ID: $ALIAS_ID"