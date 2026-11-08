"""Shared, non-collected test helpers for ``tests/`` and the slices' ``tests/`` (ADR 0005).

Helpers here observe Matplotlib through its own canvas and public getters; they
never call the production geometry helpers they help to test. The filesystem
helpers keep tests inside their inputs: ``excluded_dirs`` walks a tree without
listing pruned directories, and ``approved_inputs`` reads only the exact files
its manifest lists below ``docs/superpowers``.
"""
