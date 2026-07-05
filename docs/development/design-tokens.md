---
orphan: true
---

# Semantic Design Tokens

`dm.tokens` names common plotting roles: body, title, tick, label,
annotation, and emphasis text sizes; hairline, reference, trend, and
emphasis line weights; and small, default, and emphasis scatter sizes.

The font-size and line-width accessors resolve from `matplotlib`
`rcParams` at call time, so they track the active dartwork-mpl preset in
the same session. Scatter sizes are fixed semantic marker areas from the
token source of truth.

The source of truth is the versioned JSON file at
`src/dartwork_mpl/asset/tokens/semantic_tokens.json`. Use
`dm.tokens.version()` to read the schema version and
`dm.tokens.as_dict()` to export every currently resolved token.

This brings the semantic layer that previously lived only in
`valuation.theme` into dartwork-mpl as a render-neutral public API.
