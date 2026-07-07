# Getting Started with ArchAssessor

**Phase 1 core is implemented and working.** The `archscan` CLI parses a Terraform
directory offline, evaluates it against a built-in SOC 2-mapped rule pack, and
produces a scored Markdown / HTML / JSON assessment. See
[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for exactly what is done vs.
still open, and the full spec suite (`specs/`) for the design behind it.

## Prerequisites

- **Python 3.13+** (to run the `archscan` CLI)
- **Git** (to clone the repo)
- Optional: **Node.js 14+** (only to view the interactive `GUIDE.html` spec map)

Runtime dependencies are just two pinned packages (`python-hcl2`, `PyYAML`).

## Quick start — run a scan (5 minutes)

```bash
git clone https://github.com/deepakd0/arch-assessor.git
cd arch-assessor

python3.13 -m venv venv
./venv/bin/pip install -e .

# Assess the bundled fixture, or point it at your own Terraform directory:
./venv/bin/archscan scan tests/fixtures/terraform/simple
./venv/bin/archscan scan /path/to/your/terraform --format html -o report.html
```

Useful commands:

```bash
archscan scan DIR --fail-on high      # exit 1 if any high+ finding (CI gating)
archscan graph DIR                    # dump the parsed architecture graph as JSON
archscan rules list                   # list the built-in rule pack
archscan --help                       # full flag reference
```

Run the tests to verify the build (193 tests, ~4s):

```bash
./venv/bin/pip install pytest pytest-cov hypothesis
./venv/bin/pytest tests/ -q
```

## View the visual spec guide (optional)

```bash
node serve.mjs     # then open http://localhost:4173
```

A dark-themed map of the entire spec suite — pipeline diagrams, file tree, roadmap.
Or open the files directly:

- **Start here:** [README.md](README.md) — the executive summary, pitch, roadmap.
- **For decision makers:** [PRD.md](PRD.md) — personas, user stories, success metrics.
- **For builders:** [specs/000-overview.md](specs/000-overview.md) — conventions, build order, glossary.
- **For complete picture:** [GUIDE.html](GUIDE.html) — open in any browser (no server needed).

### Reading order for the design docs

1. [README.md](README.md) — "What is this, who's it for, why Phase 1 is shaped this way"
2. [PRD.md](PRD.md) — "Who are the personas, what are we measuring success by"
3. [GUIDE.html](GUIDE.html) or [TRACEABILITY.md](TRACEABILITY.md) — "Map of everything"
4. [specs/000-overview.md](specs/000-overview.md) — "How to read the other specs, glossary, conventions"
5. Specs `001`–`006` — "What gets built, box by box" (implementation)
6. Specs `007`–`011` — "Quality bar, security, tests, governance" (production-readiness)
7. [decisions/](decisions/README.md) — "Why this choice and not the obvious alternative"

## Project structure

```
arch-assessor/
├── README.md                        entry point, pitch, roadmap
├── PRD.md                           product requirements
├── GUIDE.html                       interactive visual guide
├── GETTING_STARTED.md               this file
├── CONTRIBUTING.md                  how to implement or extend
├── TRACEABILITY.md                  requirement → spec → test matrix
│
├── specs/                           implementation + production-readiness specs
│   ├── 000-overview.md              conventions, glossary, build order
│   ├── 001-architecture-graph-schema.md
│   ├── 002-terraform-parser.md
│   ├── 003-rule-format-and-framework-mappings.md
│   ├── 004-evaluation-engine.md
│   ├── 005-report-renderer.md
│   ├── 006-cli.md
│   ├── 007-nonfunctional-requirements.md
│   ├── 008-threat-model.md
│   ├── 009-test-strategy.md
│   ├── 010-lifecycle-versioning-support.md
│   └── 011-rule-pack-governance.md
│
├── decisions/                       architecture decision records
│   ├── README.md                    ADR format and index
│   ├── 0001-record-architecture-decisions.md
│   ├── 0002-offline-hcl-parsing-with-python-hcl2.md
│   ├── 0003-declarative-yaml-rules-not-code.md
│   ├── 0004-three-valued-verdict-logic.md
│   ├── 0005-stdlib-cli-and-rendering.md
│   ├── 0006-byte-deterministic-output.md
│   ├── 0007-license-and-open-core.md
│   └── 0008-ingest-sarif-not-build-scanners.md
│
├── serve.mjs                        local dev server for GUIDE.html
├── .claude/
│   └── launch.json                  Claude Code preview config (optional)
├── .gitignore
└── LICENSE (Apache-2.0)
```

## Viewing on different machines

### macOS / Linux

```bash
# Clone
git clone https://github.com/deepakd0/arch-assessor.git
cd arch-assessor

# Serve the guide
node serve.mjs

# Open browser
open http://localhost:4173
# or: firefox http://localhost:4173
```

### Windows

```powershell
# Clone
git clone https://github.com/deepakd0/arch-assessor.git
cd arch-assessor

# Serve the guide
node serve.mjs

# Open browser
start http://localhost:4173
```

### Docker (optional, for CI/CD integration)

Create `Dockerfile`:

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .
EXPOSE 4173
CMD ["node", "serve.mjs"]
```

Build and run:

```bash
docker build -t arch-assessor .
docker run -p 4173:4173 arch-assessor
```

Then visit **http://localhost:4173**.

## Using with Claude Code (optional)

If you have [Claude Code](https://claude.com/claude-code) installed, the repo includes a `.claude/launch.json` config:

```bash
# From the arch-assessor directory
/preview_start arch-assessor-guide
```

This starts the server and opens a live preview panel in Claude Code.

## What's next?

**Phase 1 core is built** (`src/archassessor/`, 193 tests, mypy-strict clean). To
extend it, see [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for the ordered
list of remaining Phase-1 hardening items and Phase-2 features, and
[CONTRIBUTING.md](CONTRIBUTING.md) for the workflow. In brief:

1. **Pick an open item** from IMPLEMENTATION_STATUS.md (each names the spec section that defines "done").
2. **Follow the spec** — every spec (`specs/001`–`011`) has numbered acceptance criteria that become pytest tests.
3. **Run the gates** before a PR: `pytest tests/ -q`, `ruff check`, `mypy --strict src/` (all wired into CI).
4. **Follow the ADRs** in `decisions/` — they record why each choice was made; re-read before deviating.

## Status

- **Phase 1** (MVP): specced (specs 000–011, PRD, ADRs) **and core implemented** — see [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for the done/open breakdown.
- **Phase 2–6** (roadmap): planned; specs not yet written.

One human gate remains before any public `0.1.0`: an SME must sign off the SOC 2 /
ISO / PCI mappings (a technical pre-review is recorded in
`src/archassessor/rules/builtin/MAPPING-REVIEWS.md`).

## Questions or issues?

See [SECURITY.md](SECURITY.md) for security-related reports.

For everything else, open an issue on GitHub — this repo is public and contributions are welcome once the license decision is finalized (see [ADR-0007](decisions/0007-license-and-open-core.md)).

---

**Status:** Phase 1 core implemented and tested · Last updated 2026-07-06 · **License:** Apache-2.0
