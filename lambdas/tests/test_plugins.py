import pytest
import yaml
import json
import uuid
from utils.dotdict import DotDict
from utils.dates import toUTC


class TestLowerCaseKeys(object):
    def setup(self):
        from normalization_plugins.lowercase_keys import message

        self.plugin = message()

    def test_nochange(self):
        metadata = {"something": "else"}
        event = {"key1": "syslog", "tags": ["atag"]}
        result, metadata = self.plugin.onMessage(event, metadata)
        # in = out - plugin didn't modify it
        assert result == event

    def test_lower_a_key(self):
        metadata = {"something": "else"}
        event = {"KEY1": "syslog", "tags": ["atag"]}
        expected = {"key1": "syslog", "tags": ["atag"]}
        result, metadata = self.plugin.onMessage(event, metadata)
        # lower case the upper case key
        assert result == expected

    def test_lower_a_sub_key(self):
        metadata = {"something": "else"}
        event = {"KEY1": "syslog", "tags": ["atag"], "details": {"SUBKEY": "subvalue"}}
        expected = {
            "key1": "syslog",
            "tags": ["atag"],
            "details": {"subkey": "subvalue"},
        }
        result, metadata = self.plugin.onMessage(event, metadata)
        # lower case the upper case keys wherever they are
        assert result == expected


class TestEnsureEventID(object):
    def setup(self):
        from enrichment_plugins.ensure_eventid import message

        self.plugin = message()

    def test_ensure_event_id(self):
        metadata = {"something": "else"}
        event = {"key1": "syslog", "tags": ["atag"]}
        result, metadata = self.plugin.onMessage(event, metadata)
        assert "eventid" in result
        assert "eventid" in event
        assert type(uuid.UUID(event["eventid"])) == uuid.UUID


class TestEventShell(object):
    def setup(self):
        from normalization_plugins.event_shell import message

        self.plugin = message()

    def test_ensure_base_event_shell(self):
        # given a really empty message
        # does it get the base shell?
        # does it move any non base items to 'details'?
        metadata = {"something": "else"}
        event = {"key1": "syslog", "tags": ["atag"]}
        result, metadata = self.plugin.onMessage(event, metadata)
        assert "severity" in result
        assert "tags" in result
        assert "atag" in result["tags"]
        assert "key1" in result["details"]

    def test_ensure_complex_event_shell(self):
        # given a complex message
        # does it get the base shell?
        # does it move any non base items to 'details'?
        metadata = {"something": "else"}
        event = {
            "key1": "syslog",
            "tags": ["atag"],
            "complexkey": {"subkey": "subvalue"},
        }
        result, metadata = self.plugin.onMessage(event, metadata)
        assert "severity" in result
        assert "tags" in result
        assert "atag" in result["tags"]
        assert "key1" in result["details"]
        assert "complexkey" in result["details"]
        assert "subkey" in result["details"]["complexkey"]
