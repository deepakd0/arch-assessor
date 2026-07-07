# Duplicate resource address: the second declaration is ignored (first wins).
resource "aws_vpc" "dup" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_vpc" "dup" {
  cidr_block = "10.1.0.0/16"
}

# Self-referencing edge: must not create a self-loop.
resource "aws_instance" "self_ref" {
  ami           = "ami-0000000000"
  instance_type = "t3.micro"
  subnet_id     = aws_instance.self_ref.id
}

# Reference to a resource type/name that was never declared (W002 on edges).
resource "aws_lambda_function" "orphan_ref" {
  runtime  = "python3.13"
  role     = aws_iam_role.never_declared.arn
}

# Module source that does not exist on disk.
module "missing" {
  source = "./modules/does_not_exist"
}

# Load balancer routing to compute -> routes_to edge. (The reference attribute
# below is synthetic for this fixture; it only needs to be a string containing
# the target's address, exercising _edge_for's routes_to branch.)
resource "aws_instance" "backend" {
  ami           = "ami-0000000001"
  instance_type = "t3.micro"
}

resource "aws_lb" "front" {
  name       = "front"
  depends_on = [aws_instance.backend]
}

# S3 modifier referencing a bucket that was never declared (W002 on modifiers).
resource "aws_s3_bucket_versioning" "orphan_modifier" {
  bucket = aws_s3_bucket.never_declared.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Property resolving to a non-var/non-local interpolation (unresolved -> W006).
resource "aws_db_instance" "cross_ref_property" {
  engine = aws_ssm_parameter.engine_name.value
}
