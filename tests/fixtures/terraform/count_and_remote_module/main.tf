resource "aws_instance" "web" {
  count         = 3
  ami           = "ami-1234567890"
  instance_type = "t3.small"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
}

resource "aws_s3_bucket" "logged" {
  bucket = "logged-bucket"
}

resource "aws_s3_bucket_logging" "logged" {
  bucket = aws_s3_bucket.logged.id

  target_bucket = "log-bucket"
  target_prefix = "logs/"
}
