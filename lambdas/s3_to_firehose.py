import boto3
import gzip
import json
import logging
import os
from io import BytesIO, TextIOWrapper, StringIO
from utils.dotdict import DotDict
from utils.helpers import is_cloudtrail, generate_metadata, emit_json_block, chunks
from json import JSONDecodeError

logger = logging.getLogger()
logger.setLevel(logging.INFO)
FIREHOSE_DELIVERY_STREAM = os.environ.get(
    "FIREHOSE_DELIVERY_STREAM", "data_lake_s3_stream"
)
FIREHOSE_BATCH_SIZE = os.environ.get("FIREHOSE_BATCH_SIZE", 100)


def send_to_firehose(records):
    f_hose = boto3.client("firehose")

    # records should be a list of dicts
    response = None
    if type(records) is list:
        # batch up the list below the limits of firehose
        for batch in chunks(records, FIREHOSE_BATCH_SIZE):
            response = f_hose.put_record_batch(
                DeliveryStreamName=FIREHOSE_DELIVERY_STREAM,
                Records=[
                    {"Data": bytes(str(json.dumps(record) + "\n").encode("UTF-8"))}
                    for record in batch
                ],
            )
            logger.debug("firehose response is: {}".format(response))


def lambda_handler(event, context):
    """
        Called on a PUT to s3
        Make every attempt to read in json records
        from the s3 source
    """
    metadata = generate_metadata(context)
    logger.debug("Event is: {}".format(event))

    # make the event easier to traverse
    event = DotDict(event)

    # test harnesses
    if event == {"test": "true"}:
        return {"Hello": "from s3_to_firehose"}
    elif event == {"metadata": "name"}:
        return metadata
    elif "Records" in event:
        # should be triggered by s3 Put/Object created events
        s3 = boto3.client("s3")
        for record in event.Records:
            record = DotDict(record)
            s3_bucket = record.s3.bucket.name
            s3_key = record.s3.object.key
            # a new bucket will fire for folders *and* files, early exit if it's a folder
            if s3_key.endswith("/"):
                return event
            # assume the file is just good ol json
            source = "s3json"
            # if the file name is cloudtrail-ish
            if is_cloudtrail(s3_key):
                source = "cloudtrail"
            try:
                s3_response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
            except Exception as e:
                logger.error(f"{e} while attempting to get_object {s3_bucket} {s3_key}")
                continue
            s3_data = ""
            # gunzip if zipped
            if s3_key[-3:] == ".gz":
                s3_raw_data = s3_response["Body"].read()
                with gzip.GzipFile(fileobj=BytesIO(s3_raw_data)) as gzip_stream:
                    s3_data += "".join(TextIOWrapper(gzip_stream, encoding="utf-8"))
            else:
                s3_data = s3_response["Body"].read().decode("utf-8")

            # create our list of records to append out findings to
            s3_records = []
            s3_dict = None
            try:
                # load the json we have from either a .json file or a gunziped file
                s3_dict = json.loads(s3_data)
            except JSONDecodeError:
                # file isn't well formed json, see if we can interpret json from it
                for block in emit_json_block(StringIO(s3_data)):
                    if block:
                        record = json.loads(block)
                        record["source"] = source
                        s3_records.append(record)
            # if this is a dict of a single 'Records' list, unroll the list into
            # it's sub records
            if s3_dict and "Records" in s3_dict:
                if type(s3_dict["Records"]) is list:
                    for record in s3_dict["Records"]:
                        record["source"] = source
                        s3_records.append(record)
            # maybe it's just a list already?
            elif s3_dict and type(s3_dict) is list:
                # a list of dicts
                for record in s3_dict:
                    record["source"] = source
                    s3_records.append(record)
            elif s3_dict and type(s3_dict) is dict:
                # a single dict, but lets add it to a list
                # for consistent handling
                s3_dict["source"] = source
                s3_records.append(s3_dict)

            logger.debug("pre-plugins s3_records is: {}".format(s3_records))
            # send off to firehose for further processing
            if s3_records:
                send_to_firehose(s3_records)

        return
