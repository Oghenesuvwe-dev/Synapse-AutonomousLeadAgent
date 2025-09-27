#!/usr/bin/env python3
"""
Simple test script for webhook functionality (no external dependencies)
"""
import json
import sys
import os

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


def test_email_trigger_detection():
    """Test email trigger type detection"""
    event = {"path": "/webhook/email", "body": "{}"}
    trigger_type, content = determine_trigger_type_and_extract_content(event)
    assert trigger_type == "email", f"Expected 'email', got '{trigger_type}'"
    print("✓ Email trigger detection")


def test_slack_trigger_detection():
    """Test Slack trigger type detection"""
    event = {"path": "/webhook/slack", "body": "{}"}
    trigger_type, content = determine_trigger_type_and_extract_content(event)
    assert trigger_type == "slack", f"Expected 'slack', got '{trigger_type}'"
    print("✓ Slack trigger detection")


def test_generic_trigger_detection():
    """Test generic trigger type detection"""
    event = {"path": "/webhook", "body": "{}"}
    trigger_type, content = determine_trigger_type_and_extract_content(event)
    assert trigger_type == "generic", f"Expected 'generic', got '{trigger_type}'"
    print("✓ Generic trigger detection")


def test_email_content_extraction():
    """Test email content extraction"""
    event = {
        "body": json.dumps({
            "from": "sarah.johnson@techcorp.com",
            "subject": "CRM Solution Inquiry",
            "text": "We need a CRM solution for our team"
        })
    }
    content = extract_email_content(event)
    assert "sarah.johnson@techcorp.com" in content, "Email address not found in content"
    assert "CRM Solution Inquiry" in content, "Subject not found in content"
    assert "We need a CRM solution" in content, "Body text not found in content"
    print("✓ Email content extraction")


def test_slack_content_extraction_command():
    """Test Slack slash command content extraction"""
    event = {
        "body": "command=/lead&text=New lead from ABC Corp&user_name=john"
    }
    content = extract_slack_content(event)
    assert "/lead" in content, "Command not found in content"
    assert "New lead from ABC Corp" in content, "Text not found in content"
    assert "john" in content, "User name not found in content"
    print("✓ Slack command extraction")


def test_form_data_parsing():
    """Test URL-encoded form data parsing"""
    form_data = "command=%2Flead&text=New%20lead&user_name=john"
    parsed = parse_form_data(form_data)
    assert parsed["command"] == "/lead", f"Expected '/lead', got '{parsed.get('command')}'"
    assert parsed["text"] == "New lead", f"Expected 'New lead', got '{parsed.get('text')}'"
    assert parsed["user_name"] == "john", f"Expected 'john', got '{parsed.get('user_name')}'"
    print("✓ Form data parsing")


def test_session_id_generation():
    """Test session ID generation"""
    event = {"body": json.dumps({"user": "test_user"})}
    session_id = generate_session_id("slack", event)
    assert session_id.startswith("slack-"), f"Session ID should start with 'slack-', got '{session_id}'"
    assert len(session_id) > 10, f"Session ID should be longer than 10 chars, got {len(session_id)}"
    print("✓ Session ID generation")


def test_slack_response_formatting():
    """Test Slack response formatting"""
    agent_response = json.dumps({
        "summary": "High-value enterprise lead",
        "priority": "High",
        "action": "create_lead"
    })
    formatted = format_response_for_trigger("slack", agent_response, "original content")
    assert isinstance(formatted, dict), "Slack response should be a dictionary"
    assert "text" in formatted, "Slack response should have 'text' field"
    assert "attachments" in formatted, "Slack response should have 'attachments' field"
    print("✓ Slack response formatting")


def test_email_response_formatting():
    """Test email response formatting"""
    agent_response = json.dumps({
        "summary": "Medium priority lead",
        "priority": "Medium"
    })
    formatted = format_response_for_trigger("email", agent_response, "original content")
    assert isinstance(formatted, str), "Email response should be a string"
    assert "Medium priority" in formatted, "Priority should be mentioned in response"
    print("✓ Email response formatting")


def test_sample_email_webhook():
    """Test with sample email webhook payload"""
    try:
        with open('infra/events/sample-email-webhook.json', 'r') as f:
            sample_event = json.load(f)
        
        trigger_type, content = determine_trigger_type_and_extract_content(sample_event)
        assert trigger_type == "email", f"Expected 'email', got '{trigger_type}'"
        assert "sarah.johnson@techcorp.com" in content, "Email address not found"
        assert "VP of Engineering" in content, "Title not found"
        assert "techcorp.com" in content, "Company domain not found"
        print("✓ Sample email webhook")
    except FileNotFoundError:
        print("⚠ Sample email webhook file not found, skipping test")


def test_sample_slack_webhook():
    """Test with sample Slack webhook payload"""
    try:
        with open('infra/events/sample-slack-webhook.json', 'r') as f:
            sample_event = json.load(f)
        
        trigger_type, content = determine_trigger_type_and_extract_content(sample_event)
        assert trigger_type == "slack", f"Expected 'slack', got '{trigger_type}'"
        assert "/lead" in content, "Command not found"
        assert "ABC Marketing" in content, "Company name not found"
        assert "john.smith" in content, "User name not found"
        print("✓ Sample Slack webhook")
    except FileNotFoundError:
        print("⚠ Sample Slack webhook file not found, skipping test")


def main():
    """Run all tests"""
    print("Running webhook parsing tests...\n")
    
    tests = [
        test_email_trigger_detection,
        test_slack_trigger_detection,
        test_generic_trigger_detection,
        test_email_content_extraction,
        test_slack_content_extraction_command,
        test_form_data_parsing,
        test_session_id_generation,
        test_slack_response_formatting,
        test_email_response_formatting,
        test_sample_email_webhook,
        test_sample_slack_webhook
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {str(e)}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All webhook tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())