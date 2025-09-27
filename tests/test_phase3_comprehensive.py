#!/usr/bin/env python3
"""
Phase 3 Comprehensive Test Suite for Synapse Project
Tests end-to-end functionality, monitoring, and production readiness
"""

import json
import requests
import boto3
import time
import os
from typing import Dict, Any, Optional

class SynapseTestSuite:
    def __init__(self):
        self.cloudformation = boto3.client('cloudformation')
        self.lambda_client = boto3.client('lambda')
        self.cloudwatch = boto3.client('cloudwatch')
        self.stack_name = 'synapse-project'
        self.api_endpoint = None
        self.function_names = {}
        
    def setup(self):
        """Initialize test environment and get stack resources"""
        print("🔧 Setting up test environment...")
        
        # Get stack resources
        try:
            resources = self.cloudformation.list_stack_resources(
                StackName=self.stack_name
            )['StackResourceSummaries']
            
            for resource in resources:
                if resource['ResourceType'] == 'AWS::Lambda::Function':
                    logical_id = resource['LogicalResourceId']
                    physical_id = resource['PhysicalResourceId']
                    self.function_names[logical_id] = physical_id
                    
            # Get API Gateway endpoint
            try:
                outputs = self.cloudformation.describe_stacks(
                    StackName=self.stack_name
                )['Stacks'][0].get('Outputs', [])
                
                for output in outputs:
                    if 'Webhook' in output['OutputKey']:
                        self.api_endpoint = output['OutputValue']
                        break
            except:
                print("⚠️  API Gateway endpoint not found in outputs")
                
            print(f"✓ Found {len(self.function_names)} Lambda functions")
            if self.api_endpoint:
                print(f"✓ API endpoint: {self.api_endpoint}")
            else:
                print("⚠️  API endpoint not available yet")
                
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
            
        return True
    
    def test_lambda_functions(self):
        """Test individual Lambda functions"""
        print("\n🧪 Testing Lambda Functions...")
        results = {}
        
        # Test Scraper Function
        if 'ScraperFunction' in self.function_names:
            print("  Testing Scraper Function...")
            try:
                response = self.lambda_client.invoke(
                    FunctionName=self.function_names['ScraperFunction'],
                    Payload=json.dumps({
                        "url": "https://example.com"
                    })
                )
                
                result = json.loads(response['Payload'].read())
                if response['StatusCode'] == 200:
                    print("  ✓ Scraper Function: PASS")
                    results['scraper'] = 'PASS'
                else:
                    print(f"  ❌ Scraper Function: FAIL - {result}")
                    results['scraper'] = 'FAIL'
                    
            except Exception as e:
                print(f"  ❌ Scraper Function: ERROR - {e}")
                results['scraper'] = 'ERROR'
        
        # Test CRM Function
        if 'CrmFunction' in self.function_names:
            print("  Testing CRM Function...")
            try:
                test_payload = {
                    "lead_data": {
                        "first_name": "Test",
                        "last_name": "User",
                        "email1": "test@example.com",
                        "account_name": "Test Company",
                        "description": "Test lead from Phase 3"
                    }
                }
                
                response = self.lambda_client.invoke(
                    FunctionName=self.function_names['CrmFunction'],
                    Payload=json.dumps(test_payload)
                )
                
                result = json.loads(response['Payload'].read())
                if response['StatusCode'] == 200:
                    print("  ✓ CRM Function: PASS")
                    results['crm'] = 'PASS'
                else:
                    print(f"  ❌ CRM Function: FAIL - {result}")
                    results['crm'] = 'FAIL'
                    
            except Exception as e:
                print(f"  ❌ CRM Function: ERROR - {e}")
                results['crm'] = 'ERROR'
        
        return results
    
    def test_webhook_endpoints(self):
        """Test webhook endpoints if API Gateway is available"""
        print("\n🌐 Testing Webhook Endpoints...")
        
        if not self.api_endpoint:
            print("  ⚠️  API Gateway endpoint not available, skipping webhook tests")
            return {}
            
        results = {}
        
        # Test generic webhook
        try:
            response = requests.post(
                f"{self.api_endpoint}/webhook",
                json={"text": "Test lead from Phase 3 testing"},
                timeout=30
            )
            
            if response.status_code == 200:
                print("  ✓ Generic Webhook: PASS")
                results['generic_webhook'] = 'PASS'
            else:
                print(f"  ❌ Generic Webhook: FAIL - {response.status_code}")
                results['generic_webhook'] = 'FAIL'
                
        except Exception as e:
            print(f"  ❌ Generic Webhook: ERROR - {e}")
            results['generic_webhook'] = 'ERROR'
        
        # Test email webhook
        try:
            email_payload = {
                "from": "test@example.com",
                "subject": "Test Lead Inquiry",
                "text": "Hi, I'm interested in your CRM solution. Please contact me."
            }
            
            response = requests.post(
                f"{self.api_endpoint}/webhook/email",
                json=email_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                print("  ✓ Email Webhook: PASS")
                results['email_webhook'] = 'PASS'
            else:
                print(f"  ❌ Email Webhook: FAIL - {response.status_code}")
                results['email_webhook'] = 'FAIL'
                
        except Exception as e:
            print(f"  ❌ Email Webhook: ERROR - {e}")
            results['email_webhook'] = 'ERROR'
        
        return results
    
    def test_monitoring_setup(self):
        """Test CloudWatch monitoring and metrics"""
        print("\n📊 Testing Monitoring Setup...")
        results = {}
        
        try:
            # Check if metrics are being generated
            metrics = self.cloudwatch.list_metrics(
                Namespace='AWS/Lambda',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': list(self.function_names.values())[0] if self.function_names else 'test'
                    }
                ]
            )
            
            if metrics['Metrics']:
                print("  ✓ CloudWatch Metrics: Available")
                results['metrics'] = 'PASS'
            else:
                print("  ⚠️  CloudWatch Metrics: Not yet available (may take time)")
                results['metrics'] = 'PENDING'
                
        except Exception as e:
            print(f"  ❌ CloudWatch Metrics: ERROR - {e}")
            results['metrics'] = 'ERROR'
        
        return results
    
    def test_suitecrm_integration(self):
        """Test SuiteCRM integration"""
        print("\n🔗 Testing SuiteCRM Integration...")
        
        try:
            # Test if SuiteCRM secret exists
            secrets_client = boto3.client('secretsmanager')
            secret = secrets_client.get_secret_value(SecretId='Synapse/SuiteCRM')
            
            if secret:
                print("  ✓ SuiteCRM Credentials: Available")
                
                # Parse credentials
                creds = json.loads(secret['SecretString'])
                if all(key in creds for key in ['url', 'client_id', 'client_secret']):
                    print("  ✓ SuiteCRM Credentials: Valid format")
                    return {'suitecrm_config': 'PASS'}
                else:
                    print("  ❌ SuiteCRM Credentials: Invalid format")
                    return {'suitecrm_config': 'FAIL'}
                    
        except Exception as e:
            print(f"  ❌ SuiteCRM Integration: ERROR - {e}")
            return {'suitecrm_config': 'ERROR'}
    
    def generate_report(self, test_results: Dict[str, Dict[str, str]]):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("📋 PHASE 3 COMPREHENSIVE TEST REPORT")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for category, results in test_results.items():
            print(f"\n{category.upper()}:")
            for test_name, status in results.items():
                total_tests += 1
                if status == 'PASS':
                    passed_tests += 1
                    print(f"  ✓ {test_name}: {status}")
                elif status == 'FAIL':
                    print(f"  ❌ {test_name}: {status}")
                elif status == 'ERROR':
                    print(f"  🚨 {test_name}: {status}")
                else:
                    print(f"  ⚠️  {test_name}: {status}")
        
        print(f"\n📊 SUMMARY: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! System is ready for production.")
        elif passed_tests >= total_tests * 0.8:
            print("⚠️  Most tests passed. Review failed tests before production.")
        else:
            print("❌ Multiple test failures. System needs attention before production.")
        
        return passed_tests / total_tests if total_tests > 0 else 0

def main():
    """Run comprehensive Phase 3 test suite"""
    print("🚀 Starting Phase 3 Comprehensive Test Suite...")
    
    suite = SynapseTestSuite()
    
    if not suite.setup():
        print("❌ Test setup failed. Exiting.")
        return
    
    # Run all test categories
    test_results = {}
    
    test_results['lambda_functions'] = suite.test_lambda_functions()
    test_results['webhook_endpoints'] = suite.test_webhook_endpoints()
    test_results['monitoring'] = suite.test_monitoring_setup()
    test_results['suitecrm'] = suite.test_suitecrm_integration()
    
    # Generate final report
    success_rate = suite.generate_report(test_results)
    
    # Exit with appropriate code
    exit(0 if success_rate >= 0.8 else 1)

if __name__ == "__main__":
    main()