import os
import boto3
import time
import logging, logging.config
from utils.dotdict import DotDict
from utils.dates import get_date_parts
from utils.dates import toUTC
from utils.athena import run_query, default_bucket

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_athena_query(config):
    (
        hour,
        month,
        day,
        year,
        last_hour_hour,
        last_hour_month,
        last_hour_day,
        last_hour_year,
    ) = get_date_parts()
    query = f"""
    ALTER TABLE {config.athena_database}.{config.athena_table}
    ADD IF NOT EXISTS PARTITION
    (year='{year}',
    month='{month}',
    day='{day}',
    hour='{hour}'
    )
    location 's3://uoc-{config.account}-output-bucket/{year}/{month}/{day}/{hour}'
    """
    return query


def handler(event, context):
    session = boto3.session.Session()
    athena = session.client("athena")
    config = DotDict({})
    config.account = boto3.client("sts").get_caller_identity().get("Account")
    config.athena_database = os.environ.get("ATHENA_DATABASE", "events")
    config.athena_table = os.environ.get("ATHENA_TABLE", "events")

    # query status/wait for response
    query_status = None
    athena_query = get_athena_query(config)
    logger.debug(athena_query)
    athena_response = run_query(
        athena, athena_query, config.athena_database, default_bucket(session)
    )
    while query_status == "QUEUED" or query_status == "RUNNING" or query_status is None:
        query_status = athena.get_query_execution(
            QueryExecutionId=athena_response["QueryExecutionId"]
        )["QueryExecution"]["Status"]["State"]
        logger.debug(query_status)
        if query_status == "FAILED" or query_status == "CANCELLED":
            raise Exception(
                'Athena query with the string "{}" failed or was cancelled'.format(
                    athena_query
                )
            )
        if query_status != "SUCCEEDED":
            time.sleep(0.5)
    logger.debug("Query finished: {}".format(query_status))
    return
