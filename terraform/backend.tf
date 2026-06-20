/*
Optional S3 backend configuration example with DynamoDB locking.

Notes:
- Backends cannot use Terraform variables. Either fill these values here (not recommended for shared repos),
  or run `terraform init -backend-config="bucket=..." -backend-config="key=..."`.
- Create an S3 bucket and a DynamoDB table for state locking before initializing.

Example usage:
  aws s3 mb s3://my-terraform-state-bucket --region us-east-1
  aws dynamodb create-table --table-name terraform-locks --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST

Then initialize with:
  terraform init -backend-config="bucket=my-terraform-state-bucket" -backend-config="key=llm-chatbot/terraform.tfstate" -backend-config="region=us-east-1" -backend-config="dynamodb_table=terraform-locks"

*/

terraform {
  backend "s3" {
    # Uncomment and set values here for a static backend, or use -backend-config when running `terraform init`.
    # bucket         = "my-terraform-state-bucket"
    # key            = "llm-chatbot/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "terraform-locks"
    # encrypt        = true
  }
}
