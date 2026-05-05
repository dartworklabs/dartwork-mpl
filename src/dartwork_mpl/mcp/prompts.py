"""MCP Prompts for dartwork-mpl.

This module defines interactive prompts that guide users through
creating and reviewing dartwork-mpl plots. The wording is aligned
with the 0.4 SSOT in ``asset/prompt/`` (00-index, 01-policy,
02-anti-patterns, 03-recipes, 05-templates).

The prompt strings deliberately *describe* forbidden patterns
without spelling out their literal call form, so that the prompt
text itself does not trigger the dartwork-mpl lint engine. Each
rule reference cites the lint rule id from ``02-anti-patterns.yaml``.
"""

from fastmcp import FastMCP

__all__ = ["register_prompts"]

_MAX_INPUT_CHARS = 8192


def _truncate(value: str, label: str) -> str:
    """Cap a prompt input at :data:`_MAX_INPUT_CHARS` characters.

    Long inputs (e.g. a 100k-char paste) bloat the rendered prompt and
    waste the model's context budget. We append a clear marker so the
    model sees that truncation happened.
    """
    if len(value) <= _MAX_INPUT_CHARS:
        return value
    return (
        value[:_MAX_INPUT_CHARS]
        + f"\n\n... [truncated; {label} exceeded {_MAX_INPUT_CHARS} chars]"
    )


def register_prompts(mcp: FastMCP) -> None:
    """
    Register all prompts with the MCP server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance to register prompts with.
    """

    @mcp.prompt()
    def create_plot(description: str, data_sample: str = "") -> str:
        """Generate a dartwork-mpl plot script from a description.

        Parameters
        ----------
        description : str
            Natural language description of the desired plot
            (e.g. "tornado chart comparing energy savings across 5 buildings").
        data_sample : str
            Optional sample data in JSON or CSV format.
        """
        description = _truncate(description, "description")
        data_sample = _truncate(data_sample, "data_sample")
        data_section = ""
        if data_sample:
            data_section = f"""
## Data Sample
```
{data_sample}
```
Use this real data in the generated script.
"""

        return f"""You are an expert data visualization engineer using **dartwork-mpl 0.4**, a publication-quality matplotlib design system.

## Task
Generate a complete Python script that creates the following plot:

**Description**: {description}
{data_section}
## Mandatory Rules (0.4 surface)
1. **Import**: `import dartwork_mpl as dm` (and `import matplotlib.pyplot as plt` only if you actually need a `plt.colorbar` etc.).
2. **Figure creation**: Use `dm.subplots(width="13cm", aspect="standard")` or `dm.figure(width=..., aspect=...)`. Do NOT use `plt.subplots` / `plt.figure` (lint id `plt-subplots`). `width` accepts `"<n>cm"`, `"<n>in"`, `"<n>mm"`, `dm.cm(n)` / `dm.inch(n)` / `dm.mm(n)`, or a raw number (cm). `aspect` is one of `square / portrait / standard / golden / wide / cinema`, or a positive float.
3. **No `figsize` and no `dpi` argument** on figure/subplots calls (lint ids `figsize-direct`, `dpi-arg`). Width and aspect are decided separately so report-wide width consistency can be enforced; dpi is governed by the active style preset.
4. **Layout**: Call `dm.auto_layout(fig)` after data is plotted. `dm.simple_layout(fig)` is reserved for advanced GridSpec cases that `auto_layout` cannot fit. Do NOT call `tight_layout` (lint id `tight-layout`).
5. **No `plt.style.use`** anywhere — use `dm.style.use(...)` or pass `style=[...]` to `dm.subplots` (lint id `plt-style-use`).
6. **Colors**: prefer named palettes — `oc.*` (Open Color), `tw.*` (Tailwind), `dc.*` (dartwork core), `md.*`, `ad.*`, `cu.*`, `pr.*`. Raw hex works but triggers a lint info.
7. **Fonts / weights / line widths**: do NOT pass literal `fontsize=` numbers. Use `dm.fs(n)` / `dm.fw(n)` / `dm.lw(n)` offsets from the active style.
8. **Save**: end the script with `dm.save_formats(fig, "name", formats=("png", "pdf"), dpi=300)` (scripts) or `dm.save_and_show(fig, "name")` (notebooks). Do not stop at `plt.show` — the rendered artifact must be persisted (lint id `plt-show-only`).
9. **Width tokens**: the legacy width aliases under `dm` (the SW / MW / TW / DW / FS_* / WIDTHS family) were REMOVED in 0.4.0 — accessing them now raises `AttributeError` (lint id `deprecated-width-token`). Use `width="<n>cm"` plus an aspect token, or `dm.col1` / `dm.col2` for academic columns.

## Style presets (composite, recommended)
Apply via `dm.style.use("scientific")` or pass a stack to `dm.subplots(style=[...])`.

- `scientific` — journal paper defaults
- `report` — technical reports
- `presentation` — slide decks
- `poster` — large-format posters
- `web` — light, screen-friendly
- `minimal` — minimal decoration
- `dark` — dark background
- `*-kr` variants (`scientific-kr`, `report-kr`, `presentation-kr`, …) for Korean text

`base`, `font-*`, `lang-kr`, `theme-*`, `spine-*` are *primitive* mplstyle building blocks — the composite presets above are usually what you want.

## Reference resources (read on demand)
- `dartwork-mpl://guide/agent-entry` — entry point + decision tree
- `dartwork-mpl://guide/policy` — width / aspect / layout / color / save policy
- `dartwork-mpl://guide/recipes` — intent → function-call cookbook
- `dartwork-mpl://guide/anti-patterns` — machine-readable lint catalog
- `dartwork-mpl://templates/{{plot_type}}` — bundled starter scripts

## Skeleton
```python
import dartwork_mpl as dm

fig, ax = dm.subplots(width="13cm", aspect="standard")
# ... plot data on `ax` using named colors ...
ax.set_xlabel("...")
ax.set_ylabel("...")

dm.auto_layout(fig)
dm.save_formats(fig, "output", formats=("png", "pdf"), dpi=300)
```

Generate clean, well-commented code that follows these rules strictly. Run the result through `lint_dartwork_mpl_code(code)` and fix any `[CRITICAL]` finding before returning it.
"""

    @mcp.prompt()
    def style_review(code: str) -> str:
        """Review and fix a dartwork-mpl script for style compliance.

        Parameters
        ----------
        code : str
            Python source code to review.
        """
        code = _truncate(code, "code")
        return f"""You are a strict code reviewer for **dartwork-mpl 0.4**, a publication-quality matplotlib design system.

## Code to Review
```python
{code}
```

## Review Checklist (aligned with `asset/prompt/02-anti-patterns.yaml`)
Check the code against ALL of these rules and provide fixes. Each rule maps to a lint id you can confirm by calling `lint_dartwork_mpl_code(code)`.

### Critical (Must Fix)
- [ ] Uses `dm.subplots(width=..., aspect=...)` (or `dm.figure(width=..., aspect=...)`) instead of `plt.subplots` / `plt.figure` (`plt-subplots`).
- [ ] No literal `figsize` argument anywhere — width and aspect must be set via `dm.subplots` / `dm.figure` (`figsize-direct`).
- [ ] No `tight_layout` call — use `dm.auto_layout(fig)` (or `dm.simple_layout(fig)` for advanced GridSpec cases) (`tight-layout`).

### Warning (Should Fix)
- [ ] No `dpi=` argument on `plt.figure` / `plt.subplots` / `dm.subplots` / `dm.figure`. The active style controls dpi (`dpi-arg`).
- [ ] No `plt.style.use` — call `dm.style.use(...)` or pass `style=[...]` to `dm.subplots` (`plt-style-use`).
- [ ] No legacy width tokens (the SW / MW / TW / DW / FS_* / WIDTHS family on `dm`) — use `width="<n>cm"` plus an aspect token, or `dm.col1` / `dm.col2` for academic columns (`deprecated-width-token`).
- [ ] No `cm2in`-based figsize idiom (legacy 0.3 pattern: `figsize` constructed from `dm.cm2in` calls). Use `width="<n>cm"` plus an aspect token instead (`cm2in-figsize`).
- [ ] No mention of the retired sizing-policy slogan from 0.3 (lint id `zero-resize-mention`). 0.4 uses free-form width input plus a lint consistency guard.

### Info (Recommend)
- [ ] Script ends with `dm.save_formats(fig, "name", formats=("png", "pdf"), dpi=300)` or `dm.save_and_show(fig, "name")`, not a bare `plt.show` call (`plt-show-only`).
- [ ] Colors use named palettes (`oc.*`, `tw.*`, `dc.*`, `md.*`, `ad.*`, `cu.*`, `pr.*`) rather than raw hex.
- [ ] Font sizes / weights / line widths go through `dm.fs(n)` / `dm.fw(n)` / `dm.lw(n)` instead of literals.

### Quality (Recommend)
- [ ] Axis labels are set.
- [ ] Legend is properly placed when multiple series exist.
- [ ] Code is well-commented.
- [ ] Data construction is cleanly separated from plotting logic.

## Reference resources
- `dartwork-mpl://guide/policy` — full 0.4 policy.
- `dartwork-mpl://guide/recipes` — canonical 0.4 invocations per intent.
- `dartwork-mpl://guide/anti-patterns` — the lint engine source.

## Output Format
For each issue found:
1. **Issue**: what's wrong (cite the lint rule id when applicable).
2. **Location**: line number or code snippet.
3. **Fix**: corrected code.

Then provide the complete corrected script. Confirm by passing it through `lint_dartwork_mpl_code(...)`; the report should be clean of `[CRITICAL]` findings.
"""
