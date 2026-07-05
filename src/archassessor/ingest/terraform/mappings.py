"""Declarative Terraform resource -> node mapping table (spec 002 §5).

Each entry maps a Terraform resource type to a canonical node type and a set
of property extractors. Extractors receive the resource body and a `resolve`
callable that substitutes variables/locals (returning None for anything it
cannot determine — null means "undeterminable", spec 001 §3.1). Adding a
resource type is a one-entry change here, never a parser change.
"""

from __future__ import annotations

from collections.abc import Callable

Resolve = Callable[[object], object]
Body = dict[str, object]


def _attr(body: Body, name: str, resolve: Resolve) -> object:
    return resolve(body.get(name))


def _block(body: Body, name: str) -> Body | None:
    """First nested block of the given name, or None."""
    value = body.get(name)
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    if isinstance(value, dict):
        return value
    return None


def _bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _database_common(body: Body, resolve: Resolve) -> dict[str, object]:
    return {
        "engine": _attr(body, "engine", resolve),
        "encryption_at_rest": _bool_or_none(_attr(body, "storage_encrypted", resolve)),
        "publicly_accessible": _bool_or_none(_attr(body, "publicly_accessible", resolve)),
        "backup_retention_days": _attr(body, "backup_retention_period", resolve),
        "deletion_protection": _bool_or_none(_attr(body, "deletion_protection", resolve)),
    }


def _db_instance(body: Body, resolve: Resolve) -> dict[str, object]:
    props = _database_common(body, resolve)
    props["multi_az"] = _bool_or_none(_attr(body, "multi_az", resolve))
    return props


def _dynamodb(body: Body, resolve: Resolve) -> dict[str, object]:
    sse = _block(body, "server_side_encryption")
    if sse is None:
        encrypted: bool | None = True  # AWS default for DynamoDB (spec 002 §5.1)
    else:
        encrypted = _bool_or_none(resolve(sse.get("enabled")))
    return {"engine": "dynamodb", "encryption_at_rest": encrypted}


def _s3_bucket(body: Body, resolve: Resolve) -> dict[str, object]:
    versioning = _block(body, "versioning")  # legacy inline block only
    enabled = _bool_or_none(resolve(versioning.get("enabled"))) if versioning else None
    return {
        "encryption_at_rest": None,  # set by modifier resources (spec 002 §5.2)
        "public_access_blocked": None,
        "versioning_enabled": enabled,
        "logging_enabled": None,
    }


def _security_group(body: Body, resolve: Resolve) -> dict[str, object]:
    raw = body.get("ingress")
    blocks = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
    world_ports: set[str] = set()
    for block in blocks:
        if not isinstance(block, dict):
            continue
        cidrs = block.get("cidr_blocks") or []
        cidrs6 = block.get("ipv6_cidr_blocks") or []
        all_cidrs = [c for c in (list(cidrs) + list(cidrs6)) if isinstance(c, str)]
        if not any(c in {"0.0.0.0/0", "::/0"} for c in all_cidrs):
            continue
        from_port = resolve(block.get("from_port"))
        to_port = resolve(block.get("to_port"))
        if isinstance(from_port, int) and isinstance(to_port, int):
            world_ports.add(str(from_port) if from_port == to_port else f"{from_port}-{to_port}")
    return {
        "open_to_world": bool(world_ports),
        "open_to_world_ports": sorted(world_ports),
    }


def _load_balancer(body: Body, resolve: Resolve) -> dict[str, object]:
    internal = _bool_or_none(_attr(body, "internal", resolve))
    scheme: str | None = None
    if internal is not None:
        scheme = "internal" if internal else "internet-facing"
    return {"internal": internal, "scheme": scheme}


def _queue(body: Body, resolve: Resolve) -> dict[str, object]:
    sse = _attr(body, "sqs_managed_sse_enabled", resolve)
    kms = body.get("kms_master_key_id")
    encrypted: bool | None
    if sse is True or kms is not None:
        encrypted = True
    elif sse is False:
        encrypted = False
    else:
        encrypted = None
    return {"encryption_at_rest": encrypted}


def _topic(body: Body, resolve: Resolve) -> dict[str, object]:
    return {"encryption_at_rest": True if body.get("kms_master_key_id") is not None else None}


Extractor = Callable[[Body, Resolve], dict[str, object]]

RESOURCE_MAP: dict[str, tuple[str, Extractor | None]] = {
    "aws_instance": (
        "compute",
        lambda b, r: {
            "instance_type": _attr(b, "instance_type", r),
            "public_ip": _bool_or_none(_attr(b, "associate_public_ip_address", r)),
        },
    ),
    "aws_ecs_service": ("container_service", None),
    "aws_lambda_function": ("function", lambda b, r: {"runtime": _attr(b, "runtime", r)}),
    "aws_db_instance": ("database", _db_instance),
    "aws_rds_cluster": ("database", _database_common),
    "aws_dynamodb_table": ("database", _dynamodb),
    "aws_elasticache_cluster": ("cache", lambda b, r: {"engine": _attr(b, "engine", r)}),
    "aws_s3_bucket": ("storage", _s3_bucket),
    "aws_sqs_queue": ("queue", _queue),
    "aws_sns_topic": ("topic", _topic),
    "aws_vpc": ("network", None),
    "aws_subnet": ("subnet", None),
    "aws_security_group": ("security_group", _security_group),
    "aws_lb": ("load_balancer", _load_balancer),
    "aws_alb": ("load_balancer", _load_balancer),
    "aws_api_gateway_rest_api": ("api_gateway", None),
    "aws_route53_zone": ("dns_zone", None),
    "aws_cloudfront_distribution": ("cdn", None),
    "aws_secretsmanager_secret": ("secret_store", None),
    "aws_kms_key": (
        "kms_key",
        lambda b, r: {"rotation_enabled": _bool_or_none(_attr(b, "enable_key_rotation", r))},
    ),
    "aws_iam_role": ("iam_role", None),
}

# Resources that configure another resource instead of becoming nodes (spec 002 §5.2).
MODIFIER_TYPES: frozenset[str] = frozenset(
    {
        "aws_s3_bucket_server_side_encryption_configuration",
        "aws_s3_bucket_public_access_block",
        "aws_s3_bucket_versioning",
        "aws_s3_bucket_logging",
    }
)
