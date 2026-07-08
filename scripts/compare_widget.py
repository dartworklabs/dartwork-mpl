r"""Shared renderer for the docs before/after comparison widget.

History: the docs used to show vanilla-vs-dartwork comparisons with a
drag-to-wipe slider. That widget was chronically fragile — it guessed the
``_static/`` path at runtime from ``window.location.pathname`` (so any
unexpected URL shape 404'd the images), loaded the SVGs asynchronously
with no fallback (so a slow/missing load collapsed the container and the
two images' text overlapped), and computed a ``clip-path`` boundary on
every pointer move.

This module replaces all of that with a **CSS-only in-place toggle**: a
segmented "Dartwork / Vanilla" pill that swaps which full-size image is
shown via the ``:checked`` pseudo-class on hidden radio inputs. There is
**no JavaScript**, **no runtime path guessing** (each caller passes the
exact static relative path), and **no clip math**. Images are plain
``<img>`` elements (isolated — no inline-SVG id collisions), so a missing
image degrades to one broken pane instead of a collapsed widget. Toggling
in place (same position, same size) also makes the styling difference
easier to read than a half-width side-by-side.

The output is a self-contained, id-scoped HTML snippet that sphinx pages
embed via ``{raw} html`` ``:file:``.
"""

from __future__ import annotations

import html

_TEMPLATE = """<style>
  /* before/after toggle — {alt} (id-scoped to #{wid}) */
  #{wid} {{
    max-width: 720px;
    margin: 1.6em auto;
    font-family: var(--dm-f-sys, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
  }}
  #{wid} .dmc-radio {{
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
  }}
  #{wid} .dmc-tabs {{
    display: inline-flex;
    gap: 3px;
    padding: 3px;
    border-radius: var(--dm-radius-full, 999px);
    background: var(--dm-i-track, #ece9e3);
    margin: 0 0 0.7em;
  }}
  #{wid} .dmc-tab {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    padding: 5px 15px;
    border-radius: var(--dm-radius-full, 999px);
    font-size: var(--dm-type-label-size, 0.8em);
    font-weight: 600;
    letter-spacing: 0;
    color: var(--dm-text-muted, #6b6862);
    transition: background 0.15s, color 0.15s, box-shadow 0.15s;
    user-select: none;
    -webkit-user-select: none;
  }}
  #{wid} .dmc-tab::before {{
    content: "";
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex: 0 0 auto;
  }}
  #{wid} .dmc-tab-after::before {{
    background: var(--dm-i-active-line, #12a594);
  }}
  #{wid} .dmc-tab-before::before {{
    background: var(--dm-danger-9, #e5484d);
  }}
  #{wid} .dmc-stage {{
    position: relative;
    border-radius: var(--dm-radius-4, 8px);
    border: 1px solid var(--dm-border-faint, #e4e2dd);
    background: var(--dm-bg-panel, #fbfaf7);
    overflow: hidden;
  }}
  /* Graceful default: the "after" pane shows even if :checked is unsupported. */
  #{wid} .dmc-pane {{
    margin: 0;
  }}
  #{wid} .dmc-pane-after {{
    display: block;
  }}
  #{wid} .dmc-pane-before {{
    display: none;
  }}
  #{wid} .dmc-pane img {{
    display: block;
    width: 100%;
    height: auto;
  }}
  #{wid}-b:checked ~ .dmc-stage .dmc-pane-after {{
    display: none;
  }}
  #{wid}-b:checked ~ .dmc-stage .dmc-pane-before {{
    display: block;
    animation: dmcIn 0.16s ease;
  }}
  #{wid}-a:checked ~ .dmc-stage .dmc-pane-after {{
    display: block;
    animation: dmcIn 0.16s ease;
  }}
  #{wid} .dmc-tab-after {{
    background: var(--dm-i-thumb, #fff);
    color: var(--dm-text-strong, #1a1a1a);
    box-shadow: var(--dm-shadow-1, 0 1px 3px rgba(0, 0, 0, 0.18));
  }}
  #{wid}-b:checked ~ .dmc-tabs .dmc-tab-after {{
    background: transparent;
    color: var(--dm-text-muted, #6b6862);
    box-shadow: none;
  }}
  #{wid}-b:checked ~ .dmc-tabs .dmc-tab-before {{
    background: var(--dm-i-thumb, #fff);
    color: var(--dm-text-strong, #1a1a1a);
    box-shadow: var(--dm-shadow-1, 0 1px 3px rgba(0, 0, 0, 0.18));
  }}
  @keyframes dmcIn {{
    from {{
      opacity: 0.4;
    }}
    to {{
      opacity: 1;
    }}
  }}
</style>

<div id="{wid}">
  <input class="dmc-radio" type="radio" name="{wid}" id="{wid}-a" checked>
  <input class="dmc-radio" type="radio" name="{wid}" id="{wid}-b">
  <div class="dmc-tabs dm-tabs" role="tablist" aria-label="{alt} — compare">
    <label class="dmc-tab dm-tab dmc-tab-after" for="{wid}-a">{after_label}</label>
    <label class="dmc-tab dm-tab dmc-tab-before" for="{wid}-b">{before_label}</label>
  </div>
  <div class="dmc-stage">
    <figure class="dmc-pane dmc-pane-after">
      <img src="{after_src}" alt="{alt} — {after_label}" loading="lazy">
    </figure>
    <figure class="dmc-pane dmc-pane-before">
      <img src="{before_src}" alt="{alt} — {before_label}" loading="lazy">
    </figure>
  </div>
</div>
"""


def render_compare(
    wid: str,
    *,
    after_src: str,
    before_src: str,
    after_label: str = "Dartwork",
    before_label: str = "Vanilla",
    alt: str = "",
) -> str:
    """Return a self-contained before/after toggle snippet.

    Parameters
    ----------
    wid:
        Unique id stem (scopes all CSS + the radio ``name`` so multiple
        widgets can coexist on one page). Use only ``[a-z0-9-]``.
    after_src, before_src:
        Exact static relative paths (from the *embedding page*) to the
        "after" (dartwork) and "before" (vanilla) images. No runtime
        path guessing — the caller knows the page depth.
    after_label, before_label:
        Pill labels. Default "Dartwork" / "Vanilla".
    alt:
        Human description used for ``alt`` text and the tablist label.
    """
    return _TEMPLATE.format(
        wid=wid,
        after_src=html.escape(after_src, quote=True),
        before_src=html.escape(before_src, quote=True),
        after_label=html.escape(after_label),
        before_label=html.escape(before_label),
        alt=html.escape(alt),
    )
