#!/usr/bin/env python3
"""
End-to-End Testing Script for Synapse Project
Tests the complete workflow from webhook to CRM integration
"""

import json
import boto3
import time
import requests
from typing import Dict, Any, Optional

class SynapseE2ETest:
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        self.logs_client = boto3.client('logs')
        self.cloudformation = boto3.client('cloudformation')
        
        # Get function names from CloudFormation stack
        self.stack_name = 'synapse-project'
        self.webhook_function = None
        self.scraper_function = None
        self.crm_function = None
        self.agent_id = None
        self.agent_alias_id = None
        
        self._get_stack_resources()
    
    def _get_stack_resources(self):
        """Get resource names from CloudFormation stack"""
        try:
            response = self.cloudformation.describe_stack_resources(
                StackName=self.stack_name
            )
            
            for resource in response['StackResources']:
                if resource['ResourceType'] == 'AWS::Lambda::Function':
                    if 'WebhookFunction' in resource['LogicalResourceId']:
                        self.webhook_function = resource['PhysicalResourceId']
                    elif 'ScraperFunction' in resource['LogicalResourceId']:
                        self.scraper_function = resource['PhysicalResourceId']
                    elif 'CrmFunction' in resource['LogicalResourceId']:
                        self.crm_function = resource['PhysicalResourceId']
                elif resource['ResourceType'] == 'AWS::Bedrock::Agent':
                    self.agent_id = resource['PhysicalResourceId']
                elif resource['ResourceType'] == 'AWS::Bedrock::AgentAlias':
                    self.agent_alias_id = resource['PhysicalResourceId']
                    
            print(f"✓ Found resources:")
            print(f"  Webhook Function: {self.webhook_function}")
            print(f"  Scraper Function: {self.scraper_function}")
            print(f"  CRM Function: {self.crm_function}")
            print(f"  Agent ID: {self.agent_id}")
            print(f"  Agent Alias ID: {self.agent_alias_id}")
            
        except Exception as e:
            print(f"❌ Error getting stack resources: {e}")
            raise
    
    def test_webhook_function(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Test webhook function directly"""
        print(f"\n🧪 Testing Webhook Function...")
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.webhook_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                if 'FunctionError' in response:
                    print(f"❌ Function Error: {result}")
                    return {'success': False, 'error': result}
                else:
                    print(f"✓ Webhook function executed successfully")
                    return {'success': True, 'result': result}
            else:
                print(f"❌ HTTP Error {response['StatusCode']}")
                return {'success': False, 'error': f"HTTP {response['StatusCode']}"}
                
        except Exception as e:
            print(f"❌ Error invoking webhook function: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_scraper_function(self, url: str) -> Dict[str, Any]:
        """Test scraper function directly"""
        print(f"\n🧪 Testing Scraper Function with URL: {url}")
        
        payload = {
            'requestBody': {
                'content': {
                    'application/json': json.dumps({'url': url})
                }
            },
            'actionGroup': 'ScraperActionGroup',
            'apiPath': '/scrape',
            'httpMethod': 'POST'
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.scraper_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                if 'FunctionError' in response:
                    print(f"❌ Function Error: {result}")
                    return {'success': False, 'error': result}
                else:
                    print(f"✓ Scraper function executed successfully")
                    return {'success': True, 'result': result}
            else:
                print(f"❌ HTTP Error {response['StatusCode']}")
                return {'success': False, 'error': f"HTTP {response['StatusCode']}"}
                
        except Exception as e:
            print(f"❌ Error invoking scraper function: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_crm_function(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test CRM function directly"""
        print(f"\n🧪 Testing CRM Function...")
        
        payload = {
            'requestBody': {
                'content': {
                    'application/json': json.dumps({'lead_data': lead_data})
                }
            },
            'actionGroup': 'CrmActionGroup',
            'apiPath': '/create_lead',
            'httpMethod': 'POST'
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.crm_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                if 'FunctionError' in response:
                    print(f"❌ Function Error: {result}")
                    return {'success': False, 'error': result}
                else:
                    print(f"✓ CRM function executed successfully")
                    return {'success': True, 'result': result}
            else:
                print(f"❌ HTTP Error {response['StatusCode']}")
                return {'success': False, 'error': f"HTTP {response['StatusCode']}"}
                
        except Exception as e:
            print(f"❌ Error invoking CRM function: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_function_logs(self, function_name: str, minutes: int = 5) -> list:
        """Get recent logs for a function"""
        log_group = f"/aws/lambda/{function_name}"
        
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (minutes * 60 * 1000)
            
            response = self.logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time
            )
            
            return [event['message'] for event in response.get('events', [])]
            
        except Exception as e:
            print(f"❌ Error getting logs for {function_name}: {e}")
            return []
    
    def run_full_workflow_test(self):
        """Run complete end-to-end workflow test"""
        print("🚀 Starting Full Workflow Test...")
        
        # Test data
        email_payload = {
            "httpMethod": "POST",
            "path": "/webhook/email",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "from": "sarah.johnson@techcorp.com",
                "subject": "CRM Solution Inquiry - Urgent",
                "text": "Hi, I'm Sarah Johnson, VP of Engineering at TechCorp (techcorp.com). We need a CRM solution for our 500+ person team. Budget approved."
            })
        }
        
        slack_payload = {
            "httpMethod": "POST",
            "path": "/webhook/slack",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "body": "command=/lead&text=New%20lead%3A%20ABC%20Marketing%20agency%20looking%20for%20CRM%20solution.%20Contact%3A%20john%40abcmarketing.co&user_name=john.smith"
        }
        
        test_results = {
            'email_webhook': None,
            'slack_webhook': None,
            'scraper_direct': None,
            'crm_direct': None
        }
        
        # Test 1: Email Webhook
        print("\n" + "="*50)
        print("TEST 1: Email Webhook Processing")
        print("="*50)
        test_results['email_webhook'] = self.test_webhook_function(email_payload)
        
        # Test 2: Slack Webhook
        print("\n" + "="*50)
        print("TEST 2: Slack Webhook Processing")
        print("="*50)
        test_results['slack_webhook'] = self.test_webhook_function(slack_payload)
        
        # Test 3: Scraper Function
        print("\n" + "="*50)
        print("TEST 3: Direct Scraper Function")
        print("="*50)
        test_results['scraper_direct'] = self.test_scraper_function("https://example.com")
        
        # Test 4: CRM Function
        print("\n" + "="*50)
        print("TEST 4: Direct CRM Function")
        print("="*50)
        sample_lead = {
            "first_name": "John",
            "last_name": "Doe",
            "email1": "john.doe@example.com",
            "account_name": "Example Corp",
            "description": "Test lead from E2E testing"
        }
        test_results['crm_direct'] = self.test_crm_function(sample_lead)
        
        # Print summary
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result and result.get('success'))
        
        for test_name, result in test_results.items():
            status = "✓ PASS" if result and result.get('success') else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
            if result and not result.get('success'):
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        # Get logs for failed tests
        if passed_tests < total_tests:
            print("\n" + "="*50)
            print("RECENT LOGS FOR DEBUGGING")
            print("="*50)
            
            for function_name in [self.webhook_function, self.scraper_function, self.crm_function]:
                if function_name:
                    print(f"\n--- Logs for {function_name} ---")
                    logs = self.get_function_logs(function_name)
                    for log in logs[-10:]:  # Last 10 log entries
                        print(log.strip())
        
        return test_results

def main():
    """Main test execution"""
    try:
        tester = SynapseE2ETest()
        results = tester.run_full_workflow_test()
        
        # Exit with appropriate code
        success_count = sum(1 for r in results.values() if r and r.get('success'))
        if success_count == len(results):
            print("\n🎉 All tests passed!")
            return 0
        else:
            print(f"\n❌ {len(results) - success_count} tests failed")
            return 1
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())