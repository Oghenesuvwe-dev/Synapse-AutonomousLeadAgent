#!/usr/bin/env python3
"""
Standalone test for webhook logic without external dependencies
"""
import json
import re
from urllib.parse import unquote_plus
from typing import Dict, Any, Tuple


def determine_trigger_type_and_extract_content(event: Dict[str, Any]) -> Tuple[str, str]:
    """Determine the trigger type and extract relevant content."""
    path = event.get("path", "")
    if "/webhook/email" in path:
        return "email", extract_email_content(event)
    elif "/webhook/slack" in path:
        return "slack", extract_slack_content(event)
    else:
        return "generic", extract_generic_content(event)


def extract_email_content(event: Dict[str, Any]) -> str:
    """Extract content from email webhook payload."""
    try:
        body = event.get("body", "")
        if isinstance(body, str):
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = parse_form_data(body)
        else:
            payload = body or {}

        extracted_parts = []
        
        # Extract subject
        subject = payload.get("subject", "")
        if subject:
            extracted_parts.append(f"Subject: {subject}")
        
        # Extract sender
        sender = payload.get("from", payload.get("sender", ""))
        if sender:
            extracted_parts.append(f"From: {sender}")
        
        # Extract main content
        content_fields = ["text", "plain", "body-plain", "stripped-text", "message", "content"]
        for field in content_fields:
            if field in payload and payload[field]:
                content = payload[field]
                if isinstance(content, str) and content.strip():
                    extracted_parts.append(f"Content: {content.strip()}")
                    break
        
        return "\n".join(extracted_parts) if extracted_parts else str(body)
        
    except Exception as e:
        return str(event.get("body", ""))


def extract_slack_content(event: Dict[str, Any]) -> str:
    """Extract content from Slack webhook payload."""
    try:
        body = event.get("body", "")
        if isinstance(body, str):
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = parse_form_data(body)
        else:
            payload = body or {}

        # Handle Slack slash commands
        if "command" in payload:
            command = payload.get("command", "")
            text = payload.get("text", "")
            user = payload.get("user_name", "")
            return f"Slack command {command} from {user}: {text}"
        
        # Handle Slack events API
        if "event" in payload:
            event_data = payload["event"]
            event_type = event_data.get("type", "")
            text = event_data.get("text", "")
            user = event_data.get("user", "")
            return f"Slack {event_type} from {user}: {text}"
        
        # Handle direct message format
        text_fields = ["text", "message", "content"]
        for field in text_fields:
            if field in payload and payload[field]:
                user = payload.get("user_name", payload.get("user", ""))
                content = payload[field]
                return f"Slack message from {user}: {content}"
        
        return str(body)
        
    except Exception as e:
        return str(event.get("body", ""))


def extract_generic_content(event: Dict[str, Any]) -> str:
    """Extract content from generic webhook payload."""
    try:
        body = event.get("body", "")
        
        if isinstance(body, str):
            try:
                payload = json.loads(body)
                text_fields = ["text", "message", "content", "body", "description"]
                for field in text_fields:
                    if field in payload and payload[field]:
                        return str(payload[field])
                return json.dumps(payload, indent=2)
            except json.JSONDecodeError:
                return body
        elif isinstance(body, dict):
            text_fields = ["text", "message", "content", "body", "description"]
            for field in text_fields:
                if field in body and body[field]:
                    return str(body[field])
            return json.dumps(body, indent=2)
        else:
            return str(body)
            
    except Exception as e:
        return str(event)


def parse_form_data(body: str) -> Dict[str, str]:
    """Parse URL-encoded form data."""
    try:
        pairs = body.split('&')
        result = {}
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                result[unquote_plus(key)] = unquote_plus(value)
        return result
    except Exception as e:
        return {}


def run_tests():
    """Run all webhook logic tests"""
    print("Running webhook logic tests...\n")
    
    passed = 0
    failed = 0
    
    # Test 1: Email trigger detection
    try:
        event = {"path": "/webhook/email", "body": "{}"}
        trigger_type, content = determine_trigger_type_and_extract_content(event)
        assert trigger_type == "email", f"Expected 'email', got '{trigger_type}'"
        print("✓ Email trigger detection")
        passed += 1
    except Exception as e:
        print(f"❌ Email trigger detection failed: {e}")
        failed += 1
    
    # Test 2: Slack trigger detection
    try:
        event = {"path": "/webhook/slack", "body": "{}"}
        trigger_type, content = determine_trigger_type_and_extract_content(event)
        assert trigger_type == "slack", f"Expected 'slack', got '{trigger_type}'"
        print("✓ Slack trigger detection")
        passed += 1
    except Exception as e:
        print(f"❌ Slack trigger detection failed: {e}")
        failed += 1
    
    # Test 3: Generic trigger detection
    try:
        event = {"path": "/webhook", "body": "{}"}
        trigger_type, content = determine_trigger_type_and_extract_content(event)
        assert trigger_type == "generic", f"Expected 'generic', got '{trigger_type}'"
        print("✓ Generic trigger detection")
        passed += 1
    except Exception as e:
        print(f"❌ Generic trigger detection failed: {e}")
        failed += 1
    
    # Test 4: Email content extraction
    try:
        event = {
            "body": json.dumps({
                "from": "sarah.johnson@techcorp.com",
                "subject": "CRM Solution Inquiry",
                "text": "We need a CRM solution for our team"
            })
        }
        content = extract_email_content(event)
        assert "sarah.johnson@techcorp.com" in content, "Email address not found"
        assert "CRM Solution Inquiry" in content, "Subject not found"
        assert "We need a CRM solution" in content, "Body text not found"
        print("✓ Email content extraction")
        passed += 1
    except Exception as e:
        print(f"❌ Email content extraction failed: {e}")
        failed += 1
    
    # Test 5: Slack content extraction
    try:
        event = {
            "body": "command=/lead&text=New%20lead%20from%20ABC%20Corp&user_name=john"
        }
        content = extract_slack_content(event)
        assert "/lead" in content, "Command not found"
        assert "New lead from ABC Corp" in content, "Text not found"
        assert "john" in content, "User name not found"
        print("✓ Slack content extraction")
        passed += 1
    except Exception as e:
        print(f"❌ Slack content extraction failed: {e}")
        failed += 1
    
    # Test 6: Form data parsing
    try:
        form_data = "command=%2Flead&text=New%20lead&user_name=john"
        parsed = parse_form_data(form_data)
        assert parsed["command"] == "/lead", f"Expected '/lead', got '{parsed.get('command')}'"
        assert parsed["text"] == "New lead", f"Expected 'New lead', got '{parsed.get('text')}'"
        assert parsed["user_name"] == "john", f"Expected 'john', got '{parsed.get('user_name')}'"
        print("✓ Form data parsing")
        passed += 1
    except Exception as e:
        print(f"❌ Form data parsing failed: {e}")
        failed += 1
    
    # Test 7: Sample email webhook
    try:
        with open('../infra/events/sample-email-webhook.json', 'r') as f:
            sample_event = json.load(f)
        
        trigger_type, content = determine_trigger_type_and_extract_content(sample_event)
        assert trigger_type == "email", f"Expected 'email', got '{trigger_type}'"
        assert "sarah.johnson@techcorp.com" in content, "Email address not found"
        assert "VP of Engineering" in content, "Title not found"
        print("✓ Sample email webhook")
        passed += 1
    except FileNotFoundError:
        print("⚠ Sample email webhook file not found, skipping test")
    except Exception as e:
        print(f"❌ Sample email webhook failed: {e}")
        failed += 1
    
    # Test 8: Sample Slack webhook
    try:
        with open('../infra/events/sample-slack-webhook.json', 'r') as f:
            sample_event = json.load(f)
        
        trigger_type, content = determine_trigger_type_and_extract_content(sample_event)
        assert trigger_type == "slack", f"Expected 'slack', got '{trigger_type}'"
        assert "/lead" in content, "Command not found"
        assert "ABC Marketing" in content, "Company name not found"
        print("✓ Sample Slack webhook")
        passed += 1
    except FileNotFoundError:
        print("⚠ Sample Slack webhook file not found, skipping test")
    except Exception as e:
        print(f"❌ Sample Slack webhook failed: {e}")
        failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All webhook logic tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_tests())