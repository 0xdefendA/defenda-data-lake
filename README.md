# defendA Data Lake
An AWS-native, serverless log management system to allow you to ingest unstructured JSON, normalize & enrich it and store it in Athena for queries and analysis.

**Build Status:**
- Master [![Build Status](https://travis-ci.com/0xdefenda/defenda-data-lake.svg?branch=master) ](https://travis-ci.com/0xdefenda/defenda-data-lake)

## Video intro
Here's a brief video intro to the data lake.

[![video intro](http://img.youtube.com/vi/eYQ0gjTMVhc/0.jpg)](http://www.youtube.com/watch?v=eYQ0gjTMVhc "defendA security data lake")

## Why?
Centralized log/event management is a core element of an infosec program, yet most solutions are not cloud native, require unnecessary servers/clusters and force you to massage your events into a strict format.

The reality is that infosec teams aren't able to dictate what format events come in which is usually arbitrary, nested JSON.

This solution uses only serverless constructs to allow you to store unstructured JSON from any source in a predictable data structure that can be accessed using Athena's native SQL.

## Deployment:

Deployment is via python/pipenv, terraform and a mini-docker environment to compile the lambdas.

It uses us-west-2 as the default region, set a terraform.tfvars variable ( aws_region = "some-other-region ) if you'd like it elsewhere.


First get the code and initiate pipenv (or [install it if you aren't converted yet](https://pipenv.pypa.io/en/latest/install/)):

```bash
git clone <this repo> .
pipenv --python 3.8
```

Now build the lambdas:

```bash
./generate_lambda_zip.py
```

Init and run terraform
```bash
terraform init
terraform plan
terraform apply
```
and you will end up with:

- An Athena database: `defenda_datalake`
- A table: `events`
- An s3 bucket to serve as the data store for the athena data lake: `data-lake-<accountnumber>-output-bucket`
- An s3 bucket to act as an input if you have things that can't talk directly to firehose: `data-lake-<accountnumber>-input-bucket`
- A firehose delivery stream: `data_lake_s3_stream`
- A lambda to operate on records bound for athena: `data_lake_lambda`
- A lambda to generate partitions: `data_lake_generate_partitions`
- All the iam permissions and glue to sync these together

## Event structure
Athena does require *some* structure to allow for querying. To enable that and still allow unstructured JSON we use the following `event shell`

- eventid (string)
    - a unique guid
- utctimestamp (string)
    - timestamp for the event in UTC, ISO format
- severity (string)
    - DEBUG, INFO, WARNING, etc
- summary (string)
    - a human readable text description of the event
- category (string)
    - what sort of event: authentication, etc.
- source (string)
    - where the event came from (gsuite, sophos, cloudtrail, okta, etc)
- tags (array<string>)
    - a series of tags you'd like to add
- plugins (array<string>)
    - a record of what plugins operated on this event
- details (string)
    - this `string` is the native JSON of the event. Stored as a string to allow for json_extract_scalar operations to query the JSON structure.
- year (string) (Partitioned)
    - partition for athena
- month (string) (Partitioned)
    - partition for athena
- day (string) (Partitioned)
    - partition for athena
- hour (string) (Partitioned)
    - partition for athena

### Sample query
So what does it look like to use this data lake? Here's a sample query that would return all AWS console logins in a certain partition/timeframe:

```sql
SELECT utctimestamp,
         summary,
         source,
         details

FROM "defenda_data_lake"."events"
    where
    source='cloudtrail' AND json_extract_scalar(details,'$.eventname') = 'ConsoleLogin'
    AND (
            (year='2020'
            AND month='06'
            AND day='19'
            AND hour='01')
            OR
            (year='2020'
            AND month='06'
            AND day='19'
            AND hour='00')
    )
    limit 100
```

You can use the [json_extract_scalar](https://prestodb.io/docs/current/functions/json.html) function and [json path expressions](https://goessner.net/articles/JsonPath/index.html#e2) to get at any layer of the nested JSON stored in the 'details' field as part of your query.

The date portion of the where clause allows us to hone in on a particular time period and allows us to limit the cost of the query by limiting the amount of data scanned by Athena.

Queries can be any valid [Presto SQL](https://prestodb.io/docs/current/sql/select.html) including [functions](https://prestodb.io/docs/current/functions.html)


Here's another, slightly more complex query taking advantage of the work the ip_addresses.py plugin does to gather all the ips it's seen into a list. We can use that to query for any events involving a suspect ip like so:

```sql
SELECT
    utctimestamp,
    summary,
    source,
    details,
    tags
FROM defenda_data_lake.events
    where
        source ='cloudtrail'
    AND json_array_contains(json_extract(details,'$._ipaddresses'),'7.1.14.12')
    AND year='2020'
    AND month='09'
    AND day='07'
    AND hour='18'
    LIMIT 100;
```

The plugin searches events for likely IP fields, verifies them, normalizes source/destination IPs and then appends them to a metadata list details._ipaddresses. We can query that json natively by extracting it from the details athena field and use the Presto function json_array_contains to narrow our query to the IP address in question.

### Python querying
Thanks to the [pyathena library](https://pypi.org/project/PyAthena/) and [pandas](https://pandas.pydata.org/), querying and exploring data is easy!

Here's the same sample query looking for IP address events, but performed from a python environment.

```python
from pyathena import connect
from pyathena.util import as_pandas
from pyathena.pandas_cursor import PandasCursor
import pandas as pd

cursor = connect(work_group='defenda_data_lake',region_name='us-west-2',cursor_class=PandasCursor).cursor()

cursor.execute("""
SELECT
    utctimestamp,
    summary,
    source,
    details,
    tags
FROM defenda_data_lake.events
    where
        source ='cloudtrail'
    AND json_array_contains(json_extract(details,'$._ipaddresses'),'7.1.14.12')
    AND year='2020'
    AND month='09'
    AND day='07'
    AND hour='18'
    LIMIT 100;
               """)
df = as_pandas(cursor)
df.head()

```

You simply create a cursor to handle your results, send it a query and your result is a pandas data frame.

If you'd like your query results restored to a list of python dictionaries you can convert the JSON in the details field like so:

```python
query_results=[]
for message in df.to_dict('records'):
    message['details']=json.loads(message['details'])
    query_results.append(message)
```

### Advantages

#### Serverless!
No servers to manage and this scales up as your event ingestion scales. You can store as much data as s3/athena can handle and due to the JSON handling, changes in data structures won't blow up your infrastructure.

#### Security
Operating via serverless, there is nothing to maintain, patch, etc. Python libraries will of course update over time.

There is nothing exposed to the outside world, no extra costs for authentication, no extra licensing for secure transport, etc.

#### Customizable
A simple plugin system allows you to write your own custom event handlers to either normalize your data or enhance it as you see fit. Plugins are in python, usually a dozen lines of code and an be fine tuned to operate only on the events of interest.

#### Integration
For input that can't be hooked up to firehose, you can deposit raw JSON in the s3 input bucket and it will be send automatically through to firehose/athena. You can use this to hook up legacy event producers that may not be able to speak native firehose but can write files to s3.

#### Cost
This costs nothing to deploy. Costs will vary depending on your data ingestion, but can get started today without having to guesstimate event per second, data size, throughput, or other statistics you usually have to commit to in other log management platforms.

Preliminary tests sending 500MB of data to the data lake resulted in the following costs:

Test using s3 as the input (copying json files to s3):
 - s3: $0.51
 - firehose: $0.02
 - athena: $0.00

Test using firehose only as the input (no files, direct to firehose):
 - s3: $0.02
 - firehose: $0.02
 - athena: $0.00


### Disadvantages

#### Latency
Depending on your rate of event ingestion, firehose will queue events for 60 seconds before flushing to s3. If you have enough flow, this usually isn't a problem but if your event flow is very low you may see a slight delay.

#### Query Cost potential

Athena's pricing is based on $/query/data that as of this writing is $5 per terabyte. Each query is charged based on the amount of underlying data that was scanned to resolve the query and prorated accordingly. So if your query operated on a megabyte of data in a partition, your charge would be only for that megabyte.

However it is a `per query` charge. So if you aren't careful with your queries and don't make use of partitions you can run up a bill.

To help, data is automatically partitioned in hour chunks (year/month/day/hour structure in the s3 bucket). By simply adding some criteria to your where clause you can limit the amount of data you interact with and are charged for. Data is also automatically gzipped to also reduce the charges.


## Companion Projects

Anything that sends json to firehost can be used as an input into the data lake. Here are some sample companion projects that do just that to send security events from some common data sources:

- [gsuite log ingestion](https://github.com/jeffbryner/gsuite-activity-lambda)
- [sophos log ingestion](https://github.com/jeffbryner/sophos-activity-lambda)
- [meraki log ingestion](https://github.com/jeffbryner/meraki-activity-lambda)
- [beats log ingestion](https://github.com/jeffbryner/firehose-es-input#browserbeat-example)

## Plugins
Inspired by [MozDef's plugin system](https://github.com/mozilla/MozDef/tree/master/mq/plugins) via [pynsive](https://github.com/zinic/pynsive/), the plugins in the data lake use a similar concept of operations, but are ordered a bit differently.

### Plugin types
Plugins can either normalize or enrich an event. Events are first run through normalization plugins, then through enrichment plugins. This makes it easier to target your plugin to the task at hand, and makes it easier to perform whatever operation you are envisoning.

Plugins are python, and register themselves to receive events containing a field, a category or a tag. Plugins can signal they'd like to see all events by registering for '*'.

If an event matches the registration, the event and it's metadata are sent to the plugin where the plugin can rearrange/rename fields (normalization), add information to the event (enrichment) or perform any operation you might envision with the event.

A plugin can signal to drop the event by returning None for the message. The pipeline will not store the event, which can help weed out noise.

### Sample plugin
Lets look at the sample Gsuite login plugin configured to operate on events from the [gsuite log ingestion](https://github.com/jeffbryner/gsuite-activity-lambda) project that polls Google for gsuite security events and sends them to firehose.

```python
class message(object):

    def __init__(self):
        '''
        handle gsuite login activity record
        '''

        self.registration = ['kind']
        self.priority = 20
```

The plugin registers to receive any even that has a field named 'kind'. The registration property is a list and can contain a list of fields that, if present, the plugin would like to receive. You could have a registration of ```['ipaddress','ip_address','srcip']``` for example to receive any event that contains any or all of those fields.

Next, the plugin puts itself as priority 20, meaning any plugin with a lower number will receive the event first. This allows you to order your plugins in case that is important in the plugin pipeline logic. Plugins will be called in order of priority, 0 going first, higher numbers going later.

Next the plugin contains the logic to use when encountering a matching event:

```python
    def onMessage(self, message, metadata):
        # for convenience, make a dot dict version of the message
        dot_message=DotDict(message)

        # double check that this is our target message
        if 'admin#reports#activity' not in dot_message.get('details.kind','')\
            or 'id' not in message.get('details','') \
            or 'etag' not in message.get('details',''):
            return(message, metadata)
# <trimmed for brevity>
```

Your plugins can make use of the utils functions like DotDict, etc to operate on an event. It's best practice to first ensure this event fully matches what you expect and this plugin is double checking for certain fields in the structure and returning the message unchanged if there isn't a match.

Normalization plugins usually cherry pick fields from the original event and surface them to standardized fields to make querying/correlating easier. For example this plugin sets some tags and brings out the IP address and timestamp:

```python
        message["source"]="gsuite"
        message["tags"].append("gsuite")

        # clean up ipaddress field
        if 'ipaddress' in message['details']:
            message['details']['sourceipaddress']=message['details']['ipaddress']
            del message['details']['ipaddress']

        # set the actual time
        if dot_message.get("details.id.time",None):
            message['utctimestamp']=toUTC(message['details']['id']['time']).isoformat()

```

it goes on to do the same for other common fields and most importantly sets a human readable summary:

```python
        # set summary
        message["summary"]=chevron.render("{{details.user}} {{details.events.0.name}} from IP {{details.sourceipaddress}}",message)
```
The [chevron library](https://github.com/noahmorrison/chevron) allows us to use mustache templates to access fields and fields within lists to pull out information from the event as needed. ```details.events.0.name``` in this case is looking for the first item in the details.events list and if that exists, it uses the ```name``` field in the text. Chevron is forgiving, you can reference fields that may not exist, or only exist in some cases.

The utility libraries are purposefully crafted to allow you to get at the most stubborn data. In a gsuite event for example, the majority of the information is tucked away in key/value fields. Take this marker for suspicious logins as an example:

```json
    "events": [
        {
            "type": "login",
            "name": "login_success",
            "parameters": [
                {
                    "name": "login_type",
                    "value": "exchange"
                },
                {
                    "name": "login_challenge_method",
                    "multiValue": [
                        "none"
                    ]
                },
                {
                    "name": "is_suspicious",
                    "boolValue": false
                }
            ]
        }
    ]
```

You can see there are several 'name' fields with a parameters list that make it difficult to programatically query.

This plugin solves this via the use of the dict_match function like so:

```python
        #suspicious?
        suspicious={"boolvalue":True,"name":"is_suspicious"}
        for e in dot_message.get("details.events",[]):
            for p in e.get("parameters",[]):
                if dict_match(suspicious,p):
                    message["details"]["suspicious"]=True
```

The dict_match function takes a dictionary of keys and values and compares it to something. If the keys and values match, it returns true which in this case allows to mark an event as suspicious if the name='is_suspicious' and a field called 'boolvalue' is True.

Lastly the plugin returns the event and metadata back to the pipeline to be sent on to another plugin, or to the final data lake:

```python
        return (message, metadata)
```

It's best to include tests for plugins, and the [test for the gsuite login plugin can be found here](https://github.com/0xdefendA/defenda-data-lake/blob/main/lambdas/tests/test_plugin_gsuite_logins.py) as an example.