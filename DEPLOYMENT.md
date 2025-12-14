# Deployment Guide

This guide walks you through deploying the Website Diff Checker from scratch.

## Prerequisites

Before you begin, ensure you have:

- [ ] AWS Account with administrator access
- [ ] AWS CLI installed and configured
- [ ] Terraform >= 1.0 installed
- [ ] Python 3.12 installed
- [ ] Git installed

## Step-by-Step Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/batemapf/site-differ.git
cd site-differ
```

### 2. Set Up AWS SES Email

You need to verify at least one email address (or domain) in AWS SES:

```bash
# Set your AWS region
export AWS_REGION=us-east-1

# Verify your sender email
aws ses verify-email-identity --email-address noreply@yourdomain.com

# Verify your recipient email (required if in SES sandbox)
aws ses verify-email-identity --email-address your-email@example.com
```

Check your email inbox and click the verification links from AWS.

**Verify the emails are confirmed:**
```bash
aws ses list-identities
```

### 3. Build the Lambda Package

```bash
cd lambda
chmod +x build.sh
./build.sh
cd ..
```

You should see `lambda_function.zip` created (approximately 18MB).

### 4. Configure Terraform Variables

Create a `terraform.tfvars` file:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your configuration:

```hcl
# Required settings
project_name = "website-diff-checker"
region       = "us-east-1"

# SES configuration (use verified emails)
ses_from_address = "noreply@yourdomain.com"
ses_to_addresses = ["your-email@example.com"]

# URLs to monitor
urls = [
  "https://example.com",
  "https://www.python.org",
]

# Optional: Enable alarms
enable_alarms = true
alarm_email   = "your-email@example.com"

# Optional: Schedule (cron format for EventBridge Scheduler)
schedule_morning_cron = "cron(0 6 * * ? *)"   # 6 AM UTC
schedule_evening_cron = "cron(0 18 * * ? *)"  # 6 PM UTC
```

### 5. Deploy Infrastructure with Terraform

```bash
# Initialize Terraform
terraform init

# Review the execution plan
terraform plan

# Apply the configuration
terraform apply
```

Type `yes` when prompted to confirm.

**Expected resources created:**
- DynamoDB table: `website-diff-checker-state`
- Lambda function: `website-diff-checker-checker`
- EventBridge schedules: morning and evening
- IAM roles and policies
- CloudWatch log group
- SES email identity
- CloudWatch alarms (if enabled)

### 6. Verify Deployment

Check that resources were created:

```bash
# Check Lambda function
aws lambda get-function --function-name website-diff-checker-checker

# Check DynamoDB table
aws dynamodb describe-table --table-name website-diff-checker-state

# Check EventBridge schedules
aws scheduler list-schedules --group-name default | grep website-diff-checker
```

### 7. Test the Lambda Function

Manually invoke the Lambda function:

```bash
aws lambda invoke \
  --function-name website-diff-checker-checker \
  --log-type Tail \
  --query 'LogResult' \
  --output text \
  output.json | base64 -d

# View the response
cat output.json
```

Expected output:
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Website diff check completed\", \"urls_checked\": 2, \"changes_detected\": 2}"
}
```

Since these are new URLs, you should receive an email with change notifications.

### 8. Verify Email Notification

Check your inbox for an email with subject like:
```
Website changes detected (2 of 2) - 2024-12-14 14:45 UTC
```

The email should contain:
- List of changed URLs
- Diff snippets for each URL
- Links to the URLs

### 9. Check CloudWatch Logs

View the Lambda execution logs:

```bash
aws logs tail /aws/lambda/website-diff-checker-checker --follow
```

Or use the AWS Console:
1. Navigate to CloudWatch > Log groups
2. Click `/aws/lambda/website-diff-checker-checker`
3. View the latest log stream

### 10. (Optional) Test Scheduled Execution

Wait for the next scheduled run (morning or evening), or manually trigger via EventBridge:

```bash
aws scheduler get-schedule \
  --name website-diff-checker-morning \
  --group-name default
```

## Post-Deployment Configuration

### Add More URLs

Edit `terraform/terraform.tfvars`:

```hcl
urls = [
  "https://example.com",
  "https://www.python.org",
  "https://github.com",  # New URL
]
```

Apply changes:
```bash
cd terraform
terraform apply
```

### Configure Noise Reduction

If you're getting false positives from dynamic content:

**Option 1: Use CSS selectors to scope content**
```hcl
selector_map_json = jsonencode({
  "https://example.com" = "#main-content"
})
```

**Option 2: Ignore specific patterns**
```hcl
ignore_regex_json = jsonencode([
  "Last updated:.*",
  "Copyright \\d{4}",
  "Session ID:.*"
])
```

Apply changes:
```bash
terraform apply
```

### Enable Notification Cooldown

To prevent spam from frequently changing pages:

```hcl
cooldown_hours = 6  # Wait 6 hours between notifications for same URL
```

### Adjust Schedule

Change check frequency:

```hcl
# Check every 4 hours instead of twice daily
schedule_morning_cron = "cron(0 */4 * * ? *)"
schedule_evening_cron = "cron(0 */4 * * ? *)"  # Or disable by commenting out
```

## GitHub Actions Setup (Optional)

To enable automated deployments via GitHub Actions:

### 1. Create IAM User for GitHub Actions

For security, use a custom IAM policy with least-privilege permissions instead of `AdministratorAccess`:

```bash
# Create IAM user
aws iam create-user --user-name github-actions-deploy

# Create a custom policy with minimal required permissions
cat > github-actions-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DeleteTable",
        "dynamodb:DescribeTable",
        "dynamodb:ListTables",
        "dynamodb:UpdateTable",
        "dynamodb:TagResource"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:DeleteFunction",
        "lambda:GetFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:TagResource",
        "lambda:AddPermission",
        "lambda:RemovePermission"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:PassRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:CreatePolicy",
        "iam:DeletePolicy",
        "iam:GetPolicy",
        "iam:GetPolicyVersion",
        "iam:TagRole",
        "iam:TagPolicy"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:DeleteLogGroup",
        "logs:DescribeLogGroups",
        "logs:PutRetentionPolicy",
        "logs:TagResource"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:VerifyEmailIdentity",
        "ses:DeleteIdentity",
        "ses:GetIdentityVerificationAttributes"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "scheduler:CreateSchedule",
        "scheduler:DeleteSchedule",
        "scheduler:GetSchedule",
        "scheduler:UpdateSchedule",
        "scheduler:TagResource"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DeleteAlarms",
        "cloudwatch:DescribeAlarms"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:CreateTopic",
        "sns:DeleteTopic",
        "sns:GetTopicAttributes",
        "sns:Subscribe",
        "sns:Unsubscribe",
        "sns:TagResource"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create and attach the policy
aws iam create-policy \
  --policy-name GitHubActionsDeployPolicy \
  --policy-document file://github-actions-policy.json

# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach the policy to the user
aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/GitHubActionsDeployPolicy
```

**Security Note:** This policy follows least-privilege principles. For even tighter security, consider using OIDC federation with GitHub Actions instead of long-lived access keys.

### 2. Create Access Keys

```bash
aws iam create-access-key --user-name github-actions-deploy
```

Save the `AccessKeyId` and `SecretAccessKey` output.

### 3. Add GitHub Secrets

In your GitHub repository, go to Settings > Secrets and variables > Actions, and add:

| Secret Name | Value |
|------------|-------|
| `AWS_ACCESS_KEY_ID` | Your access key ID |
| `AWS_SECRET_ACCESS_KEY` | Your secret access key |
| `SES_FROM_ADDRESS` | noreply@yourdomain.com |
| `SES_TO_ADDRESS` | your-email@example.com |
| `MONITOR_URLS` | `["https://example.com"]` |
| `ALARM_EMAIL` | your-email@example.com |

### 4. Push Changes

```bash
git push origin main
```

GitHub Actions will automatically:
- Run tests on every push
- Deploy Terraform changes to main branch
- Deploy Lambda updates to main branch

## Troubleshooting

### SES Sandbox Mode

**Issue:** Emails not being delivered

**Solution:** 
1. Verify both sender and recipient emails
2. Request SES production access: AWS Console → SES → Account dashboard → Request production access

### Lambda Timeout

**Issue:** Lambda function timing out

**Solution:** Increase timeout in `terraform/variables.tf`:
```hcl
lambda_timeout = 60  # Increase from 30 to 60 seconds
```

### False Positives

**Issue:** Too many change notifications

**Solutions:**
1. Use CSS selectors to focus on specific content
2. Add ignore patterns for dynamic content
3. Enable cooldown period

### 403/429 Errors

**Issue:** Websites blocking requests

**Solutions:**
1. Adjust User-Agent: `user_agent = "Mozilla/5.0 (compatible; YourBot/1.0)"`
2. Reduce check frequency
3. Add delays between requests (modify Lambda code)

## Maintenance

### View DynamoDB State

```bash
# List all monitored URLs
aws dynamodb scan --table-name website-diff-checker-state

# Get specific URL state
aws dynamodb get-item \
  --table-name website-diff-checker-state \
  --key '{"url": {"S": "https://example.com"}}'
```

### Reset URL State

To force a fresh check (will trigger notification):

```bash
aws dynamodb delete-item \
  --table-name website-diff-checker-state \
  --key '{"url": {"S": "https://example.com"}}'
```

### Update Lambda Code

If you modify the Lambda code:

```bash
cd lambda
./build.sh
cd ../terraform
terraform apply
```

### Cleanup / Destroy

To remove all resources:

```bash
cd terraform
terraform destroy
```

Type `yes` to confirm.

## Cost Estimate

Monthly cost for typical usage (2 checks/day, 10 URLs):
- Lambda: ~$0.20
- DynamoDB: ~$0.00 (minimal reads/writes)
- SES: ~$0.00 (first 62,000 emails free)
- CloudWatch: ~$0.50
- **Total: ~$1/month**

## Next Steps

1. Monitor CloudWatch logs for errors
2. Adjust schedules based on needs
3. Add more URLs to monitor
4. Configure noise reduction as needed
5. Set up AWS Budgets for cost alerts
6. Consider enabling DynamoDB backups

## Support

For issues:
- Check CloudWatch logs
- Review this guide
- Open an issue on GitHub
