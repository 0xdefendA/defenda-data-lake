from utils.dict_helpers import enum_keys, getValueByPath, find_keys
from utils.dotdict import DotDict
from utils.helpers import is_ip


class message(object):
    def __init__(self):
        """
        takes an incoming message
        discovers ip addresses and
        normalizes the field names (source/destination)
        """

        self.registration = ["*"]
        self.priority = 20

    def onMessage(self, message, metadata):
        # help ourselves to a dot dict and list of keys
        message = DotDict(message)
        message_keys = list(enum_keys(message))

        # search for source ip address
        # likely places for a source IP
        likely_fields = [
            "src",
            "srcip",
            "src_ip",
            "source_ip",
            "sourceipaddress",
            "source_ip_address",
            "c-ip",
        ]
        for field in likely_fields:
            if field in message_keys:
                # do we already have one?
                if not getValueByPath(message, "details.sourceipaddress"):
                    source_ips = list(find_keys(message, field))
                    if source_ips and is_ip(source_ips[0]):
                        message.details.sourceipaddress = source_ips[0]

        return (message, metadata)