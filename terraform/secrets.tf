resource "aws_secretsmanager_secret" "app_secrets" {
  for_each = toset(var.secrets)

  name        = "${var.project_name}/${each.value}"
  description = "Secret for ${each.value}"
  tags        = var.tags
}

# We do not create secret versions here to avoid storing values in code.
