"""Colour fixtures for the cross-cutting colour contracts that stay in ``tests/``.

The colour slice owns these fixtures in ``src/dartwork_mpl/_colors/conftest.py``
(ADR 0005); ``tests/test_color_v6_comparison.py`` observes colours and MCP
discovery together, so it stays here and reuses them. The repository-wide
bootstrap and state isolation live in the root ``conftest.py``.
"""

from dartwork_mpl._colors.conftest import candidate_catalog, v5_ssot

__all__ = ["candidate_catalog", "v5_ssot"]
