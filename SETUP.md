# Setup Guide

This guide will walk you through setting up your AWS environment and deploying the Wikipedia Views Data Extraction pipeline.

## Prerequisites

- AWS root account created
- Personal IAM user created
- AWS CLI installed and configured with your IAM user credentials
- Terraform installed (v1.0+)
- Git repository cloned locally
- pip is installed

## Step 1: Configure IAM Groups and Permissions

### 1.1 Create the 'admins' IAM Group

Create an IAM group for administrators with full AWS access:

```bash
aws iam create-group --group-name admins
```

Attach the AdministratorAccess policy to the admins group:

```bash
aws iam attach-group-policy \
  --group-name admins \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

### 1.2 Create the 'data_engineers' IAM Group

Create an IAM group for data engineers:

```bash
aws iam create-group --group-name data_engineers
```

Attach the required policies to the data_engineers group:

```bash
aws iam attach-group-policy \
  --group-name data_engineers \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-group-policy \
  --group-name data_engineers \
  --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess

aws iam attach-group-policy \
  --group-name data_engineers \
  --policy-arn arn:aws:iam::aws:policy/AmazonEventBridgeFullAccess
```

### 1.3 Add Your User to Both Groups

Replace `YOUR_USERNAME` with your actual IAM username:

```bash
aws iam add-user-to-group --user-name YOUR_USERNAME --group-name admins
aws iam add-user-to-group --user-name YOUR_USERNAME --group-name data_engineers
```

### 1.4 Verify Group Membership

Confirm your user has been added to both groups:

```bash
aws iam list-groups-for-user --user-name YOUR_USERNAME
```

## Step 2: Configure Terraform

### 2.1 Edit Region Configuration

Open the `variables.tf` file in `terraform/` and update the `region` variable to your desired AWS region:

```hcl
variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"  # Change this to your desired region
}
```

Common AWS regions:
- `us-east-1` (N. Virginia)
- `us-west-2` (Oregon)
- `eu-west-1` (Ireland)
- `ap-southeast-1` (Singapore)

### 2.1 Edit API request header

In `terraform/variables.tf` replace `YOUR_ACCOUNT` in the `user_agent_string` variable with your GitHub account name:

```hcl
variable "user_agent_string" {
  description = "The User-Agent header used in API requests"
  default = "Page views analysis (https://github.com/YOUR_ACCOUNT)"
  type = string
}
```
This ensures the wikimedia API admins can contact you if there are issues with your API requests.

## Step 3: Configure Lambda Dependencies

## 3.1 Install Dependencies for Lambda Main
Run the following command so the `requests` package and its dependencies can be zipped with the lambda code and deployed on AWS.

```bash
python3 -m pip install requests -t api_to_s3/lambda/
```

## Step 4: Deploy Infrastructure with Terraform

### 4.1 Initialize Terraform

Navigate to your project directory and initialize Terraform:

```bash
terraform init
```

### 4.2 Review the Deployment Plan

Generate and review the execution plan:

```bash
terraform plan
```

Review the output to ensure the resources being created match your expectations.

### 4.3 Apply the Configuration

Deploy the infrastructure:

```bash
terraform apply
```

Type `yes` when prompted to confirm the deployment.

## Step 5: Verify Deployment

After the Terraform apply completes successfully, verify that your resources have been created:

- Two lambda functions
- S3 bucket
- EventBridge rule (for daily runs)
- Step Functions state machine (for backfills)
- Associated IAM roles and policies

You can check these in the AWS Console or using AWS CLI commands.

## Next Steps

- Test the Lambda function manually through the AWS Console
- Trigger a backfill using the Step Functions state machine
- Monitor the daily scheduled runs
- Check S3 for extracted data

## Troubleshooting

If you encounter permission errors:
- Verify your IAM user is in both groups: `aws iam list-groups-for-user --user-name YOUR_USERNAME`
- Ensure your AWS CLI credentials are up to date
- You may need to log out and log back in for group permissions to take effect

If Terraform fails:
- Check that your AWS credentials have sufficient permissions
- Verify the region is valid and available for your account
- Review the Terraform error messages for specific resource issues