from __future__ import print_function

import base64
import json
from json import JSONDecodeError
from io import StringIO
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def emit_json_block(stream):
    """ take a stream of io.StringIO(blob)
        iterate it and emit json blocks as they are found
    """
    open_brackets = 0
    block = ""
    while True:
        c = stream.read(1)
        if not c:
            break

        if c == "{":
            open_brackets += 1
        elif c == "}":
            open_brackets -= 1
        block += c

        if open_brackets == 0:
            yield block.strip()
            block = ""


def lambda_handler(event, context):
    output = []

    if "records" in event:
        for record in event["records"]:
            output_record = {}
            logger.info(record)
            payload = base64.b64decode(record["data"])

            payload_dict = None
            try:
                # load the json we have from either a .json file or a gunziped file
                payload_dict = json.loads(payload)
            except JSONDecodeError:
                # file isn't well formed json, see if we can interpret json from it
                logger.error("json decode error, attempting to parse json")
                for block in emit_json_block(StringIO(payload)):
                    if block:
                        payload_dict = json.loads(block)

            if payload_dict:
                payload_dict["yup"] = "seen"
                logger.info(payload_dict)
                output_record = {
                    "recordId": record["recordId"],
                    "result": "Ok",
                    "data": base64.b64encode(
                        json.dumps(payload_dict).encode("utf-8")
                    ).decode("utf-8"),
                }
            else:
                logger.error(f"record {record['recordId']} failed processing")
                output_record = {
                    "recordId": record["recordId"],
                    "result": "ProcessingFailed",
                    "data": record["data"],
                }

            output.append(output_record)

        logger.info("Processed {} records.".format(len(event["records"])))

        return {"records": output}
    else:
        logger.info(f"no records found in {event} with context: {context}")

