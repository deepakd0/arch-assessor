resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "private" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
}

resource "aws_instance" "web" {
  ami           = "ami-1234567890"
  instance_type = "t3.small"
  subnet_id     = aws_subnet.private.id
}

resource "aws_db_instance" "main" {
  engine                  = "postgres"
  instance_class          = "db.t3.micro"
  storage_encrypted       = true
  multi_az                = false
  backup_retention_period = 14
}
