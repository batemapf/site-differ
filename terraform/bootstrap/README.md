# Bootstrap Terraform Backend Resources

This directory contains the Terraform configuration to create the backend infrastructure (S3 bucket and DynamoDB table) needed for remote state storage.

## Purpose

The main Terraform configuration requires an S3 bucket and DynamoDB table for storing and locking state. These resources must be created first before the main configuration can use them.

## One-Time Setup

Run this configuration **once** before using the main Terraform configuration:

```bash
cd terraform/bootstrap
terraform init
terraform apply
```

This will create:
- S3 bucket: `website-diff-checker-terraform-state`
- DynamoDB table: `website-diff-checker-terraform-locks`

## After Bootstrap

After running the bootstrap configuration:

1. The backend resources are created
2. Go back to the main terraform directory: `cd ..`
3. Initialize the backend: `terraform init`
4. Terraform will now use remote state storage

## Cleanup

To destroy the backend resources (only do this if you're completely removing the project):

```bash
cd terraform/bootstrap
terraform destroy
```

**Warning:** This will delete the state bucket. Make sure you've destroyed all resources in the main configuration first.

## CI/CD Integration

The GitHub Actions workflow automatically handles backend initialization. No manual intervention is needed for CI/CD runs after the bootstrap is complete.
