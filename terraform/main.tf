## S3 Bucket

resource "aws_s3_bucket" "s3_bucket" {
  bucket = var.s3_bucket_name
}

## Lambda Function Main

resource "aws_iam_role" "lambda_main_role" {
  name = "aws_lambda_main_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_s3_policy" {
  name        = "lambda_s3_policy"
  description = "Allow lambda to put and get objects in S3"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = ["s3:PutObject", "s3:HeadObject", "s3:GetObject"],
        Resource = "${aws_s3_bucket.s3_bucket.arn}/*"
      },
      {      
        Effect = "Allow",
        Action = "s3:ListBucket",
        Resource = "${aws_s3_bucket.s3_bucket.arn}"
        },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_main_policy_attach" {
  role       = aws_iam_role.lambda_main_role.name
  policy_arn = aws_iam_policy.lambda_s3_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_main_basic_execution" {
  role       = aws_iam_role.lambda_main_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "archive_file" "lambda_main_zip" {
  type = "zip"
  source_dir = "../api_to_s3/lambda_main"
  output_path = "../api_to_s3/lambda_main/lambda.zip"
}

resource "aws_lambda_function" "lambda_function_main" {
  function_name = var.lambda_function_main_name
  filename = "../api_to_s3/lambda_main/lambda.zip"
  role = aws_iam_role.lambda_main_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.14"
  timeout = 420 
  depends_on = [ aws_iam_role_policy_attachment.lambda_main_policy_attach ]
  source_code_hash = data.archive_file.lambda_main_zip.output_base64sha256
  environment {
    variables = {
      USER_AGENT_STRING = var.user_agent_string
      BUCKET_NAME = var.s3_bucket_name
    }
  }
}

## Lambda Function Main Trigger

resource "aws_cloudwatch_event_rule" "daily_at_0700_utc" {
  name = "daily-at-0700-utc"
  schedule_expression = "cron(0 7 * * ? *)"  
}

resource "aws_cloudwatch_event_target" "daily_at_0700_utc" {
    rule = aws_cloudwatch_event_rule.daily_at_0700_utc.name
    target_id = "lambda_function"
    arn = aws_lambda_function.lambda_function_main.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_lambda_function" {
    statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = aws_lambda_function.lambda_function_main.function_name
    principal = "events.amazonaws.com"
    source_arn = aws_cloudwatch_event_rule.daily_at_0700_utc.arn
}

## Lambda Function Date Generator

resource "aws_iam_role" "lambda_date_generator_role" {
  name = "aws_lambda_date_generator_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_date_generator_basic_execution" {
  role       = aws_iam_role.lambda_date_generator_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "archive_file" "lambda_date_generator_zip" {
  type = "zip"
  source_dir = "../api_to_s3/lambda_date_generator"
  output_path = "../api_to_s3/lambda_date_generator/lambda.zip"
}

resource "aws_lambda_function" "lambda_function_date_generator" {
  function_name = var.lambda_function_date_generator_name
  filename = "../api_to_s3/lambda_date_generator/lambda.zip"
  role = aws_iam_role.lambda_date_generator_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.14"
  timeout = 30
  depends_on = [ ]
  source_code_hash = data.archive_file.lambda_date_generator_zip.output_base64sha256
}

## Step Functions State Machines

resource "aws_iam_role" "backfill_state_machine_role" {
  name = "backfill_state_machine_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "states.amazonaws.com"
      }
      }
    ]
  })
}

data "aws_iam_policy_document" "backfill_state_machine_role_policy" {
  statement {
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = ["${aws_lambda_function.lambda_function_main.arn}",
                "${aws_lambda_function.lambda_function_date_generator.arn}"]
  }
}

# Create an IAM policy for the Step Functions state machine
resource "aws_iam_role_policy" "StateMachinePolicy" {
  role   = aws_iam_role.backfill_state_machine_role.id
  policy = data.aws_iam_policy_document.backfill_state_machine_role_policy.json
}

resource "aws_sfn_state_machine" "backfill_sfn_state_machine" {
  name     = var.backfill_state_machine_name
  role_arn = aws_iam_role.backfill_state_machine_role.arn

  definition = templatefile("${path.module}/statemachine/backfill_state_machine_asl.json",
    { DateGeneratorLambda = aws_lambda_function.lambda_function_date_generator.arn,
    DateProcessorLambda = aws_lambda_function.lambda_function_main.arn}
  )
}

## Glue Transformation Job

resource "aws_glue_job" "glue_bronze_to_silver_job" {
  name              = "glue_bronze_to_silver_job"
  description       = "A Glue job to convert json files to flattened Parquet files."
  role_arn          = aws_iam_role.glue_bronze_to_silver_role.arn
  glue_version      = "5.0"
  max_retries       = 0
  timeout           = 30
  number_of_workers = 2
  worker_type       = "G.1X"
  connections       = []
  execution_class   = "STANDARD"

  command {
    script_location = "s3://${aws_s3_bucket.s3_bucket.bucket}/glue_scripts/process_raw_data.py"
    name            = "glueetl"
    python_version  = "3"
  }

  notification_property {
    notify_delay_after = 3 # delay in minutes
  }

  default_arguments = {
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                   = "true"
    "--enable-auto-scaling"              = "true"
    "--enable-job-insights"              = "true"
    "--enable-glue-datacatalog"          = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = {
    "ManagedBy" = "AWS"
  }
}

# IAM role for Glue jobs
resource "aws_iam_role" "glue_bronze_to_silver_role" {
  name = "glue-job-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_s3_object" "glue_bronze_to_silver_script" {
  bucket = var.s3_bucket_name
  key    = "glue_scripts/process_raw_data.py"
  source = "../glue_scripts/process_raw_data.py" # Make sure this file exists locally
  etag = filemd5("../glue_scripts/process_raw_data.py")
}

data "aws_iam_policy_document" "glue_bronze_to_silver_policy" {
  statement {
    effect = "Allow"

    actions = ["s3:GetObject"]

    resources = ["${aws_s3_bucket.s3_bucket.arn}/*"]
  }

  statement {
    effect = "Allow"

    actions = ["s3:PutObject", "s3:DeleteObject"]

    resources = ["${aws_s3_bucket.s3_bucket.arn}/processed/views_data/*"]
  }

  statement {
    effect = "Allow"

    actions = ["s3:ListBucket"]

    resources = ["${aws_s3_bucket.s3_bucket.arn}"]
  }

  statement {
    effect = "Allow"

    actions = [
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:GetTable",
      "glue:GetDatabase",
      "glue:GetPartitions",
      "glue:CreatePartition"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "glue_bronze_to_silver_role_policy" {
  role   = aws_iam_role.glue_bronze_to_silver_role.id
  policy = data.aws_iam_policy_document.glue_bronze_to_silver_policy.json
}

# Glue Catalog Database

resource "aws_glue_catalog_database" "glue_catalog_database" {
  name = "wikimedia-data"
}