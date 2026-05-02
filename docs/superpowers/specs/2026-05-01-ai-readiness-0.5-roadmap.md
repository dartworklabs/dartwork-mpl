---
orphan: true
---

# dartwork-mpl AI-Readiness 0.5+ Roadmap

## Context

dartwork-mpl 0.4.x cycle(#64–#119) shipped a strong AI affordance baseline:
free-form `width=`/`aspect=` API, lint module + 15-rule SSOT
(`02-anti-patterns.yaml`), 7-check `validate_figure()` with
`validate_fixes.get_fix_suggestions()`, MCP server with 7 tools / 12 resources
/ 2 prompts, an 18-template AI gallery (`09_ai_templates`), MCP setup
guides for Claude Code/Cursor (#97), JSON lint sibling tool (#94),
44-scenario robustness suite (#108), and mypy --strict + ruff full rules
(#99–#103). README and Sphinx warnings have been polished
(138 → 2 warnings).

What is **not yet** addressed but matters for AI agents using this
library — across all three personas (MCP IDE agents, library-importing
LLMs, docs-fetching LLMs):

1. **No zero-config entry-point file** (`CLAUDE.md` / `AGENTS.md` /
   `llms.txt`) at repo root. AI clients that auto-detect these can't find
   dartwork-mpl's "use this, not that" rules without reading docs.
2. **High-value helper APIs are submodule-only**. `dm.suggest_chart_type`,
   `dm.validate_data`, `dm.save_figure`, `dm.optimize_legend`,
   `dm.auto_select_colors`, `dm.add_value_labels`,
   `dm.create_figure_with_style`, `dm.check_figure_quality` exist but only
   under `dm.helpers.*`, hidden from `dir(dm)`. LLMs that don't read
   submodules miss them.
3. **`parse_width` / `parse_aspect` errors don't self-correct**. Common
   typos (`"20.2"`, `"widee"`, `"20cm "`) raise `ValueError` without "did
   you mean" suggestions. Each round-trip costs an LLM token budget.
4. **`migrate_legacy_code` MCP prompt was promised in spec §5.3 but is
   unimplemented**. With #87 deleting all 0.3 names (BREAKING), an LLM
   that has 0.3 code in its training data crashes at runtime with no
   automated rewrite path.
5. **`lint` is MCP-only**. There is no `dm.lint(code)` Python entry-point;
   offline workflows can't lint locally without spinning up the MCP
   server.
6. **`09_ai_templates/*.py` carries no machine-readable metadata** (use
   case, difficulty, related anti-pattern rule IDs, expected
   data-shape). Intent matching ("user wants a horizontal bar chart →
   which template?") relies on docstring scanning.
7. **`asset/prompt/` has unswept legacy** (`coding-rules.md`,
   `general-guide.md`, `layout-guide.md`, `_legacy/`). Spec §7.2 only
   covered `USAGE_GUIDE.md`. LLMs reading the prompt corpus get mixed
   signals.
8. **Robustness suite (44 scenarios, #108) has not flowed back into the
   anti-pattern catalog**. Lint rules and the test suite are diverging
   sources of truth about "things AI agents do wrong."

This document specifies a phased plan that closes these gaps across two
minor releases (0.5 and 0.6).

---

## Goals & Non-Goals

### Goals

- Zero-config discoverability for AI agents that scan repo root.
- Single-tier `dm.<symbol>` access for every high-value helper an LLM
  would reach for.
- Self-correcting error messages: every public input path that an LLM is
  likely to mis-spell suggests the closest valid form.
- Native (non-MCP) parity for lint and migration helpers.
- Machine-readable metadata layer over `09_ai_templates` so MCP and
  static-fetching agents can rank templates by intent.
- One canonical prompt corpus — no `_legacy/`, no orphan guide files.

### Non-Goals

- Re-architecting the MCP server; it is healthy.
- New visualization features (tight_crop already shipped via #107).
- New style presets or color palettes.
- Replacing the existing `validate_figure()` heuristic with anything
  ML-based.

### Success Criteria

- AI agent scenario test (extension of spec §13):
  1. **A**: agent in fresh clone discovers MCP setup + first-call
     conventions purely from `CLAUDE.md`/`AGENTS.md` (no human
     pointing).
  2. **B**: agent given `width="20.2"` recovers on the next call from
     the suggestion in the error.
  3. **C**: agent given a 0.3-style snippet calls `migrate_legacy_code`
     and receives a 0.4 rewrite + applies it.
  4. **D**: agent uses `dm.lint(code)` natively (no MCP) and gets the
     same rule list as the MCP path.
  5. **E**: agent searches "horizontal bar template" and the template
     index returns `plot_bar_horizontal.py` ranked first.

---

## Phase Plan

| Phase | Theme | Tracks | Target |
|---|---|---|---|
| **0.5.0** | Discoverability + self-correction | T1, T2, T3 | 0.5 minor cut |
| **0.5.x patch** | Native parity + asset hygiene | T4, T5 | follow-on patches |
| **0.6.0** | Metadata + drift convergence | T6, T7, T8 | next minor |

Each track is 1 PR, sized to 200–800 LoC. PRs are independent; tracks
inside a phase can land in any order.

---

## Phase 0.5.0 — Discoverability & Self-Correction

### Track T1 — Zero-config entry-point files (closes G2, N1's docs side)

**Goal**: AI client that scans repo root finds dartwork-mpl conventions
without configuration.

**File map**:

- **Created**:
  - `CLAUDE.md` (repo root) — symlink-style pointer with sections:
    "What is dartwork-mpl", "First-call rules" (3 lines: width/aspect API,
    style.use, save_formats), "Anti-patterns" (link to
    `docs/integrations/index.md` and `02-anti-patterns.yaml`),
    "MCP setup" (link to `docs/integrations/mcp_server.md`),
    "Migrating from 0.3" (link to `docs/migration.md`).
    ~80 lines.
  - `AGENTS.md` — same content, second filename for non-Claude clients
    (Aider, Cursor's `.cursorrules`-equivalent path).
  - `llms.txt` — top-of-tree machine index for ChatGPT/perplexity-style
    fetchers. Format: [llmstxt.org][] spec — title, blurb, links to
    canonical docs (Quickstart, MCP guide, anti-patterns YAML raw,
    migration). ~30 lines.
  - `llms-full.txt` — concatenated form of the canonical files for one-shot
    LLM ingestion (Quickstart + Migration + 02-anti-patterns + 09_ai_templates
    README). Generated, not hand-edited.

  [llmstxt.org]: https://llmstxt.org

- **Modified**:
  - `docs/_ext/build_hooks.py` — new hook
    `generate_llms_full_txt(app)` that builds `llms-full.txt` from the
    canonical sources at build time so it never drifts.
  - `pyproject.toml` `[tool.hatch.build]` includes — ship `llms.txt` and
    `llms-full.txt` in sdist & wheel.
  - `README.md` — add a one-line "AI agents: see [CLAUDE.md](CLAUDE.md)"
    callout above the existing "Migrating from 0.3.x" callout.

**Verification**: `cat CLAUDE.md` and `curl -L llms-full.txt` from the
GitHub raw URL each contain a self-contained agent-onboarding flow. PR
includes a manual scenario test transcript.

---

### Track T2 — Top-level helper exposure (closes G1)

**Goal**: Every helper that an LLM has a reasonable chance of reaching
for is accessible as `dm.<name>` with a single import.

**File map**:

- **Modified**:
  - `src/dartwork_mpl/__init__.py`:
    - Add `from .helpers import (validate_data, auto_select_colors,
      add_value_labels, optimize_legend, suggest_chart_type,
      check_figure_quality, save_figure, create_figure_with_style)`.
    - Add each name to `__all__` under a new `# Helpers (high-level
      composition utilities)` section.
  - `docs/api/index.rst` — autosummary block for the newly-exposed
    surface (single category per module is fine; the existing
    `helpers.*` rst pages already render the details).
  - `docs/integrations/index.md` — small table at the top: "If the
    agent intends X, call dm.Y" (X = "verify input data", "pick palette",
    "pick chart type", "save with hi-res", etc.). Rows reference
    top-level names only.

**Risk**: name collision with already-exported `format_axis_*`. None
expected (the 8 new names don't overlap).

**Verification**: `python -c "import dartwork_mpl as dm;
print([n for n in dir(dm) if not n.startswith('_')])"` includes the 8
new names. mypy --strict still clean.

---

### Track T3 — Self-correcting unit/aspect errors (closes G4)

**Goal**: `parse_width` / `parse_aspect` raise `ValueError` whose
message tells the LLM exactly what to retry.

**File map**:

- **Modified**:
  - `src/dartwork_mpl/units.py`:
    - `parse_width(v)`: when a bare number arrives as string
      (`"20"`, `"20.2"`), suggest `"20cm"`. When unit token fails to
      match, run `difflib.get_close_matches` over `{"cm", "mm", "in"}`
      and append `Did you mean '20cm'?`. When trailing whitespace is
      detected, hint at it explicitly (`got "20cm "; trim trailing
      whitespace`).
    - `parse_aspect(v)`: same pattern over the 6 aspect tokens
      (`square / portrait / standard / golden / wide / cinema`). For
      numeric-string inputs (`"0.75"`), suggest `aspect=0.75` (no
      quotes).
  - `tests/test_units.py` — assertion examples added for each new
    suggestion path.

- **Created**:
  - None. Logic stays in `units.py`; no new module.

**Verification**: Each new test calls the parser with the bad input and
asserts that the `ValueError` message contains both the token name and
the closest valid form.

---

## Phase 0.5.x patches — Native parity & asset hygiene

### Track T4 — Native lint + migrate_legacy_code (closes G7, N1)

**Goal**: Anything an MCP tool can do, a Python caller can also do
without spinning up the MCP server.

**File map**:

- **Modified**:
  - `src/dartwork_mpl/__init__.py` — add `from . import lint` so
    `dm.lint.lint(code)` works. Add `from .lint import lint as
    lint_code` at top level (alias `dm.lint_code(...)` so the module
    name doesn't shadow the function).
  - `src/dartwork_mpl/lint.py` — add `migrate_legacy_code(code: str) ->
    str` function: regex-driven rewrite for the eight 0.3 patterns
    `dm.SW`/`MW`/`TW`/`DW`, `dm.FS_*`, `dm.WIDTHS[...]`, `dm.cm2in`,
    `dm.agent_utils.X`, `dm.xplot.X`, `figsize=(...)` argument on
    `dm.subplots`/`dm.figure`, and `tight_layout()`. Each rewrite
    rule lives next to the matching anti-pattern rule in
    `02-anti-patterns.yaml` (new field: `auto_fix.replacement` —
    optional template).
  - `src/dartwork_mpl/mcp/tools.py` — register
    `migrate_legacy_code(code: str)` as an MCP tool (delegates to the
    function above; no separate engine).
  - `docs/integrations/mcp_server.md` — document the new tool with
    a usage example.

- **Created**:
  - `tests/test_migrate_legacy.py` — golden-file test fixtures:
    `tests/fixtures/legacy/<pattern>.in.py` →
    `tests/fixtures/legacy/<pattern>.out.py`. One pattern per
    fixture pair.

**Risk**: regex-only migration is best-effort. Acceptance criterion is
"works on the spec §13 scenario B input"; complex AST rewrites are
explicitly out-of-scope (see Out of Scope).

**Verification**: Spec §13 scenario B reproduces. MCP integration test
calls the tool and round-trips through `lint_dartwork_mpl_code` to
confirm zero rule violations on the rewrite.

---

### Track T5 — `asset/prompt/` cleanup (closes N2)

**Goal**: A single canonical prompt corpus. No `_legacy/`. No orphan
guide files.

**File map**:

- **Deleted**:
  - `src/dartwork_mpl/asset/prompt/_legacy/` (entire dir).
  - `src/dartwork_mpl/asset/prompt/coding-rules.md` (content folded
    into `01-policy.md`).
  - `src/dartwork_mpl/asset/prompt/general-guide.md` (content folded
    into `00-index.md`).
  - `src/dartwork_mpl/asset/prompt/layout-guide.md` (content folded
    into `03-recipes.md` under a new "Layout" section).

- **Modified**:
  - `00-index.md` — concise overview that lists the 5 canonical files
    (`00-index`, `01-policy`, `02-anti-patterns.yaml`, `03-recipes`,
    `05-templates/`) and nothing else.
  - `src/dartwork_mpl/prompt.py` — `list_prompts()` warns if it
    detects unexpected files in `asset/prompt/` (drift guard).

**Verification**: `dm.list_prompts()` returns exactly the 5 canonical
entries. `dm.get_prompt("coding-rules")` returns a deprecation message
with the new pointer.

---

## Phase 0.6.0 — Metadata & drift convergence

### Track T6 — Template metadata frontmatter (closes G6)

**Goal**: AI agents (especially MCP) can rank templates by user intent.

**File map**:

- **Modified** — every `docs/examples_source/09_ai_templates/plot_*.py`
  (24 files after #98 + #96):
  - Add a YAML frontmatter block immediately after the docstring
    (separated from sphinx-gallery title block):
    ```python
    """
    Bar
    ===
    ...
    """
    # ai-template-meta:
    # use_case: "Compare a small set of categorical values"
    # difficulty: "beginner"
    # data_shape: "categories: list[str], values: list[float]"
    # related_rules: ["W001-figsize-direct", "W004-tight-layout"]
    # tags: ["bar", "categorical", "comparison"]
    ```
  - Comment-block format is chosen so sphinx-gallery still treats the
    file as a normal example (no rST/Markdown frontmatter parser
    available in the gallery pipeline).

- **Created**:
  - `src/dartwork_mpl/asset/prompt/05-templates/_index.json` —
    generated at build time from the comment metadata. Schema:
    `{template_id: {use_case, difficulty, data_shape, related_rules,
    tags, source_path}}`.
  - `src/dartwork_mpl/mcp/tools.py` new tool
    `find_template(intent: str) -> list[dict]` — uses simple keyword
    + tag matching on `_index.json` to rank templates.
  - `docs/_ext/build_hooks.py` new hook
    `generate_template_index(app)` that scans the comment metadata
    and writes `_index.json` to both
    `src/dartwork_mpl/asset/prompt/05-templates/` and
    `docs/_build/html/_static/templates_index.json` (so docs-fetching
    LLMs can also use it).

**Verification**: `dm.get_prompt("05-templates/_index")` returns the
JSON. Spec §13 scenario E: MCP `find_template("horizontal bar")`
returns `plot_bar_horizontal` first.

---

### Track T7 — Robustness suite ↔ anti-pattern convergence (closes N3)

**Goal**: One source of truth for "things AI agents get wrong."

**File map**:

- **Modified**:
  - `tests/robustness/test_*.py` — every test that currently asserts
    a defensive behaviour gets a `# SSOT: rule_id=W0XX` comment
    pointing at the matching catalog rule. Tests without a matching
    rule become candidates for adding the rule.
  - `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml` — append
    new rules derived from the unmatched test scenarios. Aim for net
    coverage gain of ≥ 8 new rules (44 scenarios − ~15 existing rules
    minus general invariants ≈ 8 candidates).
  - `tests/robustness/test_catalog_alignment.py` (new) — meta-test:
    asserts that every `# SSOT: rule_id=...` comment references an
    existing rule, and prints a coverage report.

- **Created**:
  - `docs/superpowers/specs/2026-05-XX-anti-pattern-coverage.md` —
    coverage matrix between robustness scenarios and anti-pattern
    rules, kept in-tree as governance.

**Verification**: `pytest tests/robustness/test_catalog_alignment.py`
passes; coverage report prints in CI.

---

### Track T8 — Docs interactive→static fallback (closes G8)

**Goal**: AI agents that scrape rendered docs (no JS) get a complete
narrative for the modules currently demonstrated only by the
`dynamic_ux.js` widgets (install picker, FAQ filter, helper ruler,
lint sim, color favorites).

**File map**:

- **Modified** — for each of the 5 `dynamic_ux` widget host pages:
  - `docs/installation/index.md` — add a "Plain text install matrix"
    section above the dynamic picker. Lists every command verbatim
    (uv/pip/Poetry/conda × macOS/Linux/Windows = 12 lines).
  - `docs/troubleshooting.md` — add a static "All FAQs" section
    listing every Q+A in order; the JS filter becomes pure
    enhancement.
  - `docs/usage_guide/quickstart.md` — add a static
    `dm.fs/dm.fw/dm.lw` reference table that mirrors the slider's
    current state for each preset.
  - `docs/usage_guide/save_export.md` — add a static
    "Validation lint reference" table listing every warning the lint
    sim emits.

**Verification**: `lynx -dump
docs/_build/html/installation/index.html` (or any text browser)
contains all install commands without JS rendering. Manual review.

---

## File map summary

```
Created (new files):
  CLAUDE.md
  AGENTS.md
  llms.txt
  llms-full.txt                                          (build hook)
  src/dartwork_mpl/asset/prompt/05-templates/_index.json (build hook)
  tests/fixtures/legacy/*.in.py / *.out.py
  tests/robustness/test_catalog_alignment.py
  docs/superpowers/specs/2026-05-XX-anti-pattern-coverage.md

Modified:
  README.md                                              (+1 line)
  pyproject.toml                                         (sdist includes)
  src/dartwork_mpl/__init__.py                           (T2 + T4)
  src/dartwork_mpl/units.py                              (T3)
  src/dartwork_mpl/lint.py                               (T4)
  src/dartwork_mpl/mcp/tools.py                          (T4 + T6)
  src/dartwork_mpl/prompt.py                             (T5 drift guard)
  src/dartwork_mpl/asset/prompt/00-index.md              (T5)
  src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml    (T4 + T7)
  docs/_ext/build_hooks.py                               (T1 + T6)
  docs/integrations/index.md                             (T2)
  docs/integrations/mcp_server.md                        (T4 + T6)
  docs/api/index.rst                                     (T2)
  docs/installation/index.md                             (T8)
  docs/troubleshooting.md                                (T8)
  docs/usage_guide/quickstart.md                         (T8)
  docs/usage_guide/save_export.md                        (T8)
  docs/examples_source/09_ai_templates/plot_*.py         (T6, 24 files)

Deleted:
  src/dartwork_mpl/asset/prompt/_legacy/                 (entire dir)
  src/dartwork_mpl/asset/prompt/coding-rules.md
  src/dartwork_mpl/asset/prompt/general-guide.md
  src/dartwork_mpl/asset/prompt/layout-guide.md
```

---

## Verification

End-to-end agent simulation (extends spec §13):

1. **Scenario A — zero-config**: agent in `git clone` only sees
   `CLAUDE.md` at root, follows it, calls `dm.subplots(width="12cm",
   aspect="wide")`, runs `validate_figure()`, gets 0 issues.
2. **Scenario B — self-correction**: agent passes `width="20.2"`. The
   raised `ValueError` says `Did you mean '20cm'?`. Agent retries with
   `"20cm"`, succeeds.
3. **Scenario C — legacy migration**: agent has 0.3 code with
   `dm.SW`/`figsize=`/`tight_layout()`. Calls
   `dm.lint.migrate_legacy_code(src)` (or MCP equivalent), receives
   rewritten 0.4 source, runs it, gets 0 lint violations.
4. **Scenario D — native parity**: agent calls
   `dm.lint_code("import dartwork_mpl as dm\nfig, ax = plt.subplots()")`,
   gets the same warnings list the MCP tool returns.
5. **Scenario E — intent matching**: agent calls
   MCP `find_template("horizontal bar comparison")`. First result is
   `plot_bar_horizontal`. Agent fetches via `dm.get_prompt(
   "05-templates/bar_horizontal")`, runs it, succeeds.
6. **Scenario F — top-level discovery**: agent introspects
   `dir(dm)`, sees `validate_data`, `suggest_chart_type`,
   `save_figure`, `optimize_legend`, etc., and uses one without
   reading submodules.

CI gates (existing): mypy --strict, ruff full rules, pytest
robustness suite, sphinx-build no-warnings.

CI gates (added by this plan):
- T7's `test_catalog_alignment.py` ensures robustness ↔ rules
  convergence.
- T1's `llms-full.txt` build hook runs in `sphinx-build` and fails
  the build if any canonical doc went missing.
- T6's metadata `_index.json` build hook fails if any
  `09_ai_templates/plot_*.py` lacks the meta block.

---

## Out of Scope

- AST-based migration in T4 (regex is enough for the documented
  patterns; AST belongs to a separate "1.0 hardening" cycle).
- New MCP tools beyond `migrate_legacy_code` (T4) and `find_template`
  (T6).
- Adding new style presets, palettes, or chart types.
- Replacing `validate_figure()`'s heuristic checks with model-based
  ones.
- Touching `tight_crop()` or any layout primitive shipped in 0.4.x.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `CLAUDE.md`/`AGENTS.md` drift from docs | T1 generated `llms-full.txt` + sphinx build hook re-derives from canonical sources every build. Hand-edit only the small `CLAUDE.md` skeleton. |
| Top-level re-export bloat (T2) | Keep the 8 names tightly scoped; don't add helpers to `__all__` casually. Re-running `dir(dm)` length must stay below ~120 names. |
| Regex migration false positives (T4) | Golden fixtures cover every documented 0.3 pattern. Anything outside the documented set is a hard error, not a silent rewrite. Manual review encouraged in the migration prompt's output prefix. |
| Template metadata maintenance burden (T6) | Comment block format keeps the metadata next to the code. Build hook fails the build on missing block, so drift is detected immediately. |
| Sphinx warning regression on docs additions (T8) | `sphinx_warnings.txt` budget = 2 (current). Any new warning fails CI. |

---

## Migration Plan

1. **PR 1 (T1)** — Entry-point files. Smallest, highest visibility,
   no API change. Land first.
2. **PR 2 (T2)** — Top-level helper exposure. API additive only;
   safe within 0.5.0 minor.
3. **PR 3 (T3)** — Self-correcting errors. API additive
   (better messages); safe.
4. **Cut 0.5.0** after PR 1–3.
5. **PR 4 (T4)** — Native lint + `migrate_legacy_code`. Includes
   YAML schema additions; release as 0.5.1 patch.
6. **PR 5 (T5)** — Asset cleanup. Bundled file removals; release as
   0.5.2 patch (semver-safe because the deleted files were never
   API).
7. **PR 6 (T6)** — Template metadata + `find_template` MCP tool.
   Touches 24 example files; large diff but mechanical. Release as
   0.6.0.
8. **PR 7 (T7)** — Robustness ↔ catalog convergence. Test-only PR
   plus rule additions; release with 0.6.0 or as 0.6.1.
9. **PR 8 (T8)** — Static docs fallback. Docs-only; can ship any
   time, suggested with 0.6.0.

---

## References

- Existing 0.4 design spec:
  [2026-04-29-dartwork-mpl-ai-readiness-design.md](2026-04-29-dartwork-mpl-ai-readiness-design.md)
- PR1 plan (M0–M4):
  [../plans/2026-04-29-pr1-core-width-aspect-lint.md](../plans/2026-04-29-pr1-core-width-aspect-lint.md)
- Anti-pattern catalog (SSOT):
  [../../../src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml](../../../src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml)
- llms.txt spec: https://llmstxt.org

---

## Self-Review Checklist

- [x] No "TODO" / "TBD" placeholders.
- [x] Each track has file map + verification.
- [x] Phases ordered by dependency (T2 doesn't depend on T1; safe).
- [x] Risk section identifies maintenance burdens.
- [x] No contradiction between Goals and Out of Scope.
- [x] Every gap from the re-assessment has a track assigned (G1→T2,
      G2→T1, G4→T3, G6→T6, G7→T4, G8→T8, N1→T1+T4, N2→T5, N3→T7;
      G3 + G5 already resolved upstream).
- [x] Spec is decomposed enough to start with PR 1 today; PRs are
      independent.
