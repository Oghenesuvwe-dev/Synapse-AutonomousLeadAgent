#!/usr/bin/env python3
"""
Direct component testing script for Synapse project
Tests individual Lambda functions without Bedrock Agent dependency
"""

import json
import boto3
import time
from typing import Dict, Any

class SynapseComponentTest:
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        self.cloudformation = boto3.client('cloudformation')
        
        # Get function names from CloudFormation stack
        self.stack_name = 'synapse-project'
        self.scraper_function = None
        self.crm_function = None
        
        self._get_stack_resources()
    
    def _get_stack_resources(self):
        """Get resource names from CloudFormation stack"""
        try:
            response = self.cloudformation.describe_stack_resources(
                StackName=self.stack_name
            )
            
            for resource in response['StackResources']:
                if resource['ResourceType'] == 'AWS::Lambda::Function':
                    if 'ScraperFunction' in resource['LogicalResourceId']:
                        self.scraper_function = resource['PhysicalResourceId']
                    elif 'CrmFunction' in resource['LogicalResourceId']:
                        self.crm_function = resource['PhysicalResourceId']
                        
            print(f"✓ Found resources:")
            print(f"  Scraper Function: {self.scraper_function}")
            print(f"  CRM Function: {self.crm_function}")
            
        except Exception as e:
            print(f"❌ Error getting stack resources: {e}")
            raise
    
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
                    print(f"  Response: {result}")
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
                    print(f"  Response: {result}")
                    return {'success': True, 'result': result}
            else:
                print(f"❌ HTTP Error {response['StatusCode']}")
                return {'success': False, 'error': f"HTTP {response['StatusCode']}"}
                
        except Exception as e:
            print(f"❌ Error invoking CRM function: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_component_tests(self):
        """Run direct component tests"""
        print("🚀 Starting Component Tests...")
        
        test_results = {
            'scraper_test': None,
            'crm_test': None
        }
        
        # Test 1: Scraper Function
        print("\n" + "="*50)
        print("TEST 1: Direct Scraper Function")
        print("="*50)
        test_results['scraper_test'] = self.test_scraper_function("https://example.com")
        
        # Test 2: CRM Function (with mock data since we don't have real SuiteCRM)
        print("\n" + "="*50)
        print("TEST 2: Direct CRM Function")
        print("="*50)
        sample_lead = {
            "first_name": "John",
            "last_name": "Doe",
            "email1": "john.doe@example.com",
            "account_name": "Example Corp",
            "description": "Test lead from component testing"
        }
        test_results['crm_test'] = self.test_crm_function(sample_lead)
        
        # Print summary
        print("\n" + "="*50)
        print("COMPONENT TEST SUMMARY")
        print("="*50)
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result and result.get('success'))
        
        for test_name, result in test_results.items():
            status = "✓ PASS" if result and result.get('success') else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
            if result and not result.get('success'):
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} component tests passed")
        
        return test_results

def main():
    """Main test execution"""
    try:
        tester = SynapseComponentTest()
        results = tester.run_component_tests()
        
        # Exit with appropriate code
        success_count = sum(1 for r in results.values() if r and r.get('success'))
        if success_count == len(results):
            print("\n🎉 All component tests passed!")
            return 0
        else:
            print(f"\n❌ {len(results) - success_count} component tests failed")
            return 1
            
    except Exception as e:
        print(f"❌ Component test execution failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())