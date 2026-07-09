# Typography principles — jobs, gates, and the fallback chain as a product

Date: 2026-07-10 · Status: approved direction (user: "릴리즈 빼고 다해" —
fill the D1 Typography-rationale placeholder with a principled font system)
· Scope: dartwork-mpl bundled fonts + presets + docs · Breaking: allowed
(zero-user window continues).

## 1. Problem

The font side ships 206 files / 16 families with real infrastructure
(auto-registration, `fs/fw` offsets, preset fallback chains, the D2
explorer) but **no stated logic**: no inclusion criteria, no measured
gates, no per-family job, and at least one measurable defect. Measured
matrix (fontTools, 2026-07-10; xh = x-height/UPM, math = chart-glyph
coverage of − × ± → ° μ σ Δ, tnum = tabular numerals):

| family | weights (OS/2) | tnum | math | 한글 | xh | license |
|---|---|---|--:|---|--:|---|
| Roboto | 250·300·400·500·700·900 | y | 7/8 | - | .528 | Apache-2.0 |
| Inter / Inter Display | 100–900 ×9 | y | 8/8 | - | .546/.516 | OFL |
| IBM Plex Sans | 100–700 ×7 | **-** | 8/8 | - | .525 | OFL |
| Source Sans 3 | 200–900 ×7 | **-** | 8/8 | - | .500 | OFL |
| Noto Sans (+width variants, 54 files) | 100–900 ×9 | y | 7/8 | - | .553 | OFL |
| Pretendard | 100–900 ×9 | y | 8/8 | y | .530 | OFL |
| Paperlogy | 250–900 ×8 | - | 5/8 | y | .574 | OFL |
| Noto Sans CJK KR | 400 | - | 3/8 | y | .543 | OFL |
| Noto Sans Math / Symbols / Symbols 2 | 400 | - | 8·4·3/8 | - | .536 | OFL |
| **JetBrains Mono** | **100·240·336·400·436·472·558·800** | mono | 8/8 | - | .550 | OFL |
| IBM Plex Mono | 100–700 ×7 | mono | 5/8 (grk 0) | - | .516 | OFL |
| Roboto Mono | 100·300·400·500·700 | mono | 7/8 | - | .528 | OFL |
| Source Code Pro | 200–900 ×7 | mono | 8/8 | - | .500 | OFL |

Concrete findings:

1. **JetBrains Mono is defective**: bundled files carry non-standard OS/2
   weight classes (240/336/436/472/558) — bad instances; upstream v2.304
   statics are a clean 100–800 grid (verified). This breaks the `dm.fw()`
   100-step ladder and surfaced as odd numbers in the D2 explorer.
2. **Roboto Thin = 250** — a known upstream quirk (kept, documented).
3. **tnum is absent from IBM Plex Sans and Source Sans 3** — numeric axes
   set in them wobble; nothing tells the user.
4. **No family has a stated job** — five Latin sans faces with overlapping
   plausible roles; the fallback chain (Roboto → Inter → Paperlogy → Noto
   CJK KR → Pretendard → Math → Symbols → Symbols 2) exists only as an
   mplstyle line, untested and unexplained.
5. Docs counts drifted for months (204 vs 206 vs 207) until D2 pinned them
   — because there was no registry SSOT to render from.

## 2. Decision — four axioms (mirror of color Model B)

```
T1 (job)     Every bundled family has exactly ONE documented job. A family
             whose job another family already does better is trimmed.
T2 (gates)   Inclusion is gated by measurements, in CI:
             (a) OS/2 weights on the {100..900, step 100} grid
                 (documented upstream quirks excepted by name);
             (b) numeric-axes recommendation requires tnum OR monospace;
             (c) chart-glyph set (− × ± → ° μ σ Δ) resolves within the
                 family or the preset fallback chain;
             (d) license ∈ {OFL-1.1, Apache-2.0}, recorded per family;
             (e) declared Hangul flag == cmap truth.
T3 (roles)   Docs and presets speak in ROLES — body · display · kr-body ·
             mono · fallback-tail — each mapping to one default family plus
             documented alternates. fw()/fs() are the only sizing idioms.
T4 (chain)   The fallback chain is a designed product: for every chart
             glyph the first-resolving family is pinned by test, and the
             chain's order is explained in the rationale.
```

## 3. Jobs table + exceptions ledger

Roles: **body** Roboto (default; alternates Inter·IBM Plex Sans·Source Sans
3·Noto Sans) · **display** Inter Display · **kr-body** Paperlogy (alternates
Pretendard·Noto Sans CJK KR) · **mono** JetBrains Mono (alternates IBM Plex
Mono·Roboto Mono·Source Code Pro — each pairs with its sans sibling) ·
**fallback-tail** Noto Sans Math → Symbols → Symbols 2.

| asset | violation | disposition |
|---|---|---|
| JetBrains Mono 16 files | non-grid OS/2 weights (bad instances) | **replace with upstream v2.304 official statics** (OFL originals — no RFN issue) |
| Roboto Thin 250 | off-grid weight | **keep, named exception** (upstream quirk; documented in registry) |
| IBM Plex Sans, Source Sans 3 | no tnum | **keep** — job = editorial alternates; registry flags `numeric_axes: false`, docs matrix says so |
| IBM Plex Mono greek 0 | coverage gap | **keep** — mono job is code, not labels; flagged in registry |
| Noto Sans width variants (54 files) | bulk | **keep** — condensed widths are the long-tick-label job; documented |
| every family | no stated job | **jobs table above becomes code** (registry) |

Trims: none forced — every family has a distinct job. The principled fix is
the registry + gates, not deletion.

## 4. Deliverables

- **T1 (lib truth)**: `dartwork_mpl.font` grows a `FONTS` registry
  (family → role, job one-liner, weights, italic, tnum/mono, chart-glyph
  coverage, hangul, license, quirk notes) — measured fields derived from
  the bundled files at build/test time, curated fields (role/job) in code;
  new `tests/test_font_invariants.py` enforcing T2(a–e) + T4 chain pins;
  JetBrains assets replaced; D2 explorer + `css_font_face_name` consumers
  re-verified (weight segments become the standard grid).
- **T2 (docs truth)**: the D1 "Typography rationale (placeholder)" section
  is replaced with the real thing — the axioms, the measured matrix
  (builder-rendered from the registry), the jobs table, the fallback-chain
  anatomy; `fonts/families.md` reorganized around roles; explorer copy
  unchanged.

Release note lands with the user-driven release (excluded from this pass).
