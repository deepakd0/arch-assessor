# 0002 — Parse HCL offline with python-hcl2; no terraform binary

**Status:** accepted (2026-07-02)

## Context
Three ways to read Terraform: (a) parse HCL text directly (`python-hcl2`); (b) shell out to
`terraform show -json` on a plan (accurate: expressions resolved, count/for_each expanded —
but requires the binary, `terraform init`, provider downloads, and often credentials);
(c) read state files (most accurate, most sensitive — state contains secrets).

## Decision
(a) for Phase 1. The distribution wedge demands zero-setup, zero-credential, zero-network
scanning of a bare checkout (PRD R-01, R-12). A plan-JSON ingestor is the planned Phase 2
*addition* (not replacement); state files are out indefinitely (secret-handling liability).

## Consequences
Good: `pip install` → scan in minutes; safe to run on untrusted repos (spec 008).
Bad: unresolved expressions and unexpanded count/for_each produce `unknown`s and single-node
approximations — accepted because ADR-0004 makes partial knowledge honest rather than wrong.
`python-hcl2` becomes 1 of our ≤ 3 runtime deps (NFR-M3) and its quirks are our quirks.
