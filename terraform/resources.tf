# DynamoDB table for storing website state
resource "aws_dynamodb_table" "website_diff_state" {
  name         = var.ddb_table_name != "" ? var.ddb_table_name : "${var.project_name}-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "url"

  attribute {
    name = "url"
    type = "S"
  }

  tags = {
    Name    = "${var.project_name}-state"
    Project = var.project_name
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-checker"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "${var.project_name}-logs"
    Project = var.project_name
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-lambda-role"
    Project = var.project_name
  }
}

# Locals for ARN construction
locals {
  ses_identity_arn      = "arn:aws:ses:${var.region}:*:identity/*"
  cloudwatch_logs_arn   = "${aws_cloudwatch_log_group.lambda_logs.arn}:*"
}

# IAM Policy for Lambda
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}-lambda-policy"
  description = "Policy for website diff checker Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoState"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.website_diff_state.arn
      },
      {
        Sid      = "SendEmail"
        Effect   = "Allow"
        Action   = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = local.ses_identity_arn
      },
      {
        Sid      = "Logs"
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = local.cloudwatch_logs_arn
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-lambda-policy"
    Project = var.project_name
  }
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Lambda Function
resource "aws_lambda_function" "checker" {
  filename      = var.lambda_zip_path
  function_name = "${var.project_name}-checker"
  role          = aws_iam_role.lambda_role.arn
  handler       = "app.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      DDB_TABLE         = aws_dynamodb_table.website_diff_state.name
      SES_FROM          = var.ses_from_address
      SES_TO            = join(",", var.ses_to_addresses)
      URLS_JSON         = jsonencode(var.urls)
      USER_AGENT        = var.user_agent
      COOLDOWN_HOURS    = tostring(var.cooldown_hours)
      IGNORE_REGEX_JSON = var.ignore_regex_json
      SELECTOR_MAP_JSON = var.selector_map_json
      LOG_LEVEL         = var.log_level
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_policy_attachment
  ]

  tags = {
    Name    = "${var.project_name}-checker"
    Project = var.project_name
  }
}

# IAM Role for EventBridge Scheduler
resource "aws_iam_role" "scheduler_role" {
  name = "${var.project_name}-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-scheduler-role"
    Project = var.project_name
  }
}

# IAM Policy for Scheduler to invoke Lambda
resource "aws_iam_policy" "scheduler_policy" {
  name        = "${var.project_name}-scheduler-policy"
  description = "Policy for EventBridge Scheduler to invoke Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.checker.arn
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-scheduler-policy"
    Project = var.project_name
  }
}

# Attach policy to scheduler role
resource "aws_iam_role_policy_attachment" "scheduler_policy_attachment" {
  role       = aws_iam_role.scheduler_role.name
  policy_arn = aws_iam_policy.scheduler_policy.arn
}

# EventBridge Scheduler - Morning
resource "aws_scheduler_schedule" "morning" {
  name       = "${var.project_name}-morning"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = var.schedule_morning_cron

  target {
    arn      = aws_lambda_function.checker.arn
    role_arn = aws_iam_role.scheduler_role.arn
  }

  description = "Morning website diff check"
}

# EventBridge Scheduler - Evening
resource "aws_scheduler_schedule" "evening" {
  name       = "${var.project_name}-evening"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = var.schedule_evening_cron

  target {
    arn      = aws_lambda_function.checker.arn
    role_arn = aws_iam_role.scheduler_role.arn
  }

  description = "Evening website diff check"
}

# SES Email Identity (requires manual verification)
resource "aws_ses_email_identity" "from_email" {
  email = var.ses_from_address
}

# SNS Topic for Alarms (optional)
resource "aws_sns_topic" "alarms" {
  count = var.enable_alarms && var.alarm_email != "" ? 1 : 0
  name  = "${var.project_name}-alarms"

  tags = {
    Name    = "${var.project_name}-alarms"
    Project = var.project_name
  }
}

# SNS Topic Subscription for Alarms
resource "aws_sns_topic_subscription" "alarm_email" {
  count     = var.enable_alarms && var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# CloudWatch Alarm for Lambda Errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count               = var.enable_alarms ? 1 : 0
  alarm_name          = "${var.project_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert on Lambda function errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.checker.function_name
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.alarms[0].arn] : []

  tags = {
    Name    = "${var.project_name}-lambda-errors"
    Project = var.project_name
  }
}

# CloudWatch Alarm for Lambda Throttles
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  count               = var.enable_alarms ? 1 : 0
  alarm_name          = "${var.project_name}-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert on Lambda function throttles"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.checker.function_name
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.alarms[0].arn] : []

  tags = {
    Name    = "${var.project_name}-lambda-throttles"
    Project = var.project_name
  }
}
