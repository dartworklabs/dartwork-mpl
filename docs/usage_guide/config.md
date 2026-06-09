# Global Defaults — `dm.config`

`dm.config` is the process-wide singleton that holds dartwork-mpl's
behaviour toggles. Set it once near the top of your program (or in a
notebook's first cell) and every subsequent call across `dm.layout`,
`dm.io`, and friends honours the new default — no need to thread the
keyword through every call site.

**Per-call overrides always win.** Passing `simple_layout(fig,
adopt_orphan_tick_font=True)` overrides whatever you set on
`dm.config`. The singleton supplies the *fallback* only.

## What's in there

`dm.config` is a `@dataclass` with named fields. Today there are two;
more land as audit findings ship.

| Field | Default | Affects |
|---|---|---|
| `adopt_orphan_tick_font` | `True` | `simple_layout`, `save_formats`, `save_and_show` — when an axis has tick labels but no axis label, dartwork copies the *axis label* font (size + weight + family) onto the ticks so the figure reads as one designed object. Set `False` to leave tick fonts alone. |
| `warn_on_orphan_tick_adoption` | `False` | Same three call sites. When `True`, emits a one-time `UserWarning` every time the adoption mutates a figure. Useful when debugging surprise tick changes, or when running under matplotlib's `constrained_layout` where the font swap can trigger a re-layout. |

The full surface is in [`config.py`](https://github.com/dartworklabs/dartwork-mpl/blob/main/src/dartwork_mpl/config.py) — that's the SSOT, this page is the cookbook.

## Patterns

### 1. Flip a default project-wide

Set once near the top of your entry script or notebook. Every
`simple_layout` / `save_formats` / `save_and_show` call afterwards
picks it up.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

# This project prefers tick fonts left untouched.
dm.config.adopt_orphan_tick_font = False

dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot([1, 2, 3], [1, 4, 9])

dm.simple_layout(fig)          # tick fonts NOT adopted (config wins)
dm.save_formats(fig, "out", formats=("png", "svg"))
```

### 2. Scope the change to a `with` block

`dm.config.override(...)` restores the previous values on exit, even
on exception. Use this when most of your code wants the default but
one specific export needs the opposite.

```python
dm.config.adopt_orphan_tick_font = False     # default: off

with dm.config.override(adopt_orphan_tick_font=True):
    dm.simple_layout(fig)                    # adoption ON here
    dm.save_formats(fig, "press_release", formats=("pdf",))

dm.simple_layout(fig)                        # back to OFF
```

The block is exception-safe — raising inside still restores every
overridden field.

### 3. Per-call override beats config

Pass the keyword explicitly when you want to bypass `dm.config` for a
single call. Anything you pass (`True` or `False`) wins; the only
value that defers to `dm.config` is `None` (the call-site default).

```python
dm.config.adopt_orphan_tick_font = True      # project default

# Just this figure: skip adoption.
dm.simple_layout(fig, adopt_orphan_tick_font=False)
```

### 4. Debug surprise tick changes

When a tick font silently changes between two draws (a common
constrained-layout / re-layout hazard), turn the warning on. Every
adoption emits a `UserWarning` that includes the axis it touched, so
you can isolate the offender.

```python
dm.config.warn_on_orphan_tick_adoption = True

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    dm.simple_layout(fig)

for w in caught:
    print(w.message)
# UserWarning: orphan-tick font adoption mutated 2 axes ...
```

Pair with `dm.config.adopt_orphan_tick_font = False` and the warning
goes silent — confirming you've fully opted out.

### 5. Typos fail loudly

`override(...)` raises `AttributeError` for any field name that isn't
declared on `Config`. A typo can't silently shadow the singleton.

```python
try:
    with dm.config.override(adopt_orphn_tick_font=False):   # typo
        ...
except AttributeError as exc:
    print(exc)
# dm.config has no attribute(s): ['adopt_orphn_tick_font']. Known fields: ...
```

Use this to your advantage: when you suspect a stale doc, just try
the field name — if it fails, the field's gone or never existed.

## Mental model

```{mermaid}
flowchart TD
    A["<b>per-call keyword</b><br/><code>simple_layout(fig, ...)</code><br/><i>always wins</i>"]
    B["<b>dm.config field</b><br/><code>dm.config.adopt_orphan_tick_font = False</code><br/><i>project default</i>"]
    C["<b>hard-coded Config default</b><br/>(True / False)<br/><i>library default</i>"]
    A -->|"None? fall through"| B
    B -->|"no field? fall through"| C

    classDef node fill:#fcfcfd,stroke:#cdced6,stroke-width:1px,color:#1c2024,rx:6,ry:6;
    class A,B,C node;
    linkStyle 0 stroke:#60646c,stroke-width:1px;
    linkStyle 1 stroke:#60646c,stroke-width:1px;
```

The chain is **deterministic and read-only at the lower levels** —
the per-call keyword never mutates `dm.config`, and `dm.config` never
mutates the dataclass defaults.

## When to add a new field

Don't reach for `dm.config` for everything. Use it when:

- The toggle is a **bool / enum default** the user might want to flip
  for a whole project, not a per-call decision.
- There's no preset-level home for it (preset attributes are for
  *style*, `dm.config` is for *behaviour*).
- The current default is **silent** — i.e., users today have no
  knob, and one would help.

Skip it when:

- The setting belongs to a preset (`dm.style.use(...)`).
- The setting is truly call-site (file paths, individual figure
  options).

The roadmap of candidate fields is tracked at issue
[#311 (B19 — config audit)](https://github.com/dartworklabs/dartwork-mpl/issues/311).

## See also

- [Layout and Typography](layout.md) — where `adopt_orphan_tick_font`
  actually fires.
- [Save and Validation](save_export.md) — `save_formats` / `save_and_show`
  read the same field.
- `dm.dpi(n)` — the DPI ladder (preset's base `savefig.dpi` + `n × 50`)
  that pairs naturally with these defaults. With the presets now
  shipping `300` as base, `dm.dpi()` returns `300.0`, `dm.dpi(1)`
  returns `350.0`, etc.
