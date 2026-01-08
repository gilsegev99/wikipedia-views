variable "region" {
  description = "Region"
  default     = "eu-west-2"
}

variable "s3_bucket_name" {
  description = "My Wikimedia data bucket"
  default     = "wikimedia-data-bucket"
}

variable "lambda_function_main_name" {
  description = "The lambda function to extract Wikimedia data"
  default     = "lambda-wikimedia-data-extractor"
}

variable "lambda_function_date_generator_name" {
  description = "The lambda function to generate a date range for backfill jobs"
  default     = "lambda-date-range-generator"
}

variable "user_agent_string" {
  description = "The User-Agent header used in API requests"
  default = "Page views analysis (https://github.com/gilsegev99)"
  type = string
}
