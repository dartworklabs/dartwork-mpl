"""Generate a standalone Python script that reproduces the current figure.

The script holds the figure function and ParamModel source and the active
values. Its body (including ``from dartwork_mpl.util import save_formats``)
is user-facing output and stays byte-for-byte as it was.
"""

import inspect
import textwrap
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..params import ParamModel


def _generate_script(
    model: ParamModel,
    model_cls: type[ParamModel],
    figure_fn: Callable[..., Any],
    script_dir: Path,
) -> str:
    """Generate a standalone Python script that reproduces the figure.

    The script includes the figure function source, the ParamModel class
    source, and the current parameter values.
    """
    # Get source of the figure function and model class
    try:
        fn_source = textwrap.dedent(inspect.getsource(figure_fn))
    except (OSError, TypeError):
        fn_source = f"# Could not retrieve source for {figure_fn.__name__}"

    try:
        model_source = textwrap.dedent(inspect.getsource(model_cls))
    except (OSError, TypeError):
        model_source = f"# Could not retrieve source for {model_cls.__name__}"

    # Get the module where figure_fn is defined for imports
    fn_module = inspect.getmodule(figure_fn)
    try:
        module_source = inspect.getsource(fn_module)  # type: ignore[arg-type]
        # Extract import lines from the top of the module
        import_lines = []
        for line in module_source.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                # Skip the 'run' function import (not needed in standalone)
                if "import run" in stripped or "import run," in stripped:
                    # Keep ParamModel but drop run
                    cleaned = stripped.replace(", run", "").replace("run, ", "")
                    if "import" in cleaned and cleaned != stripped:
                        import_lines.append(cleaned)
                else:
                    import_lines.append(line)
            elif (
                stripped
                and not stripped.startswith(("#", '"""', "'''", '"'))
                and import_lines
                and not stripped.startswith(("import ", "from "))
            ):
                # Stop after the import block ends
                break
        imports_block = "\n".join(import_lines)
    except (OSError, TypeError):
        imports_block = (
            "import matplotlib.pyplot as plt\n"
            "from matplotlib.figure import Figure\n"
            "from dartwork_mpl.ui import ParamModel"
        )

    # Serialize current params
    params_dict = model.model_dump()
    params_lines = []
    for key, val in params_dict.items():
        params_lines.append(f"    {key}={val!r},")
    params_str = "\n".join(params_lines)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return f'''"""Auto-generated figure script.

Generated at: {ts}
Parameters: {model_cls.__name__}
Function:   {figure_fn.__name__}
"""

{imports_block}
from pydantic import Field

from dartwork_mpl.util import save_formats


{model_source}


{fn_source}


if __name__ == "__main__":
    params = {model_cls.__name__}(
{params_str}
    )
    fig = {figure_fn.__name__}(params)
    save_formats(fig, "{figure_fn.__name__}")
    print("Saved: {figure_fn.__name__}.[svg|png|pdf|eps]")
    plt.show()
'''
