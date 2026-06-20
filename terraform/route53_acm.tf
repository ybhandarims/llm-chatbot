# Create or request an ACM certificate and validate via Route53 if `domain_name` and hosted zone exist

resource "aws_acm_certificate" "cert" {
  count       = length(var.domain_name) > 0 ? 1 : 0
  domain_name = var.domain_name
  validation_method = "DNS"
  lifecycle {
    create_before_destroy = true
  }
}

data "aws_route53_zone" "selected" {
  count = length(var.domain_name) > 0 ? 1 : 0
  name  = "${var.domain_name}."
}

resource "aws_route53_record" "cert_validation" {
  count = length(var.domain_name) > 0 ? 1 : 0

  zone_id = data.aws_route53_zone.selected[0].zone_id
  name    = aws_acm_certificate.cert[0].domain_validation_options[0].resource_record_name
  type    = aws_acm_certificate.cert[0].domain_validation_options[0].resource_record_type
  records = [aws_acm_certificate.cert[0].domain_validation_options[0].resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "cert_validation" {
  count = length(var.domain_name) > 0 ? 1 : 0

  certificate_arn         = aws_acm_certificate.cert[0].arn
  validation_record_fqdns = [aws_route53_record.cert_validation[0].fqdn]
}
