import math
import tzlocal
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
import logging

logger = logging.getLogger()

UTC = timezone.utc


def get_date_parts():
    now = datetime.now(UTC)
    last_hour_now = now - timedelta(hours=1)

    now_hour = str(now.hour).rjust(2, "0")
    now_month = str(now.month).rjust(2, "0")
    now_day = str(now.day).rjust(2, "0")
    now_year = str(now.year)
    last_hour_hour = str(last_hour_now.hour).rjust(2, "0")
    last_hour_month = str(last_hour_now.month).rjust(2, "0")
    last_hour_day = str(last_hour_now.day).rjust(2, "0")
    last_hour_year = str(last_hour_now.year)

    return (
        now_hour,
        now_month,
        now_day,
        now_year,
        last_hour_hour,
        last_hour_month,
        last_hour_day,
        last_hour_year,
    )


def toUTC(suspectedDate):
    """make a UTC date out of almost anything"""
    objDate = None
    LOCAL_TIMEZONE = tzlocal.get_localzone()

    if type(suspectedDate) == datetime:
        objDate = suspectedDate
    elif type(suspectedDate) == float:
        if suspectedDate <= 0:
            objDate = datetime(1970, 1, 1)
        else:
            # This breaks in the year 2286
            EPOCH_MAGNITUDE = 9
            magnitude = int(math.log10(int(suspectedDate)))
            if magnitude > EPOCH_MAGNITUDE:
                suspectedDate = suspectedDate / 10 ** (magnitude - EPOCH_MAGNITUDE)
            objDate = datetime.fromtimestamp(suspectedDate, LOCAL_TIMEZONE)
    elif str(suspectedDate).isdigit():
        if int(str(suspectedDate)) <= 0:
            objDate = datetime(1970, 1, 1)
        else:
            # epoch? but seconds/milliseconds/nanoseconds (lookin at you heka)
            epochDivisor = int(str(1) + "0" * (len(str(suspectedDate)) % 10))
            objDate = datetime.fromtimestamp(
                float(suspectedDate / epochDivisor), LOCAL_TIMEZONE
            )
    elif type(suspectedDate) is str:
        # try to parse float or negative number from string:
        objDate = None
        try:
            suspected_float = float(suspectedDate)
            if suspected_float <= 0:
                objDate = datetime(1970, 1, 1)
        except ValueError:
            pass
        if objDate is None:
            objDate = parse(suspectedDate, fuzzy=True)
    try:
        if objDate.tzinfo is None:
            # Attach local timezone to naive datetimes
            objDate = objDate.replace(tzinfo=LOCAL_TIMEZONE)
    except AttributeError as e:
        raise ValueError(
            "Date %s which was converted to %s has no "
            "tzinfo attribute : %s" % (suspectedDate, objDate, e)
        )

    # Convert to UTC
    objDate = objDate.astimezone(UTC)

    return objDate


def utcnow():
    """Return a timezone-aware UTC datetime"""
    return datetime.now(UTC)
