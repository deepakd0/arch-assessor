"""archscan: parse -> evaluate -> report, with a stable CI exit-code contract.

Exit codes (spec 006 §4 — stable forever):
  0 ran; no fail findings at/above --fail-on
  1 ran; threshold breached
  2 usage error (bad flags, missing path, no rules, unwritable output)
  3 input error (invalid rule files, or every .tf file unparseable)

Report bytes go to stdout (or --output); diagnostics go to stderr. Never mixed.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from archassessor import __version__
from archassessor.engine.evaluate import evaluate
from archassessor.graph.model import to_json
from archassessor.ingest.terraform.parser import ParseResult, parse_directory
from archassessor.report import render_html, render_json, render_markdown
from archassessor.rules.loader import RuleLoadError, load_builtin_pack, load_rules
from archassessor.rules.schema import FRAMEWORK_KEYS, Rule

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_INPUT = 3

_FAIL_ON_LEVELS = {
    "critical": {"critical"},
    "high": {"critical", "high"},
    "medium": {"critical", "high", "medium"},
    "low": {"critical", "high", "medium", "low"},
    "any": {"critical", "high", "medium", "low", "info"},
    "never": set(),
}


class _UsageError(Exception):
    pass


class _InputError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="archscan",
        description="Deterministic architecture assessment for Terraform repositories.",
    )
    parser.add_argument("--version", action="version", version=f"archscan {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser(
        "scan",
        help="assess a Terraform directory",
        epilog="example: archscan scan infra/ --format md --fail-on high",
    )
    scan.add_argument("path", type=Path, help="Terraform root module directory")
    scan.add_argument("--format", choices=["md", "html", "json"], default="md")
    scan.add_argument("--output", "-o", type=Path, default=None)
    scan.add_argument("--rules", type=Path, action="append", default=[])
    scan.add_argument("--no-builtin", action="store_true")
    scan.add_argument("--framework", action="append", default=[], choices=sorted(FRAMEWORK_KEYS))
    scan.add_argument("--fail-on", choices=sorted(_FAIL_ON_LEVELS), default="high")
    scan.add_argument("--include-passes", action="store_true")
    scan.add_argument("--timestamp", action="store_true")
    scan.add_argument("--quiet", "-q", action="store_true")

    graph = sub.add_parser(
        "graph",
        help="print the parsed architecture graph as canonical JSON",
        epilog="example: archscan graph infra/ -o graph.json",
    )
    graph.add_argument("path", type=Path)
    graph.add_argument("--output", "-o", type=Path, default=None)
    graph.add_argument("--quiet", "-q", action="store_true")

    rules = sub.add_parser(
        "rules",
        help="list and validate loaded rules",
        epilog="example: archscan rules list --rules ./my-pack",
    )
    rules_sub = rules.add_subparsers(dest="rules_command", required=True)
    rules_list = rules_sub.add_parser("list", help="list rules")
    rules_list.add_argument("--rules", type=Path, action="append", default=[])
    rules_list.add_argument("--no-builtin", action="store_true")
    rules_list.add_argument("--format", choices=["table", "json"], default="table")
    return parser


def _load_all_rules(extra: list[Path], no_builtin: bool) -> list[Rule]:
    rules: list[Rule] = [] if no_builtin else load_builtin_pack()
    if extra:
        for path in extra:
            if not path.exists():
                raise _UsageError(
                    f"error: rules path does not exist ({path}) — check the --rules value"
                )
        rules = rules + load_rules(extra)
    if not rules:
        raise _UsageError(
            "error: no rules loaded (--no-builtin without --rules) — pass a rules "
            "directory or drop --no-builtin"
        )
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for rule in rules:
        if rule.id in seen and seen[rule.id] != rule.source_file:
            duplicates.append(
                f"duplicate rule id {rule.id!r} in {rule.source_file} "
                f"(already defined in {seen[rule.id]}) — custom packs must use their own prefix"
            )
        seen.setdefault(rule.id, rule.source_file)
    if duplicates:
        raise RuleLoadError(sorted(duplicates))
    return sorted(rules, key=lambda r: r.id)


def _parse(path: Path, quiet: bool) -> ParseResult:
    if not path.exists():
        raise _UsageError(f"error: path does not exist ({path}) — check the directory argument")
    if not path.is_dir():
        raise _UsageError(f"error: path is not a directory ({path}) — point at a Terraform root")
    result = parse_directory(path)
    if not quiet:
        for warning in result.warnings:
            where = warning.file or "<repo>"
            if warning.line is not None:
                where = f"{where}:{warning.line}"
            print(f"warning {warning.code} {where}: {warning.message}", file=sys.stderr)
    if result.files_total > 0 and result.files_failed == result.files_total:
        raise _InputError(
            f"error: none of the {result.files_total} .tf files could be parsed "
            f"({path}) — is this a Terraform directory?"
        )
    return result


def _write_output(text: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(text)
        return
    tmp: str | None = None
    try:
        # Atomic write: temp file in the destination directory, then rename (NFR-R3).
        fd, tmp = tempfile.mkstemp(dir=str(output.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, output)
        tmp = None
    except OSError as exc:
        raise _UsageError(
            f"error: cannot write output file ({output}): {exc} — check the path and permissions"
        ) from exc
    finally:
        if tmp is not None:  # write or rename failed: do not leave the temp file behind
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _cmd_scan(args: argparse.Namespace) -> int:
    rules = _load_all_rules(args.rules, args.no_builtin)
    parse_result = _parse(args.path, args.quiet)
    assessment = evaluate(parse_result.graph, rules)

    if args.framework:
        wanted = set(args.framework)
        assessment = dataclasses.replace(
            assessment,
            frameworks=[s for s in assessment.frameworks if s.framework in wanted],
        )

    if args.format == "md":
        text = render_markdown(assessment, include_passes=args.include_passes)
    elif args.format == "html":
        text = render_html(assessment, include_passes=args.include_passes)
    else:
        generated_at = datetime.now(UTC).isoformat(timespec="seconds") if args.timestamp else None
        text = render_json(assessment, generated_at=generated_at)

    _write_output(text, args.output)

    if not args.quiet:
        summary = assessment.summary
        by_sev = summary.findings_by_severity
        sev_text = (
            ", ".join(f"{by_sev[s]} {s}" for s in ("critical", "high", "medium") if by_sev[s])
            or "none"
        )
        print(
            f"scanned {summary.nodes_total} resources, "
            f"{summary.rules_evaluated + summary.rules_not_applicable} rules -> "
            f"score {summary.score}, findings: {sev_text} (see report)",
            file=sys.stderr,
        )

    breaching = _FAIL_ON_LEVELS[args.fail_on]
    breached = any(f.verdict == "fail" and f.severity in breaching for f in assessment.findings)
    return EXIT_FINDINGS if breached else EXIT_OK


def _cmd_graph(args: argparse.Namespace) -> int:
    parse_result = _parse(args.path, args.quiet)
    _write_output(to_json(parse_result.graph), args.output)
    return EXIT_OK


def _cmd_rules_list(args: argparse.Namespace) -> int:
    rules = _load_all_rules(args.rules, args.no_builtin)
    if args.format == "json":
        import json

        payload = [
            {
                "id": r.id,
                "severity": r.severity,
                "category": r.category,
                "title": r.title,
                "frameworks": sorted(r.mappings),
            }
            for r in rules
        ]
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return EXIT_OK

    headers = ("ID", "SEVERITY", "CATEGORY", "FRAMEWORKS", "TITLE")
    rows = [
        (r.id, r.severity, r.category, ",".join(sorted(r.mappings)) or "-", r.title) for r in rules
    ]
    widths = [max(len(h), *(len(row[i]) for row in rows)) for i, h in enumerate(headers)]
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sys.stdout.write(line.rstrip() + "\n")
    for row in rows:
        sys.stdout.write(
            "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip() + "\n"
        )
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Run archscan; returns the exit code (spec 006 §4)."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits 2 on usage errors and 0 on --help/--version; pass through.
        return int(exc.code or 0)

    try:
        if args.command == "scan":
            return _cmd_scan(args)
        if args.command == "graph":
            return _cmd_graph(args)
        return _cmd_rules_list(args)
    except _UsageError as exc:
        print(exc, file=sys.stderr)
        return EXIT_USAGE
    except RuleLoadError as exc:
        print("error: rule files are invalid — fix the problems below and retry", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return EXIT_INPUT
    except _InputError as exc:
        print(exc, file=sys.stderr)
        return EXIT_INPUT


def entry() -> None:  # console_scripts entry point
    sys.exit(main())
