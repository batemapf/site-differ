# Terraform backend configuration for remote state storage
# This ensures state persists between CI/CD runs and prevents idempotency issues

terraform {
  backend "s3" {
    bucket         = "website-diff-checker-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "website-diff-checker-terraform-locks"
  }
}
