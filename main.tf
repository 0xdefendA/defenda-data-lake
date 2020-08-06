terraform {
  required_version = ">=0.12.25"
  required_providers {
    aws = ">= 2.25.0"
  }
}

provider "aws" {
  region  = "us-west-2"
  profile = "default"
}
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

output "account_id" {
  value = "${data.aws_caller_identity.current.account_id}"
}


resource "aws_s3_bucket" "data_lake_input_bucket" {
  bucket = "data-lake-${data.aws_caller_identity.current.account_id}-input-bucket"
  acl    = "private"

  versioning {
    enabled = false
  }

  lifecycle_rule {
    enabled = true

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake_input_bucket" {
  bucket = aws_s3_bucket.data_lake_input_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "data_lake_output_bucket" {
  bucket = "data-lake-${data.aws_caller_identity.current.account_id}-output-bucket"
  acl    = "private"

  versioning {
    enabled = false
  }

  lifecycle_rule {
    enabled = true

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 360
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake_output_bucket" {
  bucket = aws_s3_bucket.data_lake_output_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "data-lake-firehose-role" {
  name = "data-lake-firehose-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "firehose.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "data-lake-firehose-policy" {
  name = "data-lake-firehose-policy"
  role = aws_iam_role.data-lake-firehose-role.id

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": [
        "glue:GetTable",
        "glue:GetTableVersion",
        "glue:GetTableVersions"
      ],
      "Resource": "*"
    },
    {
      "Action": [
        "s3:*"
      ],
      "Effect": "Allow",
      "Resource": [
        "${aws_s3_bucket.data_lake_output_bucket.arn}",
        "${aws_s3_bucket.data_lake_output_bucket.arn}/*"
      ]
    },
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": [
          "logs:PutLogEvents"
      ],
      "Resource": [
          "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/kinesisfirehose/data-lake-firehose-logging:log-stream:*"
      ]
    },
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": [
          "kinesis:DescribeStream",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords"
      ],
      "Resource": "arn:aws:kinesis:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stream/data-lake-firehose-logging"
    }
  ]
}
EOF
}

resource "aws_kinesis_firehose_delivery_stream" "data-lake-firehose-logging" {
  name        = "data-lake-firehose-logging"
  destination = "extended_s3"
  extended_s3_configuration {
    bucket_arn          = aws_s3_bucket.data_lake_output_bucket.arn
    buffer_interval     = 60
    buffer_size         = 1
    compression_format  = "GZIP"
    error_output_prefix = "errors"
    role_arn            = aws_iam_role.data-lake-firehose-role.arn
  }
}


resource "aws_s3_bucket" "data_lake_athena_bucket" {
  bucket = "${data.aws_caller_identity.current.account_id}-aws-athena-query-results-${data.aws_region.current.name}"
  acl    = "private"

  versioning {
    enabled = false
  }

  lifecycle_rule {
    enabled = true

    expiration {
      days = 30
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake_athena_bucket" {
  bucket = aws_s3_bucket.data_lake_athena_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_athena_database" "defenda_datalake" {
  name   = "defenda_datalake"
  bucket = aws_s3_bucket.data_lake_athena_bucket.id
}

resource "aws_glue_catalog_table" "data_lake_events_table" {
  name          = "events"
  database_name = aws_athena_database.defenda_datalake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL = "TRUE"
  }

  partition_keys {
    name = "year"
    type = "string"
  }

  partition_keys {
    name = "month"
    type = "string"
  }

  partition_keys {
    name = "day"
    type = "string"
  }

  partition_keys {
    name = "hour"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake_output_bucket.id}/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat"

    ser_de_info {
      name                  = "json-serde"
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    columns {
      name = "eventid"
      type = "string"
    }

    columns {
      name = "_base64"
      type = "string"
    }

    columns {
      name = "utctimestamp"
      type = "string"
    }

    columns {
      name = "severity"
      type = "string"
    }

    columns {
      name = "summary"
      type = "string"
    }

    columns {
      name = "category"
      type = "string"
    }

    columns {
      name = "source"
      type = "string"
    }

    columns {
      name = "tags"
      type = "array<string>"
    }

    columns {
      name = "plugins"
      type = "array<string>"
    }

    columns {
      name = "details"
      type = "string"
    }

  }
}


resource "aws_iam_role" "data_lake_instance_role" {
  name = "data_lake_instance_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_instance_profile" "data_lake_instance_profile" {
  name = "data_lake_instance_profile"
  role = aws_iam_role.data_lake_instance_role.name
}

resource "aws_iam_role_policy" "data_lake_instance_policy" {
  name = "data_lake_instance_policy"
  role = aws_iam_role.data_lake_instance_role.id

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:*"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Action": [
      "glue:GetDatabase*",
      "glue:GetTable*",
      "glue:GetPartitions",
      "glue:BatchCreatePartition"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Action": [
      "athena:Get*",
      "athena:ListQueryExecutions",
      "athena:StartQueryExecution"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Action":[
      "secretsmanager:GetSecretValue"
      ],
      "Effect": "Allow",
      "Resource":"arn:aws:secretsmanager:*:*:secret:data_lake*"
    }
  ]
}
EOF
}


