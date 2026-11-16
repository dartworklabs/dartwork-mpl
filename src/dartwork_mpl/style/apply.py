"""Apply a preset to matplotlib's rcParams, and remember which one is active."""

from __future__ import annotations

import copy
import logging
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import RcParams

from ..vocab import DefaultLocale, Locale
from . import decide, measure
from .model import Chain, Preset, override_key


@dataclass(frozen=True)
class State:
    """The last applied presets and the values their layers wrote."""

    presets: tuple[Preset, ...] = ()
    values: dict[str, object] = field(default_factory=dict[str, object])
    locale: Locale = field(default_factory=DefaultLocale)


LOG = logging.getLogger("dartwork_mpl.style")

REGISTRY = measure.registry()
# Serializes this slice's multi-key rcParams writes across threads.
LOCK = threading.Lock()
STATE = [State()]  # one slot, replaced whole


#: What a preset's locale is handed to once it is applied.
Tint = Callable[[Locale], None]


def no_tint(locale: Locale) -> None:
    """The slice alone: a preset's locale changes nothing outside it."""
    del locale


# One slot, replaced whole: the colour slice's role colours once
# ``compose.style`` has joined them in.
TINT: list[Tint] = [no_tint]


def use(request: object, overrides: dict[str, object]) -> None:
    """Clear the last preset's values, apply the request's layers, then
    ``overrides``, then tint for the preset's locale. A rejected name or
    override changes nothing."""
    chain = decide.chain(REGISTRY.parse(request))
    known = list(mpl.rcParams)
    validated = RcParams(
        {override_key(k, known): v for k, v in overrides.items()}
    )
    with LOCK:
        write(chain, validated)
        TINT[0](chain.locale)


def write(chain: Chain, overrides: RcParams) -> None:
    """The rcParams half of :func:`use`, under the caller's lock.

    rcParams start from matplotlib's defaults, except the caller's own edits
    on keys the incoming layers do not set.
    """
    edits = measure.edits(STATE[0].values)
    # Edits off a preset no longer in force (plt.rc_context restored the
    # defaults) are matplotlib's values, not the caller's.
    yours = not STATE[0].values or measure.in_force(STATE[0].values)
    plt.rcParams.update(mpl.rcParamsDefault)
    plt.style.use([measure.layer_path(layer) for layer in chain.layers])
    declared: set[str] = set()
    for layer in chain.layers:
        declared.update(measure.load_style_dict(layer))
    for key, value in edits.items():
        if key not in declared:
            plt.rcParams[measure.rc_key(key)] = value
        elif yours and key not in overrides:
            LOG.info(
                'replaced your rcParams["%s"] = %r with the preset\'s %r: '
                "the preset sets that key; pass it to dm.style.use as an "
                'override (**{"%s": ...}) to keep yours',
                key,
                value,
                plt.rcParams[measure.rc_key(key)],
                key,
            )
    values = {
        key: copy.deepcopy(plt.rcParams[measure.rc_key(key)])
        for key in declared
        if key not in overrides
    }
    plt.rcParams.update(overrides)
    STATE[0] = State(chain.presets, values, chain.locale)


@contextmanager
def context(request: object, overrides: dict[str, object]) -> Generator[None]:
    """:func:`use` for one block; rcParams, the active preset and the tint
    of its locale come back on exit."""
    saved = replace(STATE[0])
    with mpl.rc_context():  # pyright: ignore[reportUnknownMemberType]
        use(request, overrides)
        try:
            yield
        finally:
            STATE[0] = saved
            TINT[0](saved.locale)
