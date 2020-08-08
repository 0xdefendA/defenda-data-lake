# defendA Data Lake
An AWS-native, serverless log management system to allow you to ingest unstructured JSON, normalize & enrich it and store it in Athena for queries and analysis.

## Why?
Centralized log/event management is a core element of an infosec program, yet most solutions are not cloud native, require unnecessary servers/clusters and force you to massage your events into a strict format.

The reality is that infosec teams aren't able to dictate what format events come in which is usually arbitrary, nested JSON.

This solution uses only serverless constructs to allow you to store unstructured JSON from any source in a predictable data structure that can be accessed using Athena's native SQL.

## Deployment:

Deployment is via terraform and a mini-docker environment to compile the lambdas.

It uses us-west-2 as the default region, set a terraform.tfvars variable ( aws_region = "some-other-region ) if you'd like it elsewhere.



Init terraform
```bash
terraform init
./generate_lambda_zip.py
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
- _base64 (string)
    - a base64 representation of the entire event. Athena returns csv by default which can be troublesome to return to JSON. Decoding this field yields the native json for the event.
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

FROM "defenda_datalake"."events"
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
Queries can be any valid (Presto SQL)[https://prestodb.io/docs/current/sql/select.html] including (functions)[https://prestodb.io/docs/current/functions.html]

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

### Disadvantages

#### Latency
Depending on your rate of event ingestion, firehose will queue events for 60 seconds before flushing to s3. If you have enough flow, this usually isn't a problem but if your event flow is very low you may see a delay.

#### Cost potential

Athena's pricing is based on $/query/data that as of this writing is $5 per terabyte. Each query is charged based on the amount of underlying data that was scanned to resolve the query and prorated accordingly. So if your query operated on a megabyte of data in a partition, your charge would be only for that megabyte.

However it is a `per query` charge. So if you aren't careful with your queries and don't make use of partitions you can run up a bill.

To help, data is automatically partitioned in hour chunks (year/month/day/hour structure in the s3 bucket). By simply adding some criteria to your where clause you can limit the amount of data you interact with and are charged for. Data is also automatically gzipped to also reduce the charges.