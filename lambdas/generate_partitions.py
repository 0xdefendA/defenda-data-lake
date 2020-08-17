import os
import boto3
import time
import logging, logging.config
from utils.dotdict import DotDict
from utils.dates import get_date_parts
import pyathena
from pyathena import connect

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
    location 's3://{config.account}-defenda-data-lake-output-bucket/{year}/{month}/{day}/{hour}'
    """
    return query


def lambda_handler(event, context):
    config = DotDict({})
    config.account = boto3.client("sts").get_caller_identity().get("Account")
    config.athena_workgroup = os.environ.get("ATHENA_WORKGROUP", "defenda_data_lake")
    config.athena_database = os.environ.get("ATHENA_DATABASE", "defenda_data_lake")
    config.athena_table = os.environ.get("ATHENA_TABLE", "events")

    # query status/wait for response

    athena_query = get_athena_query(config)
    logger.debug(athena_query)
    cursor = connect(work_group=config.athena_workgroup).cursor()
    cursor.execute(athena_query)
    logger.debug("Query finished: {}".format(cursor.state))
    return
