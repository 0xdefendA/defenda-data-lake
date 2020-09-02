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
        likely_source_fields = [
            "src",
            "srcaddr",
            "srcip",
            "src_ip",
            "source_ip",
            "sourceipaddress",
            "source_ip_address",
            "c-ip",
            "remoteip",
            "remote_ip",
            "remoteaddr",
            "remote_host_ip_address",
            "ipaddress",
            "ip_address",
            "ipaddr",
            "id_orig_h",
        ]

        likely_destination_fields = [
            "dst",
            "dstip",
            "dst_ip",
            "dstaddr",
            "dest",
            "destaddr",
            "dest_ip",
            "destination_ip",
            "destinationipaddress",
            "destination_ip_address",
            "id_resp_h",
        ]
        # lets find a source
        # first match wins
        try:
            for field in likely_source_fields:
                if field in message_keys:
                    # do we already have one?
                    if not getValueByPath(message, "details.sourceipaddress"):
                        # search the message for any instance of this field
                        # a list since it could appear multiple times
                        source_ips = list(find_keys(message, field))
                        for ip in source_ips:
                            if is_ip(ip):
                                message.details.sourceipaddress = ip
                                # first one wins
                                # raise an error to break both for loops
                                raise StopIteration
        except StopIteration:
            pass

        # lets find a destination
        # first match wins
        try:
            for field in likely_destination_fields:
                if field in message_keys:
                    # do we already have one?
                    if not getValueByPath(message, "details.destinationipaddress"):
                        # search the message for any instance of this field
                        # a list since it could appear multiple times
                        destination_ips = list(find_keys(message, field))
                        for ip in destination_ips:
                            if is_ip(ip):
                                message.details.destinationipaddress = destination_ips[
                                    0
                                ]
                                # first one wins
                                # raise an error to break both for loops
                                raise StopIteration
        except StopIteration:
            pass

        return (message, metadata)