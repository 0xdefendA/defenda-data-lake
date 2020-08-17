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

output "datalake_arn" {
  value = aws_athena_database.defenda_datalake.id
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




resource "aws_s3_bucket" "data_lake_athena_bucket" {
  bucket = "${data.aws_caller_identity.current.account_id}-defenda-data-lake-athena-query-results-${data.aws_region.current.name}"
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

resource "aws_athena_workgroup" "defenda_datalake_workgroup" {
  name = "defenda_datalake"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_lake_athena_bucket.bucket}/"
    }
  }
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

data "aws_iam_policy_document" "data_lake_lambda_role_policy_document" {
  statement {
    sid = "1"

    actions = [
      "s3:*",
    ]

    resources = [
      aws_s3_bucket.data_lake_input_bucket.arn,
      "${aws_s3_bucket.data_lake_input_bucket.arn}/*",
      aws_s3_bucket.data_lake_output_bucket.arn,
      "${aws_s3_bucket.data_lake_output_bucket.arn}/*",
      aws_s3_bucket.data_lake_athena_bucket.arn,
      "${aws_s3_bucket.data_lake_athena_bucket.arn}/*"
    ]
  }
  statement {
    sid = "2"
    actions = [
      "glue:GetDatabase*",
      "glue:GetTable*",
      "glue:GetPartitions",
      "glue:BatchCreatePartition"
    ]
    resources = ["*"]
  }
  statement {
    sid = "3"
    actions = [
      "athena:Get*",
      "athena:ListQueryExecutions",
      "athena:StartQueryExecution"
    ]
    resources = [
      "arn:aws:athena:*:*:workgroup/*",
      "arn:aws:athena:*:*:datacatalog/*"
    ]
  }
  statement {
    sid = "4"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [
      aws_lambda_function.data_lake_firehose_input.arn,
      "${aws_lambda_function.data_lake_firehose_input.arn}:$LATEST"
    ]
  }
  statement {
    sid = "5"
    actions = [
      "firehose:PutRecordBatch"
    ]
    resources = [
      aws_kinesis_firehose_delivery_stream.data_lake_s3_stream.arn
    ]
  }
}

resource "aws_iam_role" "data_lake_lambda_role" {
  name               = "data_lake_lambda_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}


resource "aws_iam_policy" "data_lake_lambda_role_policy" {
  name   = "data_lake_lambda_role_policy"
  path   = "/"
  policy = data.aws_iam_policy_document.data_lake_lambda_role_policy_document.json
}

resource "aws_iam_role_policy_attachment" "data_lake_lambda_role_attach" {
  role       = aws_iam_role.data_lake_lambda_role.name
  policy_arn = aws_iam_policy.data_lake_lambda_role_policy.arn
}


resource "aws_iam_role_policy_attachment" "lambda-exec-role" {
  role       = aws_iam_role.data_lake_lambda_role.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "data_lake_firehose_input" {
  filename         = "lambdas/lambda.zip"
  function_name    = "data_lake_firehose_input"
  role             = aws_iam_role.data_lake_lambda_role.arn
  handler          = "processor.lambda_handler"
  runtime          = "python3.8"
  timeout          = 100
  source_code_hash = filesha256("lambdas/lambda.zip")
}

resource "aws_lambda_function" "data_lake_s3_input" {
  filename         = "lambdas/lambda.zip"
  function_name    = "data_lake_s3_input"
  role             = aws_iam_role.data_lake_lambda_role.arn
  handler          = "s3_to_firehose.lambda_handler"
  runtime          = "python3.8"
  timeout          = 100
  source_code_hash = filesha256("lambdas/lambda.zip")
}

resource "aws_lambda_function" "data_lake_generate_partitions_lambda" {
  filename         = "lambdas/lambda.zip"
  function_name    = "data_lake_generate_partitions"
  role             = aws_iam_role.data_lake_lambda_role.arn
  handler          = "generate_partitions.lambda_handler"
  runtime          = "python3.8"
  timeout          = 100
  source_code_hash = filesha256("lambdas/lambda.zip")
}

# cloudwatch timer for the generate partitions lambda
resource "aws_cloudwatch_event_rule" "data_lake_generate_partitions_event" {
  name                = "data_lake_generate_partitions_event"
  description         = "Trigger a call to generate an athena partition"
  schedule_expression = "cron(0/10 * * * ? *)"
}

resource "aws_lambda_permission" "data_lake_allow_cloudwatch_generate_partitions" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_lake_generate_partitions_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.data_lake_generate_partitions_event.arn
}

resource "aws_cloudwatch_event_target" "data_lake_generate_partitions_event_target" {
  target_id = "data_lake_generate_partitions_event_target"
  rule      = aws_cloudwatch_event_rule.data_lake_generate_partitions_event.name
  arn       = aws_lambda_function.data_lake_generate_partitions_lambda.arn
}


# s3 lambda trigger
resource "aws_lambda_permission" "allow_bucket_lambda" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_lake_s3_input.arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_lake_input_bucket.arn
}

resource "aws_s3_bucket_notification" "lambda_bucket_notification" {
  bucket = aws_s3_bucket.data_lake_input_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.data_lake_s3_input.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_bucket_lambda]
}

resource "aws_iam_role" "data_lake_firehose_role" {
  name = "data_lake_firehose_role"

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

data "aws_iam_policy_document" "data_lake_firehose_role_policy_document" {
  statement {
    sid = "1"

    actions = [
      "s3:*",
    ]

    resources = [
      aws_s3_bucket.data_lake_output_bucket.arn,
      "${aws_s3_bucket.data_lake_output_bucket.arn}/*"
    ]
  }
  statement {
    sid = "2"
    actions = [
      "kinesis:DescribeStreamSummary",
      "kinesis:GetShardIterator",
      "kinesis:GetRecords",
      "kinesis:ListShards",
      "kinesis:SubscribeToShard",
      "kinesis:DescribeStream",
    ]
    resources = [aws_kinesis_firehose_delivery_stream.data_lake_s3_stream.arn]
  }
  statement {
    sid = "3"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
  statement {
    sid = "4"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [aws_lambda_function.data_lake_firehose_input.arn,
    "${aws_lambda_function.data_lake_firehose_input.arn}:$LATEST"]
  }
}

resource "aws_iam_policy" "data_lake_firehose_role_policy" {
  name   = "data_lake_firehose_role_policy"
  path   = "/"
  policy = data.aws_iam_policy_document.data_lake_firehose_role_policy_document.json
}

resource "aws_iam_role_policy_attachment" "data_lake_firehose_role_attach" {
  role       = aws_iam_role.data_lake_firehose_role.name
  policy_arn = aws_iam_policy.data_lake_firehose_role_policy.arn
}

resource "aws_kinesis_firehose_delivery_stream" "data_lake_s3_stream" {
  name        = "data_lake_s3_stream"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn            = aws_iam_role.data_lake_firehose_role.arn
    bucket_arn          = aws_s3_bucket.data_lake_output_bucket.arn
    compression_format  = "GZIP"
    buffer_interval     = 60
    buffer_size         = 1
    error_output_prefix = "errors"

    processing_configuration {
      enabled = "true"

      processors {
        type = "Lambda"

        parameters {
          parameter_name  = "LambdaArn"
          parameter_value = "${aws_lambda_function.data_lake_firehose_input.arn}:$LATEST"
        }
      }
    }
  }
}

