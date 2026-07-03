## What spec(s) does this implement?

Link to relevant spec(s), e.g. `specs/001-architecture-graph-schema.md`. Check the spec's acceptance criteria — are all of them addressed?

## Acceptance criteria checklist

- [ ] All acceptance criteria from the spec(s) are tested
- [ ] Type hints on all public functions
- [ ] Docstrings on all public functions (one-liner, no redundancy)
- [ ] No hardcoded paths (everything relative or `import.meta.url`-based)
- [ ] Tests pass locally: `pytest tests/ -v`
- [ ] Coverage gates met (90% overall, 100% on `engine/conditions.py`)
- [ ] `ruff check` and `mypy --strict` pass
- [ ] Determinism tests pass (if output format changed)
- [ ] Golden files reviewed (not blindly regenerated)
- [ ] No new CVEs: `pip-audit -r requirements.txt --no-deps --disable-pip`

## Changes

Brief summary of what this PR implements and why.

## Testing

How to test this locally? Provide steps or commands.

## Relevant issues

Closes #...

---

**Note:** this is a specification-phase project. Keep changes within the scope of the spec(s) you're implementing. If you discover a spec issue, open a separate issue to discuss before deviating from the spec.
