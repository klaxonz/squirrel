from decimal import Decimal
import datetime

try:
    import uuid
    _use_uuid = True
except ImportError:
    _use_uuid = False

datetime_format = "%Y/%m/%d %H:%M:%S"
date_format = "%Y/%m/%d"
time_format = "%H:%M:%S"


def set_datetime_format(fmt_string):
    datetime_format = fmt_string


def set_date_format(fmt_string):
    date_format = fmt_string


def set_time_format(fmt_string):
    time_format = fmt_string


def more(obj):
    if isinstance(obj, Decimal):
        return str(obj)

    if isinstance(obj, datetime.datetime):
        return obj.strftime(datetime_format)

    if isinstance(obj, datetime.date):
        return obj.strftime(date_format)

    if isinstance(obj, datetime.time):
        return obj.strftime(time_format)

    if _use_uuid and isinstance(obj, uuid.UUID):
        return str(obj.db_value())

    raise TypeError("%r is not JSON serializable" % obj)