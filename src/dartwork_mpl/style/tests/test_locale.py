"""A style application's semantic-colour locale is decided by one parser per input.

``stack``/``use`` read the locale from the applied style names and
``context`` from the preset name plus its styles; these tests pin both rules,
their agreement on every shipped preset, and the one documented case where
they differ.
"""

import pytest

import dartwork_mpl as dm
from dartwork_mpl.style import _locale_of_preset, _locale_of_styles


@pytest.mark.parametrize(
    ("styles", "locale"),
    [
        (["base", "lang-kr"], "kr"),
        (["base", "font-web", "custom-kr"], "kr"),
        (["base", "font-web"], "default"),
        ([], "default"),
    ],
)
def test_style_stack_locale(styles: list[str], locale: str) -> None:
    """A stack is Korean when any style contains ``lang-kr`` or ends in ``-kr``."""
    assert _locale_of_styles(styles) == locale


@pytest.mark.parametrize("preset", sorted(dm.style.presets_dict()))
def test_both_rules_agree_on_every_shipped_preset(preset: str) -> None:
    """For shipped presets, ``context`` and ``use`` pick the same locale, Korean iff ``-kr``."""
    styles = dm.style.presets_dict()[preset]
    expected = "kr" if preset.endswith("-kr") else "default"

    assert _locale_of_preset(preset, styles) == expected
    assert _locale_of_styles(styles) == expected


def test_preset_rule_trusts_the_preset_name() -> None:
    """A caller-added ``*-kr`` preset without ``lang-kr`` is Korean only under ``context``."""
    styles = ["base", "font-web"]

    assert _locale_of_preset("mine-kr", styles) == "kr"
    assert _locale_of_styles(styles) == "default"
