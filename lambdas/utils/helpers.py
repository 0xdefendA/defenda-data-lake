import uuid
import re
import collections
import logging
import netaddr
from utils.dotdict import DotDict

logger = logging.getLogger()

CLOUDTRAIL_FILE_NAME_REGEX = re.compile(
    r"\d+_cloudtrail_.+.json.gz$", re.I
)

def emit_json_block(stream):
    ''' take a stream of io.StringIO(blob)
        iterate it and emit json blocks as they are found
    '''
    open_brackets = 0
    block = ''
    while True:
        c = stream.read(1)
        if not c:
            break

        if c == '{':
            open_brackets += 1
        elif c == '}':
            open_brackets -= 1
        block += c

        if open_brackets == 0:
            yield block.strip()
            block = ''

def short_uuid():
    return str(uuid.uuid4())[0:8]

def is_cloudtrail(filename):
    match = CLOUDTRAIL_FILE_NAME_REGEX.search(filename)
    return bool(match)

def is_ip(ip):
    '''
        validate an ipv4/ipv6 or cidr mask
        valid_ipv4/6 won't recognize a cidr mask
    '''
    try:
        # by default netaddr will validate single digits like '0' as 0.0.0.0/32
        # lets be a bit more precise and support cidr masks
        # by checking for format chars (. or :)
        # and using the IPNetwork constructor
        if ('.' in ip) or (':' in ip):
            netaddr.IPNetwork(ip)
            return True
        else:
            return False
    except Exception:
        return False

def isIPv4(ip):
    try:
        return netaddr.valid_ipv4(ip,flags=1)
    except:
        return False

def isIPv6(ip):
    try:
        return netaddr.valid_ipv6(ip,flags=1)
    except:
        return False

def generate_metadata(context):
    metadata = {
        "lambda_details": {
            "function_version": context.function_version,
            "function_arn": context.invoked_function_arn,
            "function_name": context.function_name.lower(),
            "memory_size": context.memory_limit_in_mb,
        },
    }

    return DotDict(metadata)

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def first_matching_index_value(iterable, condition = lambda x: True):
    """
    Returns the first index,value tuple in the list that
    satisfies the `condition`.

    If the condition is not given, returns the first of the iterable.
    condition is passed as:
    condition = lambda i: <test>
    >>> first_matching_item( (1,2,3), condition=lambda x: x % 2 == 0)
    (1, 2)
    """
    try:
        return next((index,value) for index,value in enumerate(iterable) if condition(value))

    except StopIteration:
        return (None,None)