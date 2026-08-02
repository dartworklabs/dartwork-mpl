"""Bootstrap the generated-color build without importing runtime output."""

import importlib
import sys
from collections.abc import Callable, Sequence
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import cast

_COLOR_BUILD_MODULE = "dartwork_mpl._colors._build"


def is_color_build_invocation(
    original_argv: Sequence[str] | None = None,
    active_argv: Sequence[str] | None = None,
) -> bool:
    """Return whether Python is resolving the documented color build module.

    Parameters
    ----------
    original_argv : Sequence[str] | None, optional
        Interpreter arguments before ``-m`` processing. Defaults to
        :data:`sys.orig_argv`.
    active_argv : Sequence[str] | None, optional
        Current process arguments. Defaults to :data:`sys.argv`.

    Returns
    -------
    bool
        ``True`` only while Python is importing parent packages for the exact
        ``python -m dartwork_mpl._colors._build`` entry point.
    """
    original = tuple(
        original_argv
        if original_argv is not None
        else getattr(sys, "orig_argv", ())
    )
    active = tuple(active_argv if active_argv is not None else sys.argv)
    if not active or active[0] != "-m":
        return False
    try:
        module_flag = original.index("-m")
    except ValueError:
        return False
    module_index = module_flag + 1
    return (
        module_index < len(original)
        and original[module_index] == _COLOR_BUILD_MODULE
    )


def run_color_build_if_requested(package_name: str, package_file: str) -> None:
    """Run the color coordinator before normal package initialization.

    Parameters
    ----------
    package_name : str
        Name of the parent package currently being initialized.
    package_file : str
        Filesystem path of that package's ``__init__.py``.

    Raises
    ------
    RuntimeError
        If Python cannot construct the source package shell.
    SystemExit
        With the color coordinator's documented CLI exit status when the
        exact module-mode build was requested.
    """
    if not is_color_build_invocation():
        return

    package = sys.modules[package_name]
    colors_name = f"{package_name}._colors"
    colors_path = Path(package_file).with_name("_colors")
    colors_init = colors_path / "__init__.py"
    colors_spec = spec_from_file_location(
        colors_name, colors_init, submodule_search_locations=[str(colors_path)]
    )
    if colors_spec is None:
        raise RuntimeError("cannot create the source color-package spec")
    colors_package = module_from_spec(colors_spec)
    sys.modules[colors_name] = colors_package
    vars(package)["_colors"] = colors_package

    build_module = importlib.import_module(_COLOR_BUILD_MODULE)
    build_main = cast(Callable[[], int], vars(build_module)["main"])
    raise SystemExit(build_main())
