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
        Effect   = "Allow",
        Action   = ["s3:PutObject"],
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
  output_path = "../api_to_s3/lambda/lambda_function.zip"
}

resource "aws_lambda_function" "lambda_function" {
  function_name = var.lambda_function_name
  filename = "../api_to_s3/lambda/lambda_function.zip"
  role = aws_iam_role.lambda_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.14"
  depends_on = [ aws_iam_role_policy_attachment.lambda_policy_attach ]
  environment {
    variables = {
      USER_AGENT_STRING = var.user_agent_string
      BUCKET_NAME = var.s3_bucket_name
    }
  }
  layers = [ aws_lambda_layer_version.lambda_layer.arn ]
}

resource "aws_lambda_layer_version" "lambda_layer" {
  filename   = "../api_to_s3/lambda/layer.zip"
  layer_name = "lambda-wikimedia-data-extractor-layer"

  compatible_runtimes = ["python3.14"]
}