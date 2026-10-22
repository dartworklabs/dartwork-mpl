"""The names of the viewer's two fixed state files, the one place they are spelled.

Imports nothing, so the legacy preset helpers (``ui._config``) can name the
presets file on a base install without the ``ui`` extra. Surface (through the
``state`` package): ``StateFile``.
"""

from enum import Enum


class StateFile(Enum):
    """A fixed state file under the script root; the value is its file name (a file-format contract)."""

    CONFIG = ".dartwork_ui_config.json"
    PRESETS = ".dartwork_ui_presets.json"
