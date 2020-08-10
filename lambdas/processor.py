from __future__ import print_function

import base64
import json
from json import JSONDecodeError
from io import StringIO
from utils.dotdict import DotDict
from utils.plugins import send_event_to_plugins, register_plugins
from utils.helpers import is_cloudtrail, generate_metadata, emit_json_block, chunks
from utils.dict_helpers import merge
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    output = []
    metadata = generate_metadata(context)
    logger.debug(f"metadata is: {metadata}")
    normalization_plugins = register_plugins("normalization_plugins")
    enrichment_plugins = register_plugins("enrichment_plugins")

    if "records" in event:
        for record in event["records"]:
            output_record = {}
            logger.debug(f"found record in event: {record}")
            payload = base64.b64decode(record["data"])

            payload_dict = None
            try:
                # load the json we have from either a .json file or a gunziped file
                payload_dict = json.loads(payload)
            except JSONDecodeError as e:
                # file isn't well formed json, see if we can interpret json from it
                logger.error(f"payload is not valid json decode error {e}")

            if payload_dict:
                # normalize it
                result_record, metadata = send_event_to_plugins(
                    payload_dict, metadata, normalization_plugins
                )
                # enrich it
                result_record, metadata = send_event_to_plugins(
                    result_record, metadata, enrichment_plugins
                )
                if result_record:
                    # TODO, what to do with lambda info as metadata? Do we care?
                    # result_record = merge(result_record, metadata)
                    logger.debug(f" resulting norm/enriched is: {result_record}")
                    # json ending in new line so athena recognizes the records
                    output_record = {
                        "recordId": record["recordId"],
                        "result": "Ok",
                        "data": base64.b64encode(
                            json.dumps(result_record).encode("utf-8") + b"\n"
                        ).decode("utf-8"),
                    }
                else:
                    # result as None, means drop the record
                    # TODO, what is the right result in firehose terms
                    logger.error(f"record {record['recordId']} failed processing")
                    output_record = {
                        "recordId": record["recordId"],
                        "result": "ProcessingFailed",
                        "data": record["data"],
                    }
            else:
                logger.error(
                    f"record {record['recordId']} failed processing, no resulting dict"
                )
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

