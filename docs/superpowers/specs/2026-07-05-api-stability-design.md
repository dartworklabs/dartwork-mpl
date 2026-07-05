# API stability: soft-deprecation cycle + public-API contract — Design (P4)

> Program umbrella #411, pillar EO4. Advisory/design by orchestrator; implementation by codex.

## Problem

dartwork-mpl public names go straight from *present* → *hard-removed*: a removed name lives in
`_REMOVED_NAMES: dict[name → (version, hint)]` and the module `__getattr__` raises `AttributeError`
with a migration hint. There is **no soft-deprecation window** — a name that still works but warns.
0.4/0.5 hard-removed dozens of names (`SW`/`MW`/`subplots`/`auto_layout`/…). For a professional,
semver-disciplined library, the missing piece is a **deprecate-then-remove cycle** plus a written
public-API contract. There is also no marker distinguishing *stable* from *experimental* surface.

## Design (additive; extends the existing `_REMOVED_NAMES` + lint-hint infra)

1. **Soft-deprecation registry** `_DEPRECATED_NAMES: dict[str, _Deprecation]` in `__init__.py`, where
   `_Deprecation = NamedTuple(target, since, removed_in, hint)`. The module `__getattr__` gains a
   branch (before the `_REMOVED_NAMES` branch): a deprecated name emits `DeprecationWarning`
   (since/removed_in/hint) and **returns the aliased target** — so it still works. Ships **empty**:
   forward infrastructure so future removals are graceful.

2. **Experimental marker** `EXPERIMENTAL: frozenset[str]` (exported), naming provisional public
   surfaces that may change in a minor release without a full deprecation cycle. Seed with the
   interactive UI (`"ui"`) — the clearest provisional surface. Documentation-level only (no runtime
   warning, to stay conservative).

3. **Public-API contract** `docs/development/api-stability.md`: stable-core = `__all__` \ `EXPERIMENTAL`
   (backwards-compatible within a major version, changes follow the cycle); experimental = may
   change in a minor; the deprecation cycle (deprecate ≥ 2 minor releases in `_DEPRECATED_NAMES`
   before moving to `_REMOVED_NAMES`); the three registries' roles (`__all__` advertised /
   `_DEPRECATED_NAMES` soft-warns-still-works / `_REMOVED_NAMES` hard-raises); how to add/deprecate/
   remove a public name. Orphan page (no toctree edit — another session may own the nav).

4. **Contract test** `tests/test_api_stability.py`:
   - `_DEPRECATED_NAMES` ∩ `_REMOVED_NAMES` = ∅.
   - no `_DEPRECATED_NAMES` key is advertised in `__all__`.
   - every `__all__` name resolves via `getattr(dm, ·)`.
   - every `__all__` name that resolves to a function/class has a non-empty docstring (API-quality
     gate; skip modules/constants/instances).
   - every `EXPERIMENTAL` name is a reachable attribute.
   - the soft-deprecation mechanism works: `monkeypatch.setitem` a fake `_DEPRECATED_NAMES` entry
     aliasing a real name, assert `pytest.warns(DeprecationWarning)` on access AND that the return
     is the aliased object.

## Constraints / non-goals

- Do NOT touch `tests/test_deprecation_registry_parity.py` (its parity contract for *removed* names
  must keep passing), the prompt corpus, docs/_static, docs/design_system, docs/philosophy.
- No reclassification of the existing surface beyond seeding `EXPERIMENTAL = {"ui"}` (if `ui` is a
  reachable public attr; else ship empty and note it). The durable value is the mechanism + contract.
- No runtime `FutureWarning` on experimental use (conservative; documentation signal only).

## Acceptance

- `_DEPRECATED_NAMES` (empty) + `_Deprecation` + `__getattr__` branch + `EXPERIMENTAL` added; `__all__`
  updated with `EXPERIMENTAL`. New test green; existing deprecation tests unaffected. Contract doc
  builds (`-W`). ruff + mypy clean. Full suite green.
