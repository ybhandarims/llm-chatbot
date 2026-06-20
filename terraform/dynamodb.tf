resource "aws_dynamodb_table" "conversations" {
  name         = "conversations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "conversation_id"

  attribute {
    name = "conversation_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "messages" {
  name         = "messages"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "message_id"

  attribute {
    name = "message_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "settings" {
  name         = "settings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "setting_id"

  attribute {
    name = "setting_id"
    type = "S"
  }
}
