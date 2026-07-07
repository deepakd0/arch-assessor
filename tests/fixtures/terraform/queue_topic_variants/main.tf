resource "aws_sqs_queue" "sse_explicitly_false" {
  name                      = "sse-off"
  sqs_managed_sse_enabled   = false
}

resource "aws_sqs_queue" "no_sse_config" {
  name = "no-sse-config"
}

resource "aws_sqs_queue" "sse_managed" {
  name                    = "sse-managed"
  sqs_managed_sse_enabled = true
}

resource "aws_sns_topic" "no_kms_key" {
  name = "no-kms-key"
}
