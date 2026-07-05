variable "engine" {}

resource "aws_db_instance" "inner" {
  engine            = var.engine
  storage_encrypted = true
}
