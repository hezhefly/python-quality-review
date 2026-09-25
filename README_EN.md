# python-quality-review

**中文**: [README.md](README.md)

> A code-quality & architecture review **Claude Code Skill** for Python projects.
> Systematically reviews six dimensions — **code style / encapsulation boundaries /
> high cohesion & low coupling / orphan methods / architecture & design patterns /
> test quality** — and outputs a structured report graded P0–P3.
> Standards are drawn from engineering practices of mature open-source projects and
> the classic code-smell body of knowledge.

## What problem it solves

The generic `code-review` skill asks "does this work / is there a bug", but says almost
nothing about whether the **architecture holds up**. This skill answers a different question:

> Is this Python project's **engineering quality** at open-source standard?

Typical uses:

- Onboarding onto an unfamiliar Python repo — find the tech debt fast
- An architecture-level scan before merging a PR
- Aligning a project with mainstream engineering norms before open-sourcing it
- Producing a "quality baseline report" good enough for a weekly/debrief report

## Six review dimensions

| # | Dimension | Focus | Key checks |
|---|-----------|-------|-----------|
| 1 | Code style | Code-smell system | type-hint coverage, naming, docstrings, line length, exception handling, import order |
| 2 | Encapsulation | Public/internal boundary | `_` leakage, `__all__`, monkey-patching, dynamic attribute mounting |
| 3 | Cohesion & coupling + orphan methods | Cohesion / LCOM | orphan functions, fake classes, `utils/` abuse, cross-module internal-state access |
| 4 | Architecture & patterns | Template method / registry / layering | base-class design, extension-point completeness, if-elif dispatch chains, exception layering |
| 5 | Test quality | Realism principle | over-mocking, flaky `sleep` polling, core modules without unit tests |
| 6 | Dependencies & config | Optional deps / central config | dependency groups, lazy imports, centralized typed config |

Detailed checklists live in [`references/`](references/).

## Two operating modes

| | Quick mode (default) | Deep mode |
|---|---|---|
| Trigger | "look at this module", "review this file" | "full review", "deep audit", "whole-project inventory" |
| Coverage | Dimensions 1–3 | All 6 dimensions |
| Output | Compact table + P0/P1/P2 list | Full six-dimension report + improvement roadmap |
| Suited for | Single file / module | Whole project / formal report / pre-open-source |

Mention any of 全面/深度/完整/架构级/全项目/审计/盘点 or English equivalents
("full / deep / complete / architecture-level / whole-project / audit / inventory")
and it auto-upgrades to deep mode.

## Installation

### Option 1: skills.sh CLI (recommended, works across coding agents)

```bash
# Global install to Claude Code
npx skills add hezhefly/python-quality-review -g -a claude-code -y

# Or multiple agents at once (Codex / Cursor / OpenCode, ...)
npx skills add hezhefly/python-quality-review -g -a claude-code -a cursor -y
```

### Option 2: Manual copy for Claude Code (user-level)

```bash
git clone https://github.com/hezhefly/python-quality-review.git
cd python-quality-review
mkdir -p ~/.claude/skills/python-quality-review
cp SKILL.md ~/.claude/skills/python-quality-review/
cp -R references ~/.claude/skills/python-quality-review/
cp -R scripts ~/.claude/skills/python-quality-review/
```

Restart Claude Code, then invoke by the name `python-quality-review`.

### Option 3: One-line script

```bash
curl -fsSL https://raw.githubusercontent.com/hezhefly/python-quality-review/main/install.sh | bash
```

With no args it installs to user-level `~/.claude/skills/`; pass a project path to
install to that project's `.claude/skills/`.

## Usage

Just say, inside Claude Code:

```
Do a full quality review of the current project
```

or:

```
python-quality-review: review the src/your_package/agent/ module
```

The skill auto-picks quick vs. deep mode and prints a Markdown report to the session.
See [`references/report-template.md`](references/report-template.md).

## Best practices: get the most out of it

### 1. Run the preflight script first, then let the AI read deeply

The script surfaces objective facts; the AI judges semantics. Chain them:

```bash
# Step 1: machine scans first → objective P0/P1 list
python scripts/preflight.py src/ --min-severity P1
```

Then feed it to Claude Code:

```
Go over the preflight output: confirm what's actually worth fixing (drop false positives),
give concrete fix snippets for each P0/P1, then add the human-only dimensions
(orphan methods, test realism).
```

This way the AI spends no time finding "where the problem is" and focuses on "why and how to fix".

### 2. Pick the trigger that matches your goal

| What you want | Say |
|---------------|-----|
| Quick look at one file/module | "quick review of `src/foo/bar.py`" |
| Formal whole-project report | "do a **full** quality review of this project" |
| Pre-open-source alignment | "**deep audit**, improvement roadmap by P0–P3" |
| An unfamiliar repo | "**whole-project inventory**, tech-debt overview first" |
| One dimension only | "check only the **encapsulation boundary**: any cross-module `_private` access?" |

### 3. Don't let it change too much at once

This skill **only produces a report + roadmap — it does not edit code**. Once you have the P0 list:

- Ask it to fix P0 only (2–5 items) in one pass; move to the next batch after each lands
- For big changes (splitting a god class, reworking the exception hierarchy), ask for
  **approach options first**, then edit after you approve
- After edits, regress with `python scripts/preflight.py .` — check P0/P1 hit zero

### 4. Chain it with other skills into a pipeline

```
this skill (find problems) → python-refactoring (fix them) → code-review (verify nothing broke)
```

### 5. Keep the report as a baseline

- Save deep reports as `docs/quality-baseline-YYYY-MM.md`; compare next quarter to see P0 drop
- In CI: `python scripts/preflight.py . --min-severity P1` exits non-zero on P0/P1,
  blocking new tech debt

## Relationship to other skills

- **python-refactoring**: focused on *editing* code. This skill focuses on *finding problems +
  reporting + roadmaps*. Use them in sequence: review first, then refactor.
- **code-review**: generic functional/bug review. This skill supplements the architecture &
  engineering dimension.
- **security-audit**: security is its own dimension; this skill only touches encapsulation-adjacent
  concerns.
- **simplify**: focused on trimming code. This skill is the broader, full-system review.

## Repository layout

```
.
├── SKILL.md                   # skill entry point (frontmatter + workflow)
├── references/                # checklists / report template
│   ├── code-style-checklist.md
│   ├── encapsulation-checklist.md
│   ├── cohesion-coupling-checklist.md
│   ├── architecture-checklist.md
│   ├── best-practices-benchmarks.md
│   └── report-template.md
├── scripts/                   # zero-dependency preflight scripts (pure ast, no pip install)
│   ├── preflight.py           #   auto-surfaces P0/P1 objective issues
│   └── README.md
├── install.sh                 # one-line installer
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

> The repo-root `SKILL.md` **is** the skill — the standard skills.sh / skills CLI layout,
> so `npx skills add hezhefly/python-quality-review` hits it directly.

## Roadmap

- [x] Preflight script JSON output (preflight.py `--json`, CI-ready)
- [ ] Auto pre-scan of ruff / mypy / pylint results
- [ ] Profile presets for FastAPI / LangGraph / Pydantic projects
- [ ] Real project review samples under `examples/`

## License

[MIT](LICENSE)
