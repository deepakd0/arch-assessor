"""Terraform directory -> architecture graph (spec 002).

Offline by construction: no terraform binary, no credentials, no network.
Module semantics follow Terraform: the given directory is the root module and
local `module` calls are followed (depth-capped); directories not referenced
by a module call are not scanned, since Terraform would not read them either.

Never raises on malformed user input — problems become coded warnings and the
rest of the repository is still assessed (NFR-R2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import hcl2

from archassessor import __version__
from archassessor.graph.model import Edge, Graph, Node, SourceRef
from archassessor.ingest.terraform.mappings import MODIFIER_TYPES, RESOURCE_MAP

MAX_FILE_BYTES = 5 * 1024 * 1024  # threat T1 (spec 008)
MAX_MODULE_DEPTH = 5

_REFERENCE = re.compile(r"\$\{([a-z0-9_]+)\.([a-zA-Z0-9_-]+)")
_VAR_ONLY = re.compile(r"^\$\{var\.([a-zA-Z0-9_-]+)\}$")
_LOCAL_ONLY = re.compile(r"^\$\{local\.([a-zA-Z0-9_-]+)\}$")
_NON_RESOURCE_ROOTS = frozenset(
    {"var", "local", "data", "module", "each", "count", "path", "terraform"}
)


def _unquote(label: object) -> str:
    """python-hcl2 keeps the quotes on block labels ('"aws_vpc"'); strip them."""
    text = str(label)
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _normalize(value: object) -> object:
    """Normalize raw python-hcl2 8.x output.

    hcl2 keeps string literals quoted ('"postgres"') and adds __is_block__
    markers inside every block; strip both so the rest of the parser sees
    plain values. Interpolations (${...}) pass through untouched.
    """
    if isinstance(value, dict):
        return {_unquote(k): _normalize(v) for k, v in value.items() if k != "__is_block__"}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        return _unquote(value)
    return value


@dataclass
class Warning_:
    code: str
    message: str
    file: str | None = None
    line: int | None = None


@dataclass
class ParseResult:
    graph: Graph
    warnings: list[Warning_]
    files_total: int = 0
    files_failed: int = 0


@dataclass
class _RawResource:
    node_id: str
    rtype: str
    body: dict[str, object]
    module_path: str
    file: str


class _Parser:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.warnings: list[Warning_] = []
        self.resources: list[_RawResource] = []
        self.modifiers: list[_RawResource] = []
        self.files_total = 0
        self.files_failed = 0

    def warn(self, code: str, message: str, file: str | None = None) -> None:
        self.warnings.append(Warning_(code=code, message=message, file=file))

    # -- file handling -----------------------------------------------------

    def _tf_files(self, directory: Path) -> list[Path]:
        files: list[Path] = []
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            return []
        for entry in entries:
            if not entry.name.endswith(".tf") or not entry.is_file():
                continue
            rel = self._rel(entry)
            if entry.is_symlink() and not entry.resolve().is_relative_to(self.root):
                self.warn("W008", "symlink points outside the scanned directory; skipped", rel)
                continue
            try:
                if entry.stat().st_size > MAX_FILE_BYTES:
                    self.warn("W007", "file larger than 5 MB; skipped", rel)
                    continue
            except OSError:
                continue
            files.append(entry)
        return files

    def _rel(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.root))
        except ValueError:
            return str(path)

    def _load(self, file: Path) -> dict[str, object] | None:
        self.files_total += 1
        rel = self._rel(file)
        try:
            text = file.read_text(encoding="utf-8", errors="replace")
            parsed = hcl2.loads(text)
        except Exception as exc:  # hcl2 raises lark errors; treat all as user input
            self.files_failed += 1
            first_line = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
            self.warn("W001", f"file could not be parsed as HCL: {first_line}", rel)
            return None
        normalized = _normalize(parsed)
        return normalized if isinstance(normalized, dict) else None

    # -- value resolution ---------------------------------------------------

    def _make_resolver(self, env: dict[str, object], undefined: set[str], file: str) -> _Resolver:
        return _Resolver(self, env, undefined, file)

    # -- module parsing -----------------------------------------------------

    def parse_module(
        self, directory: Path, module_path: str, call_args: dict[str, object], depth: int
    ) -> None:
        documents: list[tuple[str, dict[str, object]]] = []
        for file in self._tf_files(directory):
            data = self._load(file)
            if data is not None:
                documents.append((self._rel(file), data))

        # Pass A: variables and locals for this module.
        env: dict[str, object] = {}
        declared: set[str] = set()
        for _, data in documents:
            for block in data.get("variable", []) or []:
                if isinstance(block, dict):
                    for raw_name, body in block.items():
                        name = _unquote(raw_name)
                        declared.add(name)
                        if isinstance(body, dict) and "default" in body:
                            default = body["default"]
                            if not (isinstance(default, str) and "${" in default):
                                env[f"var.{name}"] = default
            for block in data.get("locals", []) or []:
                if isinstance(block, dict):
                    for name, value in block.items():
                        if not (isinstance(value, str) and "${" in value):
                            env[f"local.{name}"] = value
        for name, value in call_args.items():
            env[f"var.{name}"] = value
        undefined = {f"var.{n}" for n in declared} - set(env)

        # Pass B: resources.
        for rel, data in documents:
            resolver = self._make_resolver(env, undefined, rel)
            for block in data.get("resource", []) or []:
                if not isinstance(block, dict):
                    continue
                for rtype, instances in block.items():
                    if not isinstance(instances, dict):
                        continue
                    for rname, body in instances.items():
                        if not isinstance(body, dict):
                            continue
                        self._add_resource(
                            _unquote(rtype), _unquote(rname), body, module_path, rel, resolver
                        )

        # Pass C: module calls.
        for rel, data in documents:
            resolver = self._make_resolver(env, undefined, rel)
            for block in data.get("module", []) or []:
                if not isinstance(block, dict):
                    continue
                for name, body in sorted(block.items()):
                    if not isinstance(body, dict):
                        continue
                    self._call_module(
                        _unquote(name), body, directory, module_path, rel, depth, resolver
                    )

    def _call_module(
        self,
        name: str,
        body: dict[str, object],
        directory: Path,
        module_path: str,
        file: str,
        depth: int,
        resolver: _Resolver,
    ) -> None:
        source = body.get("source")
        if not isinstance(source, str) or not source.startswith(("./", "../")):
            self.warn("W003", f"module {name!r} has a remote source; skipped", file)
            return
        if depth >= MAX_MODULE_DEPTH:
            self.warn("W003", f"module {name!r} exceeds depth {MAX_MODULE_DEPTH}; skipped", file)
            return
        child = (directory / source).resolve()
        if not child.is_dir() or not child.is_relative_to(self.root):
            self.warn("W003", f"module {name!r} source {source!r} not found in repo; skipped", file)
            return
        args = {
            key: resolver.resolve_silently(value) for key, value in body.items() if key != "source"
        }
        args = {k: v for k, v in args.items() if v is not None}
        self.parse_module(child, f"{module_path}.{name}", args, depth + 1)

    # -- resources ----------------------------------------------------------

    def _add_resource(
        self,
        rtype: str,
        rname: str,
        body: dict[str, object],
        module_path: str,
        file: str,
        resolver: _Resolver,
    ) -> None:
        node_id = f"tf:{module_path}:{rtype}.{rname}"
        raw = _RawResource(
            node_id=node_id, rtype=rtype, body=body, module_path=module_path, file=file
        )

        if rtype in MODIFIER_TYPES:
            self.modifiers.append(raw)
            return

        mapping = RESOURCE_MAP.get(rtype)
        if mapping is None:
            self.warn("W004", f"resource type {rtype!r} is not mapped; emitted as 'unknown'", file)
            node_type, props = "unknown", {}
        else:
            node_type, extractor = mapping
            props = dict(extractor(body, resolver.resolve)) if extractor else {}

        tags_raw = body.get("tags")
        tags = sorted(f"{k}={v}" for k, v in tags_raw.items()) if isinstance(tags_raw, dict) else []
        props["tags"] = tags
        props.setdefault("region", None)

        if node_id in self.nodes:
            return  # duplicate resource address: keep the first occurrence
        self.nodes[node_id] = Node(
            id=node_id,
            type=node_type,
            name=rname,
            properties=props,
            source=SourceRef(ingestor="terraform", file=file),
        )
        self.resources.append(raw)

        count_keys = {"count", "for_each"} & set(body)
        if count_keys:
            self.warn(
                "W005",
                f"{node_id}: {'/'.join(sorted(count_keys))} not expanded; modeled as one node",
                file,
            )

    # -- pass 2: modifiers ----------------------------------------------------

    def apply_modifiers(self) -> None:
        for raw in self.modifiers:
            target = self._referenced_bucket(raw)
            if target is None:
                self.warn(
                    "W002",
                    f"{raw.rtype} references a bucket that is not in the graph; modifier dropped",
                    raw.file,
                )
                continue
            props = target.properties
            if raw.rtype == "aws_s3_bucket_server_side_encryption_configuration":
                props["encryption_at_rest"] = True
            elif raw.rtype == "aws_s3_bucket_public_access_block":
                flags = [
                    raw.body.get("block_public_acls"),
                    raw.body.get("block_public_policy"),
                    raw.body.get("ignore_public_acls"),
                    raw.body.get("restrict_public_buckets"),
                ]
                props["public_access_blocked"] = all(f is True for f in flags)
            elif raw.rtype == "aws_s3_bucket_versioning":
                block = raw.body.get("versioning_configuration")
                cfg = block[0] if isinstance(block, list) and block else block
                status = cfg.get("status") if isinstance(cfg, dict) else None
                props["versioning_enabled"] = status == "Enabled"
            elif raw.rtype == "aws_s3_bucket_logging":
                props["logging_enabled"] = True

    def _referenced_bucket(self, raw: _RawResource) -> Node | None:
        value = raw.body.get("bucket")
        if isinstance(value, str):
            match = _REFERENCE.search(value)
            if match and match.group(1) == "aws_s3_bucket":
                return self.nodes.get(f"tf:{raw.module_path}:aws_s3_bucket.{match.group(2)}")
        return None

    # -- pass 3: edges ---------------------------------------------------------

    def extract_edges(self) -> None:
        for raw in self.resources:
            node = self.nodes[raw.node_id]
            for key, value in _walk_strings(raw.body):
                for match in _REFERENCE.finditer(value):
                    ref_type, ref_name = match.group(1), match.group(2)
                    if ref_type in _NON_RESOURCE_ROOTS:
                        continue
                    target_id = f"tf:{raw.module_path}:{ref_type}.{ref_name}"
                    target = self.nodes.get(target_id)
                    if target is None:
                        if ref_type in RESOURCE_MAP or ref_type.startswith("aws_"):
                            self.warn(
                                "W002",
                                f"{raw.node_id} references {ref_type}.{ref_name}, "
                                "which is not in the graph",
                                raw.file,
                            )
                        continue
                    if target_id == raw.node_id:
                        continue
                    self.edges.append(_edge_for(key, node, target))

    def result(self) -> ParseResult:
        graph = Graph(
            metadata={
                "ingestor": "terraform",
                "ingestor_version": __version__,
                "source_root": self.root.name,
            },
            nodes=sorted(self.nodes.values(), key=lambda n: n.id),
            edges=sorted(self.edges, key=lambda e: e.id),
        )
        self.warnings.sort(key=lambda w: (w.file or "", w.line or 0, w.code, w.message))
        return ParseResult(
            graph=graph,
            warnings=self.warnings,
            files_total=self.files_total,
            files_failed=self.files_failed,
        )


class _Resolver:
    """Substitutes ${var.x} / ${local.x}; anything else unresolvable -> None + W006."""

    def __init__(
        self, parser: _Parser, env: dict[str, object], undefined: set[str], file: str
    ) -> None:
        self.parser = parser
        self.env = env
        self.undefined = undefined
        self.file = file

    def resolve(self, value: object) -> object:
        resolved, ok = self._try(value)
        if not ok:
            self.parser.warn("W006", f"expression {value!r} could not be resolved", self.file)
        return resolved

    def resolve_silently(self, value: object) -> object:
        resolved, _ = self._try(value)
        return resolved

    def _try(self, value: object) -> tuple[object, bool]:
        if not isinstance(value, str):
            return value, True
        for pattern, prefix in ((_VAR_ONLY, "var"), (_LOCAL_ONLY, "local")):
            match = pattern.match(value)
            if match:
                key = f"{prefix}.{match.group(1)}"
                if key in self.env:
                    return self.env[key], True
                return None, False
        if "${" in value:
            return None, False
        return value, True


def _walk_strings(value: object, key: str = "") -> list[tuple[str, str]]:
    """Yield (nearest_key, string) pairs for every string in a nested body."""
    found: list[tuple[str, str]] = []
    if isinstance(value, str):
        found.append((key, value))
    elif isinstance(value, dict):
        for k in sorted(value):
            found.extend(_walk_strings(value[k], str(k)))
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_strings(item, key))
    return found


def _edge_for(key: str, node: Node, target: Node) -> Edge:
    if key.endswith(("subnet_id", "subnet_ids")) and target.type == "subnet":
        return Edge(from_id=target.id, to_id=node.id, type="contains")
    if key.endswith("vpc_id") and target.type == "network":
        return Edge(from_id=target.id, to_id=node.id, type="contains")
    if node.type in {"load_balancer", "api_gateway"} and target.type in {
        "compute",
        "container_service",
        "function",
    }:
        return Edge(from_id=node.id, to_id=target.id, type="routes_to")
    return Edge(from_id=node.id, to_id=target.id, type="depends_on")


def parse_directory(root: Path) -> ParseResult:
    """Parse the Terraform root module at `root` (plus local module calls).

    Never raises on malformed user input: syntax errors, oversized files, and
    unresolvable pieces become coded warnings (W001–W008) on the result.
    """
    parser = _Parser(root)
    parser.parse_module(root.resolve(), "root", {}, depth=0)
    parser.apply_modifiers()
    parser.extract_edges()
    return parser.result()
