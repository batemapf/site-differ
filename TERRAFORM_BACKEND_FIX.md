# Terraform Backend Configuration Fix

## Problem

The Terraform configuration was experiencing idempotency issues where resources that already existed in AWS were being attempted to be created again during subsequent `terraform apply` runs. This was occurring because:

1. Terraform state was stored locally and not committed to version control (correctly, for security)
2. Each GitHub Actions workflow run started with a fresh state file
3. Without state, Terraform didn't know which resources already existed in AWS

Error messages included:
- `ResourceInUseException: Table already exists: website-diff-checker-state`
- `ResourceAlreadyExistsException: The specified log group already exists`
- `EntityAlreadyExists: Role with name website-diff-checker-lambda-role already exists`

## Solution

Added remote state storage using AWS S3 and DynamoDB:

### 1. Backend Configuration (`terraform/backend.tf`)
- Configures S3 bucket for state storage
- Configures DynamoDB table for state locking
- Enables encryption for security

### 2. Bootstrap Resources (`terraform/bootstrap/`)
- Separate Terraform configuration to create backend infrastructure
- Creates S3 bucket with versioning and encryption
- Creates DynamoDB table for state locking
- Runs once before main Terraform configuration

### 3. GitHub Actions Integration
- Workflow automatically checks if backend resources exist
- Creates them if needed on first run
- Uses remote state on all subsequent runs
- Ensures idempotency across workflow executions

## Benefits

1. **Idempotency**: Terraform correctly tracks existing resources
2. **State Persistence**: State survives between workflow runs
3. **State Locking**: Prevents concurrent modifications
4. **State History**: S3 versioning provides state history
5. **Security**: State is encrypted at rest

## Usage

### First-Time Setup (Manual)
```bash
cd terraform/bootstrap
terraform init
terraform apply
cd ..
terraform init
```

### CI/CD
GitHub Actions automatically handles backend initialization - no manual intervention needed.

## Files Changed

- `terraform/backend.tf` - Backend configuration
- `terraform/bootstrap/main.tf` - Bootstrap infrastructure
- `terraform/bootstrap/README.md` - Bootstrap documentation
- `.github/workflows/terraform.yml` - Automated backend setup
- `DEPLOYMENT.md` - Updated documentation
- `.gitignore` - Exclude .terraform directories
