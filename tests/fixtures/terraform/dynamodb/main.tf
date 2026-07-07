resource "aws_dynamodb_table" "no_sse_block" {
  name = "no-sse-block"
}

resource "aws_dynamodb_table" "sse_enabled" {
  name = "sse-enabled"

  server_side_encryption {
    enabled = true
  }
}

resource "aws_dynamodb_table" "sse_disabled" {
  name = "sse-disabled"

  server_side_encryption {
    enabled = false
  }
}
