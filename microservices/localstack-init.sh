#!/bin/bash

echo "Initializing LocalStack resources..."

# Create SQS Queues
awslocal sqs create-queue --queue-name ai-jobs --region us-east-1
awslocal sqs create-queue --queue-name ai-jobs-dlq --region us-east-1

# Create DynamoDB Tables
echo "Creating DynamoDB tables..."

# Conversations Table
awslocal dynamodb create-table \
  --table-name conversations \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=conversation_id,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=conversation_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Messages Table
awslocal dynamodb create-table \
  --table-name messages \
  --attribute-definitions \
    AttributeName=conversation_id,AttributeType=S \
    AttributeName=message_id,AttributeType=S \
  --key-schema \
    AttributeName=conversation_id,KeyType=HASH \
    AttributeName=message_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Settings Table
awslocal dynamodb create-table \
  --table-name settings \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=setting_key,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=setting_key,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

echo "LocalStack initialization complete!"
