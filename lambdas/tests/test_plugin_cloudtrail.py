import json
import os
import unittest
from pathlib import Path

from utils.plugins import register_plugins, send_event_to_plugins

SAMPLES_DIR = Path(__file__).parent / "samples"


def _normalize(event):
    """Run an event through the full normalization pipeline."""
    metadata = {"something": "something"}
    plugins = register_plugins("normalization_plugins")
    result, metadata = send_event_to_plugins(event, metadata, plugins)
    return result


class TestPluginCloudtrail(unittest.TestCase):
    """Tests for the generic CloudTrail normalization plugin."""

    def setup_method(self, method):
        pass

    # --- Console Login ---

    def test_console_login_summary(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_console_login.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert result["summary"] == "someone ConsoleLogin from 98.9.3.133 in us-east-2"

    def test_console_login_category(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_console_login.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert result["category"] == "authentication"

    def test_console_login_tags(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_console_login.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert "cloudtrail" in result["tags"]
        assert "aws" in result["tags"]
        assert "write" in result["tags"]
        assert "management" in result["tags"]
        assert "signin" in result["tags"]
        assert "login-success" in result["tags"]

    def test_console_login_mfa(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_console_login.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert result["details"]["_mfa_used"] is True
        assert result["details"]["_login_result"] == "Success"

    def test_console_login_severity(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_console_login.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert result["severity"] == "INFO"

    # --- Destructive action (DeleteBucket) ---

    def test_delete_bucket_summary(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_delete_bucket.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert result["summary"] == "admin DeleteBucket from 203.0.113.50 in us-west-2"

    def test_delete_bucket_category(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_delete_bucket.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert result["category"] == "storage"

    def test_delete_bucket_severity(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_delete_bucket.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert result["severity"] == "WARNING"

    def test_delete_bucket_tags(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_delete_bucket.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert "s3" in result["tags"]
        assert "write" in result["tags"]

    # --- Failed API call (AssumedRole, error) ---

    def test_failed_api_summary(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_failed_api_call.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert (
            result["summary"]
            == "session-user DescribeInstances from 198.51.100.10 in eu-west-1"
        )

    def test_failed_api_category(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_failed_api_call.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert result["category"] == "compute"

    def test_failed_api_severity(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_failed_api_call.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert result["severity"] == "WARNING"

    def test_failed_api_error_tags(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_failed_api_call.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert "error" in result["tags"]
        assert "read" in result["tags"]
        assert "ec2" in result["tags"]
        assert result["details"]["_errorcode"] == "UnauthorizedAccess"

    # --- Existing CreateLogStream sample still works ---

    def test_create_log_stream(self):
        with open(SAMPLES_DIR / "sample_cloudtrail_create_log_stream.json") as f:
            event = json.load(f)
        result = _normalize(event)
        assert (
            result["summary"]
            == "some_lambda CreateLogStream from 54.21.12.27 in us-west-2"
        )
        assert result["category"] == "logging"
        assert "cloudtrail" in result["tags"]

    # --- Non-cloudtrail events are not modified ---

    def test_non_cloudtrail_passthrough(self):
        event = {
            "source": "syslog",
            "tags": [],
            "details": {
                "eventsource": "something.amazonaws.com",
                "eventname": "SomeAction",
            },
        }
        result = _normalize(event)
        # summary should still be UNKNOWN (set by event_shell, not changed by cloudtrail plugin)
        assert result["summary"] == "UNKNOWN"
        assert "cloudtrail" not in result["tags"]
