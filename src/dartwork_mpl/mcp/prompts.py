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
## Mandatory Rules
1. **Import**: `import matplotlib.pyplot as plt` and `import dartwork_mpl as dm`.
2. **Figure creation**: Use native matplotlib paired with `dm.figsize`:
   `fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))`.
   `dm.figsize(width, aspect)` accepts `width` as a unit string (`"13cm"`, `"5in"`, `"170mm"`, `"24pt"`) or a `Length` value (`dm.cm(13)`, `dm.col1`, `dm.col2`). Bare `int` / `float` are rejected (lint id `raw-width-number`). The second argument picks the height in one of four equivalent forms — an aspect token in `square / portrait / standard / golden / wide / cinema`, a positive float ratio (`0.6`), a unit-string height (`"12cm"`), or a `Length` height (`dm.cm(12)`).
3. **No raw `figsize=(w, h)` tuple** and no `dpi=` argument on `plt.subplots` / `plt.figure` (lint ids `figsize-direct`, `dpi-arg`). Always go through `dm.figsize`; dpi is governed by the active style preset.
4. **Layout**: Call `dm.simple_layout(fig)` after data is plotted. The default snaps axes content flush against figure edges; pass `margin="2%"` (or `dm.mm(2)`, `dm.cm(0.5)`) for a uniform buffer, or `ml/mr/mt/mb` for per-side overrides. Do NOT call `tight_layout` (lint id `tight-layout`). The historical `dm.auto_layout` is a deprecated alias.
5. **Style**: apply via `dm.style.use("scientific")` (or `dm.style.stack([...])` for a stack). No `plt.style.use` anywhere (lint id `plt-style-use`).
6. **Colors**: prefer named palettes — `oc.*` (Open Color), `tw.*` (Tailwind), `dc.*` (dartwork core), `md.*`, `ad.*`, `cu.*`, `pr.*`. Raw hex works but triggers a lint info.
7. **Fonts / weights / line widths**: do NOT pass literal `fontsize=` numbers. Use `dm.fs(n)` / `dm.fw(n)` / `dm.lw(n)` offsets from the active style.
8. **Save**: end the script with `dm.save_formats(fig, "name", formats=("png", "pdf"), dpi=300)` (scripts) or `dm.save_and_show(fig, "name")` (notebooks). Do not stop at `plt.show` — the rendered artifact must be persisted (lint id `plt-show-only`).
9. **Removed names**: `dm.subplots`, `dm.figure`, and the legacy width aliases (`dm.SW / MW / TW / DW / FS_* / WIDTHS`) raise `AttributeError` (lint ids `dm-subplots-removed`, `deprecated-width-token`). Use `plt.subplots(figsize=dm.figsize(...))` and `dm.col1` / `dm.col2` for academic columns.

## Style presets (composite, recommended)
Apply via `dm.style.use("scientific")` (or `dm.style.stack([...])` for a stack).

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

The skeleton intentionally wires every font size, line width, and font
weight through ``dm.fs(n)`` / ``dm.lw(n)`` / ``dm.fw(n)`` so that
swapping ``dm.style.use(...)`` to a different preset (``report``,
``presentation``, ``minimal``, ``*-kr``) rescales the figure correctly
without any other edits.

```python
import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))

# Named colors + preset-relative line width.
ax.plot(x, y, color="dc.ocean2", linewidth=dm.lw(0), label="Series A")
# `dm.lw(-1)` is the canonical hairline edge for filled markers/bars.
ax.scatter(x, y, color="dc.ocean5", edgecolor="white",
           linewidth=dm.lw(-1), s=20)

# Tick / legend / annotation text — one step below the body size.
ax.tick_params(labelsize=dm.fs(-1))
ax.legend(fontsize=dm.fs(-1))

ax.set_xlabel("...")
ax.set_ylabel("...")
# Title — one step above body, with the bolder weight step.
ax.set_title("...", fontsize=dm.fs(1), fontweight=dm.fw(1))

dm.simple_layout(fig)
dm.save_formats(fig, "output", formats=("png", "pdf"), dpi=300)
```

Generate clean, well-commented code that follows these rules strictly.
Run the result through ``lint_dartwork_mpl_code(code)`` to surface any
``[CRITICAL]`` issue, then through ``validate_generated_plot(code)``
to catch overflow / clipped text / asymmetric margins before returning
the snippet.
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
- [ ] Figure construction uses `plt.subplots(figsize=dm.figsize("<n>cm", "<aspect>"))` (or `plt.figure(figsize=dm.figsize(...))`). The legacy `dm.subplots` / `dm.figure` were REMOVED (`dm-subplots-removed`).
- [ ] No raw `figsize=(w, h)` tuple — wrap with `dm.figsize(...)` (`figsize-direct`).
- [ ] No bare `int`/`float` width passed to `dm.figsize` — use a unit string or a `Length` value (`raw-width-number`).
- [ ] No `tight_layout` call — use `dm.simple_layout(fig)` (`tight-layout`).

### Warning (Should Fix)
- [ ] No `dpi=` argument on `plt.figure` / `plt.subplots`. The active style controls dpi (`dpi-arg`).
- [ ] No `plt.style.use` — call `dm.style.use(...)` or `dm.style.stack([...])` (`plt-style-use`).
- [ ] No legacy width tokens (the SW / MW / TW / DW / FS_* / WIDTHS family on `dm`) — use `dm.figsize("<n>cm", "<aspect>")`, or `dm.col1` / `dm.col2` for academic columns (`deprecated-width-token`).
- [ ] No `cm2in`-based figsize idiom (legacy 0.3 pattern: `figsize` constructed from `dm.cm2in` calls). Use `dm.figsize("<n>cm", "<aspect>")` instead (`cm2in-figsize`).
- [ ] No mention of the retired sizing-policy slogan from 0.3 (lint id `zero-resize-mention`). dartwork-mpl uses free-form width input plus a lint consistency guard.

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
