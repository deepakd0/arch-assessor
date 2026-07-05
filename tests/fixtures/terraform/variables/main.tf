variable "engine" {
  default = "postgres"
}

variable "no_default" {}

locals {
  retention = 14
}

resource "aws_db_instance" "primary" {
  engine                  = var.engine
  storage_encrypted       = var.no_default
  backup_retention_period = local.retention
}
