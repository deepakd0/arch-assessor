"""Spec 002 acceptance tests against the fixture repositories."""

from __future__ import annotations

from conftest import TF

from archassessor.graph.model import to_json
from archassessor.ingest.terraform.parser import parse_directory


def _node(result, node_id):
    node = result.graph.node_by_id(node_id)
    assert node is not None, f"{node_id} missing; have {[n.id for n in result.graph.nodes]}"
    return node


def _codes(result) -> list[str]:
    return [w.code for w in result.warnings]


def test_simple_fixture_nodes_and_edges() -> None:
    result = parse_directory(TF / "simple")
    assert len(result.graph.nodes) == 4

    db = _node(result, "tf:root:aws_db_instance.main")
    assert db.type == "database"
    assert db.properties["engine"] == "postgres"
    assert db.properties["encryption_at_rest"] is True
    assert db.properties["multi_az"] is False
    assert db.properties["backup_retention_days"] == 14
    assert db.properties["publicly_accessible"] is None  # absent -> undeterminable
    assert db.source.file == "main.tf"

    edge_ids = {e.id for e in result.graph.edges}
    assert "tf:root:aws_vpc.main--contains--tf:root:aws_subnet.private" in edge_ids
    assert "tf:root:aws_subnet.private--contains--tf:root:aws_instance.web" in edge_ids


def test_s3_modifiers_apply_and_emit_no_nodes() -> None:
    result = parse_directory(TF / "s3_modifiers")
    assert len(result.graph.nodes) == 1
    bucket = _node(result, "tf:root:aws_s3_bucket.assets")
    assert bucket.properties["encryption_at_rest"] is True
    assert bucket.properties["public_access_blocked"] is True
    assert bucket.properties["versioning_enabled"] is True


def test_variables_defaults_and_unresolved() -> None:
    result = parse_directory(TF / "variables")
    db = _node(result, "tf:root:aws_db_instance.primary")
    assert db.properties["engine"] == "postgres"  # var default substituted
    assert db.properties["encryption_at_rest"] is None  # no default -> null
    assert db.properties["backup_retention_days"] == 14  # literal local
    assert "W006" in _codes(result)


def test_open_security_group() -> None:
    result = parse_directory(TF / "open_sg")
    sg = _node(result, "tf:root:aws_security_group.web")
    assert sg.properties["open_to_world"] is True
    assert sg.properties["open_to_world_ports"] == ["22"]


def test_broken_file_degrades_gracefully() -> None:
    result = parse_directory(TF / "broken")
    assert _codes(result).count("W001") == 1
    assert result.graph.node_by_id("tf:root:aws_vpc.ok") is not None
    assert result.files_total == 2 and result.files_failed == 1
    bad = [w for w in result.warnings if w.code == "W001"][0]
    assert bad.file == "bad.tf"


def test_unmapped_resource_becomes_unknown() -> None:
    result = parse_directory(TF / "unmapped")
    node = _node(result, "tf:root:aws_wafv2_web_acl.edge")
    assert node.type == "unknown"
    assert "W004" in _codes(result)


def test_local_module_ids_and_call_args() -> None:
    result = parse_directory(TF / "local_module")
    inner = _node(result, "tf:root.net:aws_db_instance.inner")
    assert inner.properties["engine"] == "mysql"  # call-site literal reached the module
    assert inner.properties["encryption_at_rest"] is True


def test_parse_is_deterministic() -> None:
    first = to_json(parse_directory(TF / "simple").graph)
    second = to_json(parse_directory(TF / "simple").graph)
    assert first == second


def test_dynamodb_encryption_variants() -> None:
    result = parse_directory(TF / "dynamodb")
    # No server_side_encryption block -> AWS default is encrypted (spec 002 §5.1).
    assert (
        _node(result, "tf:root:aws_dynamodb_table.no_sse_block").properties["encryption_at_rest"]
        is True
    )
    assert (
        _node(result, "tf:root:aws_dynamodb_table.sse_enabled").properties["encryption_at_rest"]
        is True
    )
    assert (
        _node(result, "tf:root:aws_dynamodb_table.sse_disabled").properties["encryption_at_rest"]
        is False
    )


def test_load_balancer_without_internal_attribute_is_unknown() -> None:
    result = parse_directory(TF / "lb_variants")
    lb = _node(result, "tf:root:aws_lb.no_internal_attr")
    assert lb.properties["internal"] is None
    assert lb.properties["scheme"] is None


def test_load_balancer_explicit_internet_facing() -> None:
    result = parse_directory(TF / "lb_variants")
    lb = _node(result, "tf:root:aws_lb.explicit_internet_facing")
    assert lb.properties["internal"] is False
    assert lb.properties["scheme"] == "internet-facing"


def test_s3_block_form_versioning() -> None:
    result = parse_directory(TF / "lb_variants")
    bucket = _node(result, "tf:root:aws_s3_bucket.block_form_versioning")
    assert bucket.properties["versioning_enabled"] is True


def test_queue_and_topic_encryption_variants() -> None:
    result = parse_directory(TF / "queue_topic_variants")
    assert (
        _node(result, "tf:root:aws_sqs_queue.sse_explicitly_false").properties["encryption_at_rest"]
        is False
    )
    assert (
        _node(result, "tf:root:aws_sqs_queue.no_sse_config").properties["encryption_at_rest"]
        is None
    )
    assert (
        _node(result, "tf:root:aws_sqs_queue.sse_managed").properties["encryption_at_rest"] is True
    )
    assert (
        _node(result, "tf:root:aws_sns_topic.no_kms_key").properties["encryption_at_rest"] is None
    )


def test_count_not_expanded_warns_w005() -> None:
    result = parse_directory(TF / "count_and_remote_module")
    node = _node(result, "tf:root:aws_instance.web")
    assert node.properties["instance_type"] == "t3.small"  # modeled as one node, not 3
    w005 = [w for w in result.warnings if w.code == "W005"]
    assert len(w005) == 1
    assert "count" in w005[0].message


def test_remote_module_skipped_warns_w003() -> None:
    result = parse_directory(TF / "count_and_remote_module")
    w003 = [w for w in result.warnings if w.code == "W003"]
    assert len(w003) == 1
    assert "remote source" in w003[0].message
    # No nodes from the remote module leaked into the graph.
    assert all(not n.id.startswith("tf:root.vpc:") for n in result.graph.nodes)


def test_s3_bucket_logging_modifier() -> None:
    result = parse_directory(TF / "count_and_remote_module")
    bucket = _node(result, "tf:root:aws_s3_bucket.logged")
    assert bucket.properties["logging_enabled"] is True


def test_duplicate_resource_address_keeps_first_occurrence() -> None:
    result = parse_directory(TF / "parser_edge_cases")
    dup_nodes = [n for n in result.graph.nodes if n.id == "tf:root:aws_vpc.dup"]
    assert len(dup_nodes) == 1
    assert dup_nodes[0].properties.get("region") is None  # first declaration wins


def test_self_referencing_resource_creates_no_self_loop() -> None:
    result = parse_directory(TF / "parser_edge_cases")
    self_ref_edges = [
        e
        for e in result.graph.edges
        if e.from_id == "tf:root:aws_instance.self_ref"
        or e.to_id == "tf:root:aws_instance.self_ref"
    ]
    assert self_ref_edges == []


def test_edge_reference_to_undeclared_resource_warns_w002() -> None:
    result = parse_directory(TF / "parser_edge_cases")
    w002_messages = [w.message for w in result.warnings if w.code == "W002"]
    assert any("aws_iam_role.never_declared" in m for m in w002_messages)
    assert any("aws_ssm_parameter.engine_name" in m for m in w002_messages)


def test_modifier_referencing_undeclared_bucket_warns_w002() -> None:
    result = parse_directory(TF / "parser_edge_cases")
    w002_messages = [w.message for w in result.warnings if w.code == "W002"]
    assert any("modifier dropped" in m for m in w002_messages)


def test_missing_local_module_source_warns_w003() -> None:
    result = parse_directory(TF / "parser_edge_cases")
    w003 = [w for w in result.warnings if w.code == "W003"]
    assert any("not found in repo" in w.message for w in w003)


def test_load_balancer_routes_to_compute() -> None:
    result = parse_directory(TF / "parser_edge_cases")
    edge_ids = {e.id for e in result.graph.edges}
    assert "tf:root:aws_lb.front--routes_to--tf:root:aws_instance.backend" in edge_ids


def test_cross_resource_property_reference_is_unresolved() -> None:
    result = parse_directory(TF / "parser_edge_cases")
    node = _node(result, "tf:root:aws_db_instance.cross_ref_property")
    assert node.properties["engine"] is None
    assert any(w.code == "W006" and "aws_ssm_parameter" in w.message for w in result.warnings)


def test_security_group_edge_cases() -> None:
    result = parse_directory(TF / "sg_edge_cases")
    no_ingress = _node(result, "tf:root:aws_security_group.no_ingress")
    assert no_ingress.properties["open_to_world"] is False
    assert no_ingress.properties["open_to_world_ports"] == []

    private_only = _node(result, "tf:root:aws_security_group.private_only")
    assert private_only.properties["open_to_world"] is False
