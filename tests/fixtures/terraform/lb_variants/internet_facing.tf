resource "aws_lb" "explicit_internet_facing" {
  name     = "explicit-internet-facing"
  internal = false
}
