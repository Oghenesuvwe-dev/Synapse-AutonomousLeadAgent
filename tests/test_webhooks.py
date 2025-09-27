#!/usr/bin/env python3
"""
Test script for webhook functionality
"""
import json
import sys
import os
import boto3
from moto import mock_bedrock_agent_runtime
import pytest

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from webhook import (
    determine_trigger_type_and_extract_content,
    extract_email_content,
    extract_slack_content,
    extract_generic_content,
    parse_form_data,
    generate_session_id,
    format_response_for_trigger
)


class TestWebhookParsing:
    """Test webhook content parsing functionality"""
    
    def test_email_trigger_detection(self):
        """Test email trigger type detection"""
        event = {"path": "/webhook/email", "body": "{}"}
        trigger_type, content = determine_trigger_type_and_extract_content(event)
        assert trigger_type == "email"
    
    def test_slack_trigger_detection(self):
        """Test Slack trigger type detection"""
        event = {"path": "/webhook/slack", "body": "{}"}
        trigger_type, content = determine_trigger_type_and_extract_content(event)
        assert trigger_type == "slack"
    
    def test_generic_trigger_detection(self):
        """Test generic trigger type detection"""
        event = {"path": "/webhook", "body": "{}"}
        trigger_type, content = determine_trigger_type_and_extract_content(event)
        assert trigger_type == "generic"
    
    def test_email_content_extraction(self):
        """Test email content extraction"""
        event = {
            "body": json.dumps({
                "from": "sarah.johnson@techcorp.com",
                "subject": "CRM Solution Inquiry",
                "text": "We need a CRM solution for our team"
            })
        }
        content = extract_email_content(event)
        assert "sarah.johnson@techcorp.com" in content
        assert "CRM Solution Inquiry" in content
        assert "We need a CRM solution" in content
    
    def test_slack_content_extraction_command(self):
        """Test Slack slash command content extraction"""
        event = {
            "body": "command=/lead&text=New lead from ABC Corp&user_name=john"
        }
        content = extract_slack_content(event)
        assert "/lead" in content
        assert "New lead from ABC Corp" in content
        assert "john" in content
    
    def test_slack_content_extraction_json(self):
        """Test Slack JSON event content extraction"""
        event = {
            "body": json.dumps({
                "event": {
                    "type": "message",
                    "text": "New lead inquiry",
                    "user": "U123456"
                }
            })
        }
        content = extract_slack_content(event)
        assert "message" in content
        assert "New lead inquiry" in content
        assert "U123456" in content
    
    def test_generic_content_extraction(self):
        """Test generic content extraction"""
        event = {
            "body": json.dumps({
                "text": "Generic webhook content",
                "source": "website"
            })
        }
        content = extract_generic_content(event)
        assert "Generic webhook content" in content
    
    def test_form_data_parsing(self):
        """Test URL-encoded form data parsing"""
        form_data = "command=%2Flead&text=New%20lead&user_name=john"
        parsed = parse_form_data(form_data)
        assert parsed["command"] == "/lead"
        assert parsed["text"] == "New lead"
        assert parsed["user_name"] == "john"
    
    def test_session_id_generation(self):
        """Test session ID generation"""
        event = {"body": json.dumps({"user": "test_user"})}
        session_id = generate_session_id("slack", event)
        assert session_id.startswith("slack-")
        assert len(session_id) > 10
    
    def test_slack_response_formatting(self):
        """Test Slack response formatting"""
        agent_response = json.dumps({
            "summary": "High-value enterprise lead",
            "priority": "High",
            "action": "create_lead"
        })
        formatted = format_response_for_trigger("slack", agent_response, "original content")
        assert isinstance(formatted, dict)
        assert "text" in formatted
        assert "attachments" in formatted
        assert formatted["attachments"][0]["color"] == "good"  # High priority = green
    
    def test_email_response_formatting(self):
        """Test email response formatting"""
        agent_response = json.dumps({
            "summary": "Medium priority lead",
            "priority": "Medium"
        })
        formatted = format_response_for_trigger("email", agent_response, "original content")
        assert isinstance(formatted, str)
        assert "Medium priority" in formatted
    
    def test_generic_response_formatting(self):
        """Test generic response formatting"""
        agent_response = "Lead processed successfully"
        formatted = format_response_for_trigger("generic", agent_response, "original content")
        assert formatted == agent_response


def test_sample_email_webhook():
    """Test with sample email webhook payload"""
    with open('infra/events/sample-email-webhook.json', 'r') as f:
        sample_event = json.load(f)
    
    trigger_type, content = determine_trigger_type_and_extract_content(sample_event)
    assert trigger_type == "email"
    assert "sarah.johnson@techcorp.com" in content
    assert "VP of Engineering" in content
    assert "techcorp.com" in content


def test_sample_slack_webhook():
    """Test with sample Slack webhook payload"""
    with open('infra/events/sample-slack-webhook.json', 'r') as f:
        sample_event = json.load(f)
    
    trigger_type, content = determine_trigger_type_and_extract_content(sample_event)
    assert trigger_type == "slack"
    assert "/lead" in content
    assert "ABC Marketing" in content
    assert "john.smith" in content


if __name__ == "__main__":
    # Run basic tests
    test_class = TestWebhookParsing()
    
    print("Running webhook parsing tests...")
    
    try:
        test_class.test_email_trigger_detection()
        print("✓ Email trigger detection")
        
        test_class.test_slack_trigger_detection()
        print("✓ Slack trigger detection")
        
        test_class.test_generic_trigger_detection()
        print("✓ Generic trigger detection")
        
        test_class.test_email_content_extraction()
        print("✓ Email content extraction")
        
        test_class.test_slack_content_extraction_command()
        print("✓ Slack command extraction")
        
        test_class.test_form_data_parsing()
        print("✓ Form data parsing")
        
        test_class.test_session_id_generation()
        print("✓ Session ID generation")
        
        test_class.test_slack_response_formatting()
        print("✓ Slack response formatting")
        
        test_class.test_email_response_formatting()
        print("✓ Email response formatting")
        
        test_sample_email_webhook()
        print("✓ Sample email webhook")
        
        test_sample_slack_webhook()
        print("✓ Sample Slack webhook")
        
        print("\n🎉 All webhook tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)