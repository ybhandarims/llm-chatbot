"""
Shared database configuration and utilities for microservices
"""
import boto3
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import os

logger = logging.getLogger(__name__)


class DynamoDBService:
    """Service for interacting with DynamoDB"""
    
    def __init__(self, table_name: str, region: str = "us-east-1"):
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def put_item(self, item: Dict[str, Any]) -> bool:
        """Store an item in DynamoDB"""
        try:
            if 'created_at' not in item:
                item['created_at'] = datetime.now(timezone.utc).isoformat()
            self.table.put_item(Item=item)
            logger.info(f"Item stored in {self.table_name}")
            return True
        except Exception as e:
            logger.error(f"Error storing item in {self.table_name}: {e}")
            return False
    
    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve an item from DynamoDB"""
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error retrieving item from {self.table_name}: {e}")
            return None
    
    def query(self, key_condition: str, expression_values: Dict[str, Any]) -> list:
        """Query items from DynamoDB"""
        try:
            response = self.table.query(
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=expression_values
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error querying {self.table_name}: {e}")
            return []
    
    def update_item(self, key: Dict[str, Any], updates: Dict[str, Any]) -> bool:
        """Update an item in DynamoDB"""
        try:
            update_expression = "SET " + ", ".join([f"{k}=:{k}" for k in updates.keys()])
            expression_values = {f":{k}": v for k, v in updates.items()}
            expression_values['updated_at'] = datetime.now(timezone.utc).isoformat()
            update_expression += ", updated_at=:updated_at"
            
            self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            logger.info(f"Item updated in {self.table_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating item in {self.table_name}: {e}")
            return False
    
    def delete_item(self, key: Dict[str, Any]) -> bool:
        """Delete an item from DynamoDB"""
        try:
            self.table.delete_item(Key=key)
            logger.info(f"Item deleted from {self.table_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting item from {self.table_name}: {e}")
            return False


class SQSService:
    """Service for interacting with SQS"""
    
    def __init__(self, queue_url: str, region: str = "us-east-1"):
        self.queue_url = queue_url
        self.region = region
        self.sqs = boto3.client('sqs', region_name=region)
    
    def send_message(self, message: Dict[str, Any], group_id: Optional[str] = None) -> Optional[str]:
        """Send a message to SQS queue"""
        try:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message),
                MessageGroupId=group_id or "default"
            )
            logger.info(f"Message sent to SQS: {response['MessageId']}")
            return response['MessageId']
        except Exception as e:
            logger.error(f"Error sending message to SQS: {e}")
            return None
    
    def receive_messages(self, max_messages: int = 1, wait_time: int = 20) -> list:
        """Receive messages from SQS queue"""
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time
            )
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from SQS")
            return messages
        except Exception as e:
            logger.error(f"Error receiving messages from SQS: {e}")
            return []
    
    def delete_message(self, receipt_handle: str) -> bool:
        """Delete a message from SQS queue"""
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info("Message deleted from SQS")
            return True
        except Exception as e:
            logger.error(f"Error deleting message from SQS: {e}")
            return False
    
    def send_to_dlq(self, message: Dict[str, Any], dlq_url: str) -> Optional[str]:
        """Send a message to Dead Letter Queue"""
        try:
            dlq_service = SQSService(dlq_url, self.region)
            return dlq_service.send_message(message)
        except Exception as e:
            logger.error(f"Error sending to DLQ: {e}")
            return None


def get_db_service(table_name: str) -> DynamoDBService:
    """Factory function to get DynamoDB service"""
    region = os.getenv('AWS_REGION', 'us-east-1')
    return DynamoDBService(table_name, region)


def get_sqs_service(queue_url: Optional[str] = None) -> SQSService:
    """Factory function to get SQS service"""
    if not queue_url:
        queue_url = os.getenv('SQS_QUEUE_URL', '')
    region = os.getenv('AWS_REGION', 'us-east-1')
    return SQSService(queue_url, region)
