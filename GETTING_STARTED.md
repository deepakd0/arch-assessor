# Getting Started with ArchAssessor

This is a **specification-phase project** — the complete design docs for an architecture assessment platform, ready for implementation. Nothing is built yet; this repo is 100% specs, design decisions, and planning.

## Prerequisites

- **Git** (to clone the repo)
- **Node.js 14+** (to view the interactive guide)

**No other dependencies.** All specs are plain Markdown and HTML; no build steps needed.

## Quick start (5 minutes)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/arch-assessor.git
cd arch-assessor
```

(Or download as ZIP and extract.)

### 2. View the visual guide

#### Option A: Local preview with Node (recommended)

```bash
node serve.mjs
```

Then open **http://localhost:4173** in your browser. You'll see the interactive `GUIDE.html` — a dark-themed map of the entire spec suite, with pipeline diagrams, file tree, and roadmap.

#### Option B: Open files directly

- **Start here:** [README.md](README.md) — the executive summary, pitch, roadmap.
- **For decision makers:** [PRD.md](PRD.md) — personas, user stories, success metrics.
- **For builders:** [specs/000-overview.md](specs/000-overview.md) — conventions, build order, glossary.
- **For complete picture:** [GUIDE.html](GUIDE.html) — open in any browser (no server needed).

### 3. Read the docs

**In suggested order:**

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
git clone https://github.com/YOUR_USERNAME/arch-assessor.git
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
git clone https://github.com/YOUR_USERNAME/arch-assessor.git
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

This repo is a **specification blueprint**. To build the actual product:

1. **Read** the specs in the order suggested above.
2. **Implement Phase 1** starting with spec 001 (graph schema) → 003 (rule loader) → 004 (engine) → 002 (parser) → 005 (renderer) → 006 (CLI). Each spec has numbered acceptance criteria that become pytest tests.
3. **Set up the repo structure** as described in spec 000 §3 (`src/archassessor/`, `tests/`, etc.).
4. **Run tests** per spec 009 to gate every feature.
5. **Follow the ADRs** in `decisions/` — they document why each choice was made; re-read them before deviating.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the implementation playbook.

## Specification status

- **Phase 1** (MVP): fully specified (specs 000–011, PRD, all decision records).
- **Phase 2–6** (roadmap): planned but not yet specced.

No code is implemented yet. This is purely a design and planning artifact.

## Questions or issues?

See [SECURITY.md](SECURITY.md) for security-related reports.

For everything else, open an issue on GitHub — this repo is public and contributions are welcome once the license decision is finalized (see [ADR-0007](decisions/0007-license-and-open-core.md)).

---

**Status:** Specification phase, 2026-07-03 · **License:** Apache-2.0 · **Next:** Implementation phase
