resource "aws_lb" "no_internal_attr" {
  name = "no-internal-attr"
}

resource "aws_s3_bucket" "block_form_versioning" {
  bucket = "block-form-versioning"

  versioning {
    enabled = true
  }
}
