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


class TestPluginTimestamps(object):
    def setup(self):
        from normalization_plugins.timestamps import message

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
        # remove the timstamp in this event
        # that would trigger the plugin
        # to see if it passes the no change test
        del event["details"]["timestamp"]
        result, metadata = self.plugin.onMessage(event, metadata)
        # the plugin adds a metadata field
        # remove it for the assertion test
        # in = out - plugin didn't modify it
        del result["details"]["_utcprocessedtimestamp"]

        assert result == event