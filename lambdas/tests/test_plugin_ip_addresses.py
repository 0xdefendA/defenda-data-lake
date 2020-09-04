import pytest
import yaml
import json
import uuid
import logging, logging.config
from pathlib import Path
from utils.dotdict import DotDict
from utils.dates import toUTC

logging_config_file_path = Path(__file__).parent.joinpath("logging_config.yml")
with open(logging_config_file_path, "r") as fd:
    logging_config = yaml.safe_load(fd)
    logging.config.dictConfig(logging_config)
global logger
logger = logging.getLogger()


class TestPluginIpAddresses(object):
    def setup(self):
        from normalization_plugins.ip_addresses import message

        self.plugin = message()
        self.inbound_events = []
        self.normalized_events = []
        with open(
            "./lambdas/tests/samples/sample_cloudtrail_create_log_stream.json", "r"
        ) as f:
            self.inbound_events.append(json.loads(f.read()))
        with open(
            "./lambdas/tests/samples/sample_cloudfront_wordpress_probe.json", "r"
        ) as f:
            self.inbound_events.append(json.loads(f.read()))
        with open("./lambdas/tests/samples/sample_vpc_flow_log.json", "r") as f:
            self.inbound_events.append(json.loads(f.read()))
        # run the event through default plugins
        # to set the shell and lowercase all keys
        from normalization_plugins.event_shell import message as event_shell
        from normalization_plugins.lowercase_keys import message as lowercase_keys

        metadata = {"something": "else"}
        for event in self.inbound_events:
            event, metadata = event_shell().onMessage(event, metadata)
            event, metadata = lowercase_keys().onMessage(event, metadata)
            self.normalized_events.append(event)

    def test_nochange(self):
        metadata = {"something": "else"}
        event = {}
        # use an event without an ip
        # to test if the plugin is benign when it should not act
        with open("./lambdas/tests/samples/sample_syslog_sudo.json", "r") as f:
            event = json.loads(f.read())
        # make sure we have a valid, populated dict
        assert len(event.keys())
        result, metadata = self.plugin.onMessage(event, metadata)
        # in = out - plugin didn't modify it
        # since it doesn't match the normalized format
        # and won't find an ip field under 'details'

        assert result == event

    def test_structure(self):
        metadata = {"something": "else"}
        # use the normalized event
        for event in self.normalized_events:
            result, metadata = self.plugin.onMessage(event, metadata)
            assert "utctimestamp" in result
            assert "severity" in result
            assert "summary" in result
            assert "category" in result
            assert "source" in result
            assert "tags" in result
            assert "plugins" in result
            assert "details" in result
            # we should have a source or destination for these events
            assert (
                "sourceipaddress" in result["details"]
                or "destinationipaddress" in result["details"]
            )

    def test_values(self):
        metadata = {"something": "else"}
        # use normalized events
        # we know the end result for
        event = self.normalized_events[0]
        result, metadata = self.plugin.onMessage(event, metadata)
        logger.info(result)
        assert result["details"]["sourceipaddress"] == "54.21.12.27"

        event = self.normalized_events[1]
        result, metadata = self.plugin.onMessage(event, metadata)
        logger.info(result)
        assert result["details"]["sourceipaddress"] == "139.59.66.23"

        event = self.normalized_events[2]
        result, metadata = self.plugin.onMessage(event, metadata)
        logger.info(result)
        assert result["details"]["sourceipaddress"] == "198.51.100.1"
        assert result["details"]["destinationipaddress"] == "192.0.2.1"
