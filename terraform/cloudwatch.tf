resource "aws_cloudwatch_log_group" "services" {
  for_each = toset(var.log_groups)

  name              = "/llm-chatbot/${each.value}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}
