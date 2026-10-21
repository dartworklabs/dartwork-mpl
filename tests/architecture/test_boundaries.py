"""scripts/check_boundaries.py rejects each kind of boundary violation and passes legal imports (ADR 0005).

The repository check runs the real tree against the committed layout and
debt list. The other tests feed the checker small made-up packages, so each
rule is shown failing on an injected violation and passing on its legal twin.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "check_boundaries", ROOT / "scripts" / "check_boundaries.py"
)
assert _SPEC is not None and _SPEC.loader is not None
checker = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = checker  # dataclasses look their module up
_SPEC.loader.exec_module(checker)

P = "dartwork_mpl"
LAYOUT = checker.Layout(
    entry_points=frozenset({P}),
    platform=frozenset({f"{P}._geometry", f"{P}._rc"}),
    slices=frozenset({f"{P}.layout", f"{P}.units", f"{P}.style"}),
    allowed={(f"{P}.layout", f"{P}.units"): "margins are physical lengths"},
    decisions={f"{P}.layout.solve": "margin solving is pure"},
)
# A legal tree: every unit declares its surface, layout uses the allowed
# units surface and its own private module, the root wires the surfaces.
LEGAL = {
    P: "from .layout import simple_layout\nfrom .units import cm\n",
    f"{P}._geometry": '__all__ = ["extents"]\ndef extents(): ...\n',
    f"{P}._rc": '__all__ = ["lock"]\nlock = None\n',
    f"{P}.layout": (
        '__all__ = ["simple_layout"]\n'
        "from ._impl import simple_layout\n"
        "from ..units import cm\n"
        "from .._geometry import extents\n"
    ),
    f"{P}.layout._impl": "from . import solve\ndef simple_layout(): ...\n",
    f"{P}.layout.solve": "import math\ndef solve(): ...\n",
    f"{P}.units": '__all__ = ["cm"]\ndef cm(): ...\n',
    f"{P}.style": '__all__ = ["use"]\nfrom .._rc import lock\ndef use(): ...\n',
}
PACKAGES = {P, f"{P}.layout"}


def run(**changes: str) -> list[str]:
    """Violations of LEGAL with the modules in ``changes`` replaced or added.

    Keyword names are module names below the package with dots as ``__``.
    """
    code = dict(LEGAL)
    for key, source in changes.items():
        code[f"{P}.{key.replace('__', '.')}"] = source
    return checker.violations(code, PACKAGES, LAYOUT)


def test_repository_respects_its_boundaries_apart_from_listed_debt():
    """The real tree has no violation beyond DEBT, and every DEBT entry still occurs."""
    assert checker.check(ROOT / "src" / "dartwork_mpl") == []


def test_every_debt_entry_names_the_plan_step_that_removes_it():
    """A debt entry without a plan ID would never be scheduled for removal."""
    known = {"C", "K", "L", "U", "M", "T", "D"}
    for violation, step in checker.DEBT.items():
        assert step and all(
            part.strip()[0] in known for part in step.split(",")
        ), (violation, step)


def test_the_legal_tree_passes():
    """Imports inside one slice, of an allowed surface and of platform pass."""
    assert run() == []


@pytest.mark.parametrize(
    "source",
    [
        "from dartwork_mpl.units._length import parse\n",
        "import dartwork_mpl.units._length\n",
        "from ..units import _parse\n",
        "def f():\n    from dartwork_mpl.units._length import parse\n",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    from dartwork_mpl.units._length import parse\n",
    ],
)
def test_importing_another_slices_private_module_or_name_is_rejected(source):
    """Every import form reaching below another unit's surface is a private import."""
    errors = run(layout___impl=source, units___length="def parse(): ...\n")
    assert any(
        e.startswith("private import: dartwork_mpl.layout._impl")
        for e in errors
    )


def test_platform_reaching_a_slice_directly_is_rejected():
    """Platform code knows no business: importing a slice surface fails."""
    errors = run(_geometry='__all__ = ["extents"]\nfrom .units import cm\n')
    assert (
        "platform reaches slice: dartwork_mpl._geometry -> dartwork_mpl.units"
        in errors
    )


def test_platform_reaching_a_slice_through_other_platform_is_rejected():
    """The path counts: platform -> platform -> slice fails for both platform units."""
    errors = run(
        _geometry='__all__ = ["extents"]\nfrom ._rc import lock\n',
        _rc='__all__ = ["lock"]\nfrom .style import use\n',
    )
    assert (
        "platform reaches slice: dartwork_mpl._geometry -> dartwork_mpl._rc"
        " -> dartwork_mpl.style"
    ) in errors


def test_a_cycle_between_slices_is_rejected_even_through_a_lazy_import():
    """units -> layout (inside a function) closes a cycle with layout -> units."""
    errors = run(
        units='__all__ = ["cm"]\ndef cm():\n    from .layout import simple_layout\n'
    )
    assert "cycle: dartwork_mpl.layout, dartwork_mpl.units" in errors


def test_a_dependency_missing_from_the_allowed_list_is_rejected():
    """style -> units is legal in form but has no business reason listed."""
    errors = run(style='__all__ = ["use"]\nfrom .units import cm\n')
    assert (
        "undeclared dependency: dartwork_mpl.style -> dartwork_mpl.units"
        in errors
    )


def test_a_decision_module_importing_another_feature_surface_is_rejected():
    """A pure decision imports no other unit, not even an allowed surface."""
    errors = run(layout__solve="from dartwork_mpl.units import cm\n")
    assert (
        "decision import: dartwork_mpl.layout.solve -> dartwork_mpl.units"
        in errors
    )


def test_importing_the_package_root_from_a_unit_is_rejected():
    """`import dartwork_mpl as dm` inside the package reaches every slice."""
    errors = run(units='__all__ = ["cm"]\nimport dartwork_mpl as dm\n')
    assert "entry point import: dartwork_mpl.units -> dartwork_mpl" in errors


def test_a_surface_without_literal_all_and_an_unowned_module_are_rejected():
    """A unit must declare its surface; a module must belong to a unit."""
    errors = run(units="def cm(): ...\n", stray="x = 1\n")
    assert "missing __all__: dartwork_mpl.units" in errors
    assert "unowned module: dartwork_mpl.stray" in errors


def test_an_allowance_no_import_uses_is_rejected():
    """The allowed list cannot keep a reason for a dependency that is gone."""
    errors = run(
        layout='__all__ = ["simple_layout"]\nfrom ._impl import simple_layout\n'
    )
    assert (
        "unused allowance: dartwork_mpl.layout -> dartwork_mpl.units" in errors
    )


def test_listed_debt_passes_and_stale_debt_fails(tmp_path):
    """check() lets a listed violation through and reports a debt entry that no longer occurs."""
    package = tmp_path / "dartwork_mpl"
    (package / "units").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "units" / "__init__.py").write_text(
        "def cm(): ...\n", encoding="utf-8"
    )
    layout = checker.Layout(
        frozenset({P}), frozenset(), frozenset({f"{P}.units"}), {}, {}
    )
    missing = "missing __all__: dartwork_mpl.units"
    assert checker.check(package, layout, {}) == [missing]
    assert checker.check(package, layout, {missing: "C5"}) == []
    stale = "private import: dartwork_mpl.units -> dartwork_mpl.style._x"
    assert checker.check(package, layout, {missing: "C5", stale: "C2"}) == [
        f"stale debt: {stale}"
    ]


SHIM_LAYOUT = checker.Layout(
    entry_points=LAYOUT.entry_points,
    platform=LAYOUT.platform,
    slices=LAYOUT.slices,
    allowed={
        **LAYOUT.allowed,
        (f"{P}.style", f"{P}.layout"): "a preset applies the layout",
    },
    decisions=LAYOUT.decisions,
    shims={f"{P}.layout_compat": f"{P}.layout"},
)
SHIM = '__all__ = ["simple_layout"]\nfrom .layout._impl import simple_layout\n'
# style reaches layout only through the shim's surface.
SHIM_IMPORTER = (
    '__all__ = ["use"]\nfrom .layout_compat import simple_layout\n'
    "import dartwork_mpl.layout_compat\ndef use(): ...\n"
)


def run_shim(**changes: str) -> list[str]:
    """Violations of LEGAL plus a layout shim, with ``changes`` applied as in ``run``."""
    code = {**LEGAL, f"{P}.layout_compat": SHIM, f"{P}.style": SHIM_IMPORTER}
    for key, source in changes.items():
        code[f"{P}.{key.replace('__', '.')}"] = source
    return checker.violations(code, PACKAGES, SHIM_LAYOUT)


def test_a_shim_re_exporting_its_owners_private_name_passes():
    """A shim belongs to its owner, and importers may use the names its __all__ lists."""
    assert run_shim() == []


def test_importing_a_name_a_shim_does_not_list_is_a_private_import():
    """The shim's __all__ is its surface; anything else it holds stays private."""
    importer = SHIM_IMPORTER + "from .layout_compat import solve\n"
    assert run_shim(style=importer) == [
        f"private import: {P}.style -> {P}.layout_compat.solve"
    ]


def test_a_shim_importing_a_third_units_private_module_is_rejected():
    """Shim ownership covers only its owner's private code."""
    shim = SHIM + "from .units._length import parse\n"
    assert run_shim(layout_compat=shim) == [
        f"private import: {P}.layout_compat -> {P}.units._length.parse"
    ]


def test_a_shim_without_literal_all_is_rejected():
    """Without __all__ no name of the shim is public, so its importers fail too."""
    shim = "from .layout._impl import simple_layout\n"
    assert run_shim(layout_compat=shim) == [
        f"missing __all__: {P}.layout_compat",
        f"private import: {P}.style -> {P}.layout_compat.simple_layout",
    ]
