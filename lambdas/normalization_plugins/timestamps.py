from utils.dict_helpers import enum_keys, getValueByPath, find_keys
from utils.dotdict import DotDict
from utils.dates import toUTC, utcnow
from datetime import datetime
import logging

logger = logging.getLogger()

# likely timestamp fields
likely_timestamp_fields = [
    "timestamp",
    "@timestamp",
    "time",
    "eventtime",
    "start",
]


class message(object):
    def __init__(self):
        """
        takes an incoming message
        discovers timestamps
        normalizes the format and updates utctimestamp
        appends _utcprocessedtimestamp
        """

        # register for all events
        # so we can add the processed timestamp metadata field
        self.registration = ["*"]
        self.priority = 20

    def onMessage(self, message, metadata):
        # help ourselves to a dot dict and list of keys
        message = DotDict(message)
        message_keys = list(enum_keys(message))

        try:
            for field in likely_timestamp_fields:
                if field in message_keys:
                    timestamps = list(find_keys(message, field))
                    if field == "time" and "date" in message_keys:
                        # combine date and time for a timestamp
                        dates = list(find_keys(message, "date"))
                        if dates:
                            # setup a new list for the zipped results
                            date_timestamps = []
                            for i in zip(dates, timestamps):
                                date_timestamps.append(f"{i[0]} {i[1]}")

                            if date_timestamps:
                                # replace the original list
                                # with this list of date + time
                                timestamps = date_timestamps

                    for timestamp in timestamps:
                        utctimestamp = ""
                        try:
                            utctimestamp = toUTC(timestamp)
                        except Exception as e:
                            logger.error(
                                f"exception {e} while converting {timestamp} to utc"
                            )
                            pass
                        if isinstance(utctimestamp, datetime):
                            message["utctimestamp"] = utctimestamp.isoformat()
                            # first match wins
                            raise StopIteration

        except StopIteration:
            pass

        # append processed timestamp as metadata
        message["details"]["_utcprocessedtimestamp"] = utcnow().isoformat()

        return (message, metadata)