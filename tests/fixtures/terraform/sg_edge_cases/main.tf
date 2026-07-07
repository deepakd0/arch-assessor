resource "aws_security_group" "no_ingress" {
  name = "no-ingress"
}

resource "aws_security_group" "private_only" {
  name = "private-only"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }
}
