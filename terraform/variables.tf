variable "project_name" {
  description = "Name of the project, used as prefix for resources"
  type        = string
  default     = "website-diff-checker"
}

variable "region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "schedule_morning_cron" {
  description = "Cron expression for morning check (EventBridge Scheduler format)"
  type        = string
  default     = "cron(0 6 * * ? *)"  # 6 AM UTC daily
}

variable "schedule_evening_cron" {
  description = "Cron expression for evening check (EventBridge Scheduler format)"
  type        = string
  default     = "cron(0 18 * * ? *)"  # 6 PM UTC daily
}

variable "urls" {
  description = "List of URLs to monitor"
  type        = list(string)
  default     = []
}

variable "ses_from_address" {
  description = "Verified SES email address for sending notifications"
  type        = string
}

variable "ses_to_addresses" {
  description = "List of email addresses to receive notifications"
  type        = list(string)
}

variable "ddb_table_name" {
  description = "DynamoDB table name for storing state"
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

variable "lambda_zip_path" {
  description = "Path to Lambda deployment package"
  type        = string
  default     = "../lambda/lambda_function.zip"
}

variable "user_agent" {
  description = "User-Agent string for HTTP requests"
  type        = string
  default     = "Website-Diff-Checker/1.0"
}

variable "cooldown_hours" {
  description = "Minimum hours between notifications for the same URL"
  type        = number
  default     = 0
}

variable "ignore_regex_json" {
  description = "JSON array of regex patterns to ignore in content"
  type        = string
  default     = "[]"
}

variable "selector_map_json" {
  description = "JSON map of URL to CSS selector for scoping extraction"
  type        = string
  default     = "{}"
}

variable "log_level" {
  description = "Lambda logging level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
}

variable "enable_alarms" {
  description = "Enable CloudWatch alarms"
  type        = bool
  default     = true
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = ""
}
