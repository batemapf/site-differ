output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.checker.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.checker.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.website_diff_state.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.website_diff_state.arn
}

output "ses_identity_arn" {
  description = "ARN of the SES email identity"
  value       = aws_ses_email_identity.from_email.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch Log Group for Lambda"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "morning_schedule_name" {
  description = "Name of the morning schedule"
  value       = aws_scheduler_schedule.morning.name
}

output "evening_schedule_name" {
  description = "Name of the evening schedule"
  value       = aws_scheduler_schedule.evening.name
}
