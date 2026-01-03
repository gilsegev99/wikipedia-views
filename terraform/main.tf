## S3 Bucket

resource "aws_s3_bucket" "s3_bucket" {
  bucket = var.s3_bucket_name
}

## Lambda Function

resource "aws_iam_role" "lambda_role" {
  name = "aws_lambda_role"
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
  name        = "lambda_s3_put_policy"
  description = "Allow lambda to put objects into S3"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = ["s3:PutObject", "s3:GetObject"],
        Resource = "${aws_s3_bucket.s3_bucket.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_s3_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "archive_file" "lambda_zip" {
  type = "zip"
  source_dir = "../api_to_s3/lambda"
  output_path = "../api_to_s3/lambda/lambda.zip"
}

resource "aws_lambda_function" "lambda_function" {
  function_name = var.lambda_function_name
  filename = "../api_to_s3/lambda/lambda.zip"
  role = aws_iam_role.lambda_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.14"
  timeout = 420 
  depends_on = [ aws_iam_role_policy_attachment.lambda_policy_attach ]
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  environment {
    variables = {
      USER_AGENT_STRING = var.user_agent_string
      BUCKET_NAME = var.s3_bucket_name
    }
  }
}

## Lambda Function Trigger

resource "aws_cloudwatch_event_rule" "daily_at_0700_utc" {
  name = "daily-at-0700-utc"
  schedule_expression = "cron(0 7 * * ? *)"  
}

resource "aws_cloudwatch_event_target" "daily_at_0700_utc" {
    rule = aws_cloudwatch_event_rule.daily_at_0700_utc.name
    target_id = "lambda_function"
    arn = aws_lambda_function.lambda_function.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_lambda_function" {
    statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = aws_lambda_function.lambda_function.function_name
    principal = "events.amazonaws.com"
    source_arn = aws_cloudwatch_event_rule.daily_at_0700_utc.arn
}