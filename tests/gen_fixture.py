"""Synthetic Terraform repo generator for benchmarking (spec 009 §5).

Produces a directory of .tf files with a realistic mix of resource types and
reference density (~2 edges/node): each compute instance sits in a subnet
which sits in a VPC, plus a handful of standalone storage/database/queue
resources. Usable as a script (`python gen_fixture.py DIR N`) or a library
(`generate(dir, n)`) from the benchmark tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

RESOURCES_PER_FILE = 200


def _vpc_block(vpc_id: int) -> str:
    return f'resource "aws_vpc" "v{vpc_id}" {{\n  cidr_block = "10.{vpc_id % 256}.0.0/16"\n}}\n'


def _subnet_block(vpc_id: int, subnet_id: int) -> str:
    return (
        f'resource "aws_subnet" "s{subnet_id}" {{\n'
        f"  vpc_id     = aws_vpc.v{vpc_id}.id\n"
        f'  cidr_block = "10.{vpc_id % 256}.{subnet_id % 256}.0/24"\n'
        f"}}\n"
    )


def _instance_block(subnet_id: int, instance_id: int) -> str:
    return (
        f'resource "aws_instance" "i{instance_id}" {{\n'
        f'  ami           = "ami-0000000000"\n'
        f'  instance_type = "t3.micro"\n'
        f"  subnet_id     = aws_subnet.s{subnet_id}.id\n"
        f'  tags = {{ owner = "platform", environment = "production" }}\n'
        f"}}\n"
    )


def _db_block(db_id: int) -> str:
    encrypted = "true" if db_id % 3 else "false"
    return (
        f'resource "aws_db_instance" "d{db_id}" {{\n'
        f'  engine                  = "postgres"\n'
        f"  storage_encrypted       = {encrypted}\n"
        f"  multi_az                = true\n"
        f"  backup_retention_period = 14\n"
        f'  tags = {{ owner = "platform", environment = "production" }}\n'
        f"}}\n"
    )


def _bucket_block(bucket_id: int) -> str:
    return (
        f'resource "aws_s3_bucket" "b{bucket_id}" {{\n'
        f'  bucket = "bucket-{bucket_id}"\n'
        f'  tags = {{ owner = "platform", environment = "production" }}\n'
        f"}}\n"
    )


def generate(root: Path, resource_count: int) -> None:
    """Write a synthetic Terraform repo with roughly `resource_count` resources.

    Distribution: 5% VPCs, 15% subnets, 40% instances (one edge to a subnet
    each), 15% databases, 15% buckets, plus the VPC/subnet edges themselves —
    giving the ~2 edges/node density spec 009 §5 calls for.
    """
    root.mkdir(parents=True, exist_ok=True)
    vpc_count = max(1, resource_count // 20)
    subnet_count = max(1, resource_count * 15 // 100)
    instance_count = max(1, resource_count * 40 // 100)
    db_count = max(1, resource_count * 15 // 100)
    bucket_count = max(1, resource_count - vpc_count - subnet_count - instance_count - db_count)

    blocks: list[str] = []
    for v in range(vpc_count):
        blocks.append(_vpc_block(v))
    for s in range(subnet_count):
        blocks.append(_subnet_block(s % vpc_count, s))
    for i in range(instance_count):
        blocks.append(_instance_block(i % subnet_count, i))
    for d in range(db_count):
        blocks.append(_db_block(d))
    for b in range(bucket_count):
        blocks.append(_bucket_block(b))

    for file_index in range(0, len(blocks), RESOURCES_PER_FILE):
        chunk = blocks[file_index : file_index + RESOURCES_PER_FILE]
        (root / f"generated_{file_index // RESOURCES_PER_FILE:04d}.tf").write_text(
            "\n".join(chunk), encoding="utf-8"
        )


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: gen_fixture.py DIR RESOURCE_COUNT", file=sys.stderr)
        raise SystemExit(2)
    generate(Path(sys.argv[1]), int(sys.argv[2]))


if __name__ == "__main__":
    main()
