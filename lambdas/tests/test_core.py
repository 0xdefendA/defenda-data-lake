import unittest
from io import BytesIO
from subprocess import PIPE, Popen
from pkg_resources import parse_version
import pytest
import yaml
from datetime import timezone
import datetime
from utils.plugins import send_event_to_plugins, register_plugins
from utils.helpers import is_cloudtrail, generate_metadata, short_uuid
from utils.helpers import is_ip, isIPv4, isIPv6
from utils.dict_helpers import (
    merge,
    find_keys,
    enum_values,
    enum_keys,
    sub_dict,
    dict_match,
    getValueByPath,
    dictpath,
)
from utils.dotdict import DotDict
from utils.dates import toUTC, get_date_parts
from pathlib import Path
import logging, logging.config

print("setting up logging")
logging_config_file_path = Path(__file__).parent.joinpath("logging_config.yml")
with open(logging_config_file_path, "r") as fd:
    logging_config = yaml.safe_load(fd)
    logging.config.dictConfig(logging_config)
global logger
logger = logging.getLogger()
logger.info("logging established")


class TestCore(object):
    def test_cloudtrail_file_identification(self):
        filename = "AWSLogs/722455710680/CloudTrail/us-west-2/2019/09/20/722455710680_CloudTrail_us-west-2_20190920T0000Z_2AKE4AyQfcPRcIoa.json.gz"
        assert is_cloudtrail(filename) == True
        filename = "not cloudtrailfile.json.gz"
        assert is_cloudtrail(filename) == False

    def test_lambda_metadata_generation(self):
        lambda_context = {
            "function_version": "$LATEST",
            "invoked_function_arn": "arn:aws:lambda:us-west-2:722455710680:function:processor-prod",
            "function_name": "processor-prod",
            "memory_limit_in_mb": "1024",
        }
        lambda_context = DotDict(lambda_context)
        result = generate_metadata(lambda_context)
        assert type(result.lambda_details) == type(lambda_context)
        assert "function_version" in result.lambda_details
        assert "function_arn" in result.lambda_details
        assert "function_name" in result.lambda_details
        assert "memory_size" in result.lambda_details

    def test_short_uuid(self):
        assert len(short_uuid()) == 8

    def test_to_utc(self):
        assert toUTC("Jan 1 12am 2020 UTC") == datetime.datetime(
            2020, 1, 1, 0, 0, tzinfo=timezone.utc
        )
        assert toUTC("Jan 1 12am 2020 UTC").isoformat() == "2020-01-01T00:00:00+00:00"

    def test_get_date_parts(self):
        parts = get_date_parts()
        assert len(parts) == 8

    def test_dictpath(self):
        assert list(dictpath("key.value")) == ["key", "value"]

    def test_get_value_by_path(self):
        assert getValueByPath({"key": "value"}, "key") == "value"
        assert getValueByPath({"key": {"key": "value"}}, "key.key") == "value"
        assert (
            getValueByPath({"key": {"key": {"key": "value"}}}, "key.key.key") == "value"
        )

    def test_ip_helpers(self):
        assert is_ip("127.0.0.1")
        assert is_ip("127.0.0.1/32")
        assert is_ip("127") == False
        assert is_ip("1") == False
        assert is_ip("1278.1.1.1.1") == False
        assert is_ip("fe80::")
        assert is_ip("fe80::/10")
        assert isIPv4("127.0.0.1")
        assert isIPv4("127.0.0.1/32") == False
        assert isIPv6("fe80::")
        assert isIPv6("::ffff:192.0.2.15")
        assert isIPv6(":ffff:192.0.2.15") == False

    def test_merge(self):
        dict1 = {"some_key": "some value"}
        dict2 = {"some_other_key": "some other value"}
        dict3 = merge(dict1, dict2)
        assert dict3 == {"some_key": "some value", "some_other_key": "some other value"}

    def test_find_keys(self):
        complex_dict1 = {
            "some_key": "some value",
            "sub_key": {"some_key": "some other value"},
        }
        result = list(find_keys(complex_dict1, "some_key"))
        assert result == ["some value", "some other value"]

    def test_enum_values(self):
        complex_dict1 = {
            "some_key": "some value",
            "sub_key": {"some_key": "some other value"},
        }
        result = list(enum_values(complex_dict1))
        assert result == ["some value", "some other value"]

    def test_enum_keys(self):
        complex_dict1 = {
            "some_key": "some value",
            "sub_key": {"some_key": "some other value"},
        }
        result = list(enum_keys(complex_dict1))
        assert result == ["some_key", "sub_key", "some_key"]

    def test_sub_dict(self):
        complex_dict1 = {
            "some_key": "some value",
            "sub_key": {"some_key": "some other value"},
        }
        result = sub_dict(complex_dict1, ["some_key"], "nothing")
        assert result == {"some_key": "some value"}
        result = sub_dict(complex_dict1, ["sub_key.some_key"], "nothing")
        assert result == {"sub_key.some_key": "nothing"}
        complex_dot_dict = DotDict(complex_dict1)
        result = sub_dict(complex_dot_dict, ["sub_key.some_key"], "nothing")
        assert result == {"sub_key.some_key": "some other value"}
        result = sub_dict(complex_dot_dict, ["some_key", "sub_key.some_key"])
        assert result == {
            "some_key": "some value",
            "sub_key.some_key": "some other value",
        }

    def test_dict_match(self):
        complex_dict1 = {
            "some_key": "some value",
            "sub_key": {"some_key": "some other value"},
        }
        assert dict_match({"some_key": "some value"}, complex_dict1)
        complex_dot_dict = DotDict(complex_dict1)
        assert dict_match({"sub_key.some_key": "some other value"}, complex_dot_dict)
        assert (
            dict_match({"sub_key.some_key": "not some other value"}, complex_dot_dict)
            == False
        )
