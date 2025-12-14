# Website Diff Checker

An automated system to monitor website content changes and send email notifications when changes are detected.

## Overview

This project implements a serverless website monitoring solution using AWS Lambda, DynamoDB, SES, and EventBridge Scheduler. It periodically checks configured URLs for content changes and sends email notifications with diff snippets when changes are detected.

## Features

- **Automated Monitoring**: Scheduled checks twice daily (configurable)
- **Intelligent Diffing**: HTML normalization and text-based comparison
- **Smart Notifications**: Digest emails with diff snippets
- **Conditional Requests**: Uses ETags and Last-Modified headers to reduce bandwidth
- **Flexible Configuration**: CSS selectors and regex patterns for noise reduction
- **Error Handling**: Tracks consecutive failures and alerts
- **CloudWatch Monitoring**: Logs and alarms for operational visibility

## Architecture

```
┌─────────────────┐         ┌──────────────┐
│  EventBridge    │────────▶│   Lambda     │
│   Scheduler     │         │   Function   │
└─────────────────┘         └──────┬───────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌──────────┐   ┌──────────┐   ┌──────────┐
            │ DynamoDB │   │   SES    │   │  Target  │
            │  Table   │   │  Email   │   │ Websites │
            └──────────┘   └──────────┘   └──────────┘
```

## Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.0
- Python 3.12
- AWS CLI (for manual operations)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/batemapf/site-differ.git
cd site-differ
```

### 2. Build Lambda Package

```bash
cd lambda
chmod +x build.sh
./build.sh
cd ..
```

### 3. Configure Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your configuration:

```hcl
ses_from_address = "noreply@yourdomain.com"
ses_to_addresses = ["your-email@example.com"]
urls = [
  "https://example.com",
  "https://www.example.org/page"
]
```

### 4. Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### 5. Verify SES Email

After deployment, verify your email addresses in AWS SES:
1. Check your email for verification links from AWS
2. Click the verification links to activate the email addresses

### 6. Test the Function

```bash
aws lambda invoke \
  --function-name website-diff-checker-checker \
  --log-type Tail \
  output.json

cat output.json
```

## Configuration

### Environment Variables

The Lambda function uses the following environment variables (configured via Terraform):

- `DDB_TABLE`: DynamoDB table name for state storage
- `SES_FROM`: Verified sender email address
- `SES_TO`: Comma-separated recipient email addresses
- `URLS_JSON`: JSON array of URLs or URL objects with selectors
- `USER_AGENT`: User-Agent string for HTTP requests
- `COOLDOWN_HOURS`: Minimum hours between notifications (default: 0)
- `IGNORE_REGEX_JSON`: JSON array of regex patterns to filter out
- `SELECTOR_MAP_JSON`: JSON map of URL to CSS selector
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### URL Configuration

URLs can be configured as simple strings or objects with selectors:

```hcl
# Simple URLs
urls = [
  "https://example.com",
  "https://www.example.org"
]

# With selectors (requires JSON encoding)
# Use selector_map_json variable instead
```

### Advanced Configuration

#### Ignore Patterns

Filter out noisy content using regex patterns:

```hcl
ignore_regex_json = "[\"Last updated:.*\", \"Copyright \\\\d{4}\"]"
```

#### CSS Selectors

Scope extraction to specific page sections:

```hcl
selector_map_json = "{\"https://example.com\": \"#main-content\"}"
```

#### Notification Cooldown

Prevent notification spam:

```hcl
cooldown_hours = 6  # Wait 6 hours between notifications for same URL
```

## GitHub Actions CI/CD

### Required Secrets

Configure the following secrets in your GitHub repository:

- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `SES_FROM_ADDRESS`: Verified sender email
- `SES_TO_ADDRESS`: Recipient email
- `MONITOR_URLS`: JSON array of URLs to monitor
- `ALARM_EMAIL`: Email for CloudWatch alarms (optional)

### Workflows

1. **Test** (`test.yml`): Runs on all pushes and PRs
   - Runs Python unit tests
   - Performs linting with flake8
   - Generates coverage reports

2. **Terraform** (`terraform.yml`): Infrastructure management
   - Validates Terraform on all changes
   - Applies on push to main branch
   - Runs format checks

3. **Deploy Lambda** (`deploy-lambda.yml`): Lambda deployment
   - Builds deployment package
   - Updates Lambda function code
   - Updates configuration

## Testing

### Run Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests with coverage
pytest tests/ -v --cov=lambda --cov-report=term-missing
```

### Test Individual Components

```bash
# Test normalizer
python -m pytest tests/test_normalizer.py -v

# Test diff generator
python -m pytest tests/test_diff_generator.py -v

# Test Lambda handler
python -m pytest tests/test_app.py -v
```

## Operational Procedures

### Add a New URL

1. Update `terraform.tfvars`:
   ```hcl
   urls = [
     "https://example.com",
     "https://new-site.com"  # Add new URL
   ]
   ```

2. Apply changes:
   ```bash
   terraform apply
   ```

3. The URL will be checked on the next scheduled run

### Reduce False Positives

If a URL produces false positives due to dynamic content:

1. **Add ignore patterns**:
   ```hcl
   ignore_regex_json = "[\"Last updated:.*\", \"Session ID:.*\"]"
   ```

2. **Use CSS selectors**:
   ```hcl
   selector_map_json = "{\"https://noisy-site.com\": \"#main-content\"}"
   ```

3. Redeploy with `terraform apply`

### View Logs

```bash
# Recent logs
aws logs tail /aws/lambda/website-diff-checker-checker --follow

# Specific time range
aws logs tail /aws/lambda/website-diff-checker-checker \
  --since 1h \
  --format short
```

### Manually Trigger Check

```bash
aws lambda invoke \
  --function-name website-diff-checker-checker \
  output.json
```

### Inspect DynamoDB State

```bash
# List all URLs
aws dynamodb scan \
  --table-name website-diff-checker-state \
  --projection-expression "url,last_checked_at,last_hash"

# Get specific URL
aws dynamodb get-item \
  --table-name website-diff-checker-state \
  --key '{"url": {"S": "https://example.com"}}'
```

### Reset State for URL

To force a fresh check (will trigger notification on next run):

```bash
aws dynamodb delete-item \
  --table-name website-diff-checker-state \
  --key '{"url": {"S": "https://example.com"}}'
```

## Troubleshooting

### SES Sandbox Restrictions

If in SES sandbox mode:
- Both sender and recipient emails must be verified
- Request production access: AWS Console → SES → Account dashboard → Request production access

### 403/429 Responses

If receiving rate limit or forbidden errors:
- Adjust User-Agent string
- Reduce check frequency
- Add delays between URL checks (modify Lambda code)

### False Positives

If receiving too many notifications:
- Enable cooldown period
- Add ignore regex patterns
- Use CSS selectors to scope content
- Adjust normalization logic

### Lambda Timeouts

If Lambda times out:
- Increase timeout in `variables.tf`
- Check URL response times
- Consider reducing number of URLs per invocation

## Cost Estimation

Approximate monthly costs (us-east-1, 2 checks/day, 10 URLs):

- Lambda: ~$0.20 (60 invocations × 5s avg)
- DynamoDB: ~$0.00 (on-demand, minimal reads/writes)
- SES: ~$0.00 (first 62,000 emails free from EC2/Lambda)
- CloudWatch: ~$0.50 (logs)
- **Total: ~$1/month**

Costs scale primarily with:
- Number of URLs
- Check frequency
- URL response sizes
- Number of email notifications

## Security Considerations

- **IAM**: Least privilege policies for Lambda
- **SES**: Verify identities to prevent spoofing
- **Secrets**: Use AWS Secrets Manager for sensitive data
- **VPC**: Not required for this implementation (reduces cold starts)
- **Encryption**: DynamoDB encryption at rest enabled by default

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run tests: `pytest tests/ -v`
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check CloudWatch logs for errors
- Review DynamoDB state for inconsistencies

## Roadmap

- [ ] S3 storage for full page content history
- [ ] Multi-region deployment support
- [ ] Custom metrics and dashboards
- [ ] Slack/Teams notification support
- [ ] Web UI for configuration
- [ ] Screenshot diffing for visual changes
