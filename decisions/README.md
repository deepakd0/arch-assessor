# Architecture Decision Records

One file per significant decision, numbered, never deleted. A superseded ADR stays in place
with its status changed and a pointer to the replacement — the history *is* the value.

Format (Michael Nygard style, trimmed): **Status** (proposed / accepted / superseded by
NNNN), **Context** (the forces at play), **Decision**, **Consequences** (good and bad —
an ADR with no downsides listed wasn't thought through).

When to write one: any choice a future contributor might reasonably re-litigate — new runtime
dependency (NFR-M3 makes this mandatory), data-format change, stable-contract change
(spec 010), or rejecting an "obvious" tool.

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | accepted |
| [0002](0002-offline-hcl-parsing-with-python-hcl2.md) | Parse HCL offline with python-hcl2; no terraform binary | accepted |
| [0003](0003-declarative-yaml-rules-not-code.md) | Rules are declarative YAML, not code plugins or OPA/Rego | accepted |
| [0004](0004-three-valued-verdict-logic.md) | Three-valued verdict logic (pass/fail/unknown) | accepted |
| [0005](0005-stdlib-cli-and-rendering.md) | argparse + hand-rolled rendering; no click/typer/Jinja2 | accepted |
| [0006](0006-byte-deterministic-output.md) | Byte-determinism as a product guarantee | accepted |
| [0007](0007-license-and-open-core.md) | Apache-2.0 + open-core boundary at hosted services | **proposed** |
| [0008](0008-ingest-sarif-not-build-scanners.md) | Ingest scanner output (SARIF); never build scanners | accepted |
