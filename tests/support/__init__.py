"""Shared, non-collected test helpers for ``tests/`` and the slices' ``tests/`` (ADR 0005).

Helpers here observe Matplotlib through its own canvas and public getters; they
never call the production geometry helpers they help to test.
"""
