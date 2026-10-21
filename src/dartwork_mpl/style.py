"""Matplotlib style management utilities.

This module provides functions and classes for loading and applying
matplotlib styles from the package's built-in style library.
"""

import contextlib
import copy
import difflib
import json
import threading
from collections.abc import Iterator
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import RcParams

__all__ = ["Style", "list_styles", "load_style_dict", "style", "style_path"]


# Module-level lock guarding global matplotlib state mutations
# (rcParams, style.use). Without this, concurrent ``dm.style.use(...)``
# calls from multiple threads can interleave rcParams updates and
# corrupt the active style.
_style_lock: threading.Lock = threading.Lock()

# Deep copies of normalized values written by the last successful preset stack.
# Contexts merge temporary preset writes and restore the immediate outer copy.
_dm_preset_values: dict[str, object] = {}


def _did_you_mean(value: str, candidates: list[str]) -> str | None:
    """Return the single closest match to ``value`` from ``candidates``
    or ``None`` if no entry is close enough.

    Wraps :func:`difflib.get_close_matches` with the cutoff dartwork-mpl
    uses everywhere a "did you mean" hint is shown (0.5 — close enough
    to catch typos like ``"sceintific"`` / ``"reort"`` but far enough
    to avoid suggesting unrelated keys for completely wrong input).
    """
    matches = difflib.get_close_matches(
        value.strip().lower(), [c.lower() for c in candidates], n=1, cutoff=0.5
    )
    if not matches:
        return None
    # Return the original-case spelling so the user sees the canonical
    # form rather than the lowercased lookup key.
    lowered = matches[0]
    for c in candidates:
        if c.lower() == lowered:
            return c
    return lowered


def _rcparam_differs(value: object, default: object) -> bool:
    """Return ``True`` when ``value != default``, treating mutable
    matplotlib rcParam types (Cyclers, lists, Paths, …) as equal when
    their ``repr`` matches.

    Matplotlib stores a handful of rcParams as mutable / wrapped
    objects (``axes.prop_cycle`` is a ``Cycler``; ``image.lut`` is an
    int — fine; ``axes.formatter.use_locale`` is a bool — fine; the
    bullets are the cycler and a couple of unhashable lists). Plain
    ``!=`` on those raises ``TypeError`` rather than returning a bool,
    so we fall through to a ``repr`` comparison for the awkward cases
    only.
    """
    try:
        result: bool = value != default
        return result
    except (TypeError, ValueError):
        return repr(value) != repr(default)


def _snapshot_user_rcparams() -> dict[str, object]:
    """Copy detectable caller edits before a preset reset.

    Prior-owned values equal to their saved preset value are residue; differing
    values are caller edits even when equal to Matplotlib's default. For other
    keys retain nondefault values. Native same-value writes are unobservable.
    """
    defaults = plt.rcParamsDefault  # type: ignore[attr-defined]
    overrides: dict[str, object] = {}
    for key in list(plt.rcParams):
        if key not in defaults:
            continue
        current = plt.rcParams[key]
        reference = _dm_preset_values.get(key, defaults[key])
        if _rcparam_differs(current, reference):
            overrides[key] = copy.deepcopy(current)
    return overrides


def _restore_untouched_user_rcparams(
    user_overrides: dict[str, object], preset_keys: set[str]
) -> None:
    """Restore user rcParams the freshly-applied preset does not own.

    Run *after* ``plt.style.use(...)``. A key is "owned by the preset"
    iff the preset *declared* it (``preset_keys``), regardless of the
    value it set — so a preset that explicitly sets a key to matplotlib's
    default value (e.g. ``axes.grid: False``) still wins over a
    pre-existing user value. Only keys the preset is genuinely silent
    about have the user value reinstated.
    """
    for key, user_value in user_overrides.items():
        if key in preset_keys or key not in plt.rcParams:
            continue
        plt.rcParams[key] = user_value


def _style_declared_keys(style_names: list[str]) -> set[str]:
    """Union of rcParam keys explicitly declared by the given style files."""
    keys: set[str] = set()
    for name in style_names:
        keys.update(load_style_dict(name).keys())
    return keys


def _resolve_rcparam_key(k: str) -> str:
    """Map a kwarg name to its canonical rcParam key.

    Accepts dotted names as-is (``legend.title_fontsize``) and the
    underscore shorthand. A naive ``k.replace("_", ".")`` breaks for
    rcParams whose canonical name itself contains an underscore
    (``legend.title_fontsize`` -> ``legend.title.fontsize``, invalid),
    so after the dotted-name and full-replace attempts we fall back to
    matching against the live rcParam whose dotted form, with dots
    turned to underscores, equals ``k``. Returns ``k`` unchanged when
    nothing matches, letting the downstream update raise matplotlib's
    standard "not a valid rc parameter" error.
    """
    if k in plt.rcParams:
        return k
    dotted = k.replace("_", ".")
    if dotted in plt.rcParams:
        return dotted
    for rc in plt.rcParams:
        if rc.replace(".", "_") == k:
            return rc
    return k


def style_path(name: str) -> Path:
    """
    Get the path to a style file.

    Parameters
    ----------
    name : str
        Name of the style (e.g., 'report', 'scientific').

    Returns
    -------
    Path
        Absolute path to the style file (.mplstyle).

    Raises
    ------
    TypeError
        If the style name is not a string.
    ValueError
        If the specified style name cannot be found.
    """
    if not isinstance(name, str):
        raise TypeError(f"style name must be str, got {type(name).__name__}")
    path: Path = Path(__file__).parent / f"asset/mplstyle/{name}.mplstyle"
    if not path.exists():
        available = list_styles()
        hint = _did_you_mean(name, available)
        raise ValueError(
            f"Style {name!r} not found. "
            f"Available styles: {available}."
            + (f" Did you mean {hint!r}?" if hint else "")
        )

    return path


def list_styles() -> list[str]:
    """
    Return a list of all available styles.

    Returns
    -------
    list[str]
        List of style names.
    """
    path: Path = Path(__file__).parent / "asset/mplstyle"
    return sorted([p.stem for p in path.glob("*.mplstyle")])


def _strip_mplstyle_value(raw: str) -> str:
    """Extract an mplstyle value: drop the inline comment, unwrap quotes.

    ``#`` starts a comment only outside quotes (so a quoted colour like
    ``"#1e1e1e"`` is preserved), after which a matching pair of
    surrounding quotes is removed — matching how matplotlib's own
    ``_rc_params_in_file`` normalizes the value.
    """
    quote: str | None = None
    chars: list[str] = []
    for ch in raw.strip():
        if quote is not None:
            chars.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            chars.append(ch)
        elif ch == "#":
            break
        else:
            chars.append(ch)
    value = "".join(chars).strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        value = value[1:-1]
    return value


def load_style_dict(name: str) -> dict[str, float | str]:
    """
    Read key-value pairs from an mplstyle file.

    Parameters
    ----------
    name : str
        Name of the style to load.

    Returns
    -------
    dict[str, float | str]
        Dictionary of style parameters. Values are converted to float
        where possible; otherwise they are kept as strings.

    Raises
    ------
    TypeError
        If the style name is not a string.
    ValueError
        If the named style file does not exist.
    """
    # Load key, value pair from mplstyle files.
    path: Path = style_path(name)
    style_dict: dict[str, float | str] = {}
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Split on first colon only (values may contain colons).
            if ":" not in stripped:
                continue
            key, raw_value = stripped.split(":", maxsplit=1)
            key = key.strip()

            # Strip an inline comment (``#`` outside quotes) and any
            # surrounding quotes, so quoted values like ``"#1e1e1e"``
            # round-trip to what matplotlib's own parser yields
            # (``#1e1e1e``) rather than the raw ``'"#1e1e1e"'``.
            value_str = _strip_mplstyle_value(raw_value)
            if not value_str:
                continue

            try:
                value_float: float = float(value_str)
                style_dict[key] = value_float
            except ValueError:
                style_dict[key] = value_str

    return style_dict


class Style:
    """
    Class for managing and applying multiple matplotlib styles.

    This class provides functionality for loading style presets and
    stacking multiple styles sequentially.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> dm.style.use("scientific")  # Apply a single preset
    >>> dm.style.stack(["base", "lang-kr"])  # Stack multiple styles
    """

    def __init__(self) -> None:
        """Initialize the Style instance and load presets."""
        self.presets: dict[str, list[str]] = {}
        # Load presets
        self.load_presets()

    @staticmethod
    def presets_path() -> Path:
        """
        Get the path to the presets configuration file (presets.json).

        Returns
        -------
        Path
            Path to the presets.json file containing combined style presets.
        """
        return Path(__file__).parent / "asset/mplstyle/presets.json"

    def load_presets(self) -> None:
        """
        Load style presets from the JSON file.

        Reads presets.json and stores the configuration in the instance's
        presets attribute.
        """
        with open(self.presets_path()) as f:
            self.presets = json.load(f)

    def _unknown_preset_message(self, name: str) -> str:
        """Build the actionable message used by every "preset not found"
        error site in this class.

        Lists every preset the caller could have used and, when the input
        is a near-miss for one of them, appends a single ``did you mean``
        hint. Matches the format used by :func:`style_path` and
        :func:`dartwork_mpl.icon.icon_font_path` so the three "missing
        style/preset/icon" errors all read the same way.
        """
        available = sorted(self.presets)
        hint = _did_you_mean(name, available)
        return f"Preset {name!r} not found. Available presets: {available}." + (
            f" Did you mean {hint!r}?" if hint else ""
        )

    @staticmethod
    def stack(style_names: list[str]) -> None:
        """
        Stack multiple styles in order.

        Applies multiple style files sequentially. Later styles override
        values set by earlier ones for the same keys. Detectable caller edits
        survive on incoming-silent keys; unchanged prior preset values reset.
        Preset-produced mutable values are copied before caller overrides.

        Parameters
        ----------
        style_names : list[str]
            List of style names to apply. Styles are applied in order,
            with later entries taking precedence.

        Examples
        --------
        >>> import dartwork_mpl as dm
        >>> dm.style.stack(["base", "font-scientific", "lang-kr"])
        """
        from .font import ensure_loaded as ensure_fonts_loaded

        # Ensure fonts are registered before Matplotlib tries to resolve
        # them (v5 colormaps register eagerly at import time).
        ensure_fonts_loaded()

        # Keys the incoming preset explicitly declares — parsed from the
        # style files, so "does the preset own this key?" is answered by
        # declaration, not by comparing values against the default.
        incoming_keys = _style_declared_keys(style_names)

        # Serialize global rcParams + style application across threads.
        with _style_lock:
            user_overrides = _snapshot_user_rcparams()
            plt.rcParams.update(plt.rcParamsDefault)  # type: ignore[attr-defined]
            plt.style.use(
                [style_path(style_name) for style_name in style_names]
            )
            # Capture normalized preset values before caller overrides.
            preset_values = {
                key: copy.deepcopy(plt.rcParams[key]) for key in incoming_keys
            }
            _restore_untouched_user_rcparams(user_overrides, incoming_keys)
            _dm_preset_values.clear()
            _dm_preset_values.update(preset_values)

            # Locale-aware semantic tokens (dc.pos/neg/ref/hl) applied at the
            # choke point use() funnels through, so direct stack() callers and
            # use() both get locale semantics. KR is detected from the STYLE
            # names (they carry "lang-kr" for Korean presets). Under the lock
            # for the same reason the rcParams mutation above is.
            from ._colors._semantic import apply_semantic

            is_kr = any(
                "lang-kr" in nm or nm.endswith("-kr") for nm in style_names
            )
            apply_semantic("kr" if is_kr else "default")

    def use(self, preset_name: str | list[str], **kwargs: float | str) -> None:
        """
        Apply a preset style configuration or a list of presets.

        This is the recommended way to apply styles in this module.
        Presets are pre-optimized combinations of styles for specific use cases.
        Resolve the complete request and validate overrides in isolated rcParams
        before font loading or changes to live style, semantics or bookkeeping.
        Successful requests retain the usual preset and caller-override order.
        Detectable native edits survive when the incoming preset is silent;
        incoming declarations win and current kwargs apply last. A native
        same-value rewrite is indistinguishable from unchanged preset residue;
        pass that override with or after the later switch. Explicit kwargs are
        known caller intent, including when equal to a preset value.

        Parameters
        ----------
        preset_name : str or list of str
            Name of the preset to apply. Available presets:
            - "scientific": Academic papers (default English)
            - "report": Documents, reports, and dashboards
            - "minimal": Tufte-style with minimal lines and ticks
            - "presentation": Slide presentations
            - "poster": Conference posters and large displays
            - "web": Web pages and documentation
            - "dark": Dark background theme
            - "scientific-kr": Academic papers (Korean fonts)
            - "report-kr": Reports and dashboards (Korean fonts)
            - "minimal-kr": Minimal style (Korean fonts)
            - "presentation-kr": Presentations (Korean fonts)
            - "poster-kr": Conference posters (Korean fonts)
            - "web-kr": Web pages (Korean fonts)
            - "dark-kr": Dark theme (Korean fonts)
        **kwargs : float | str
            Additional rcParams to override the preset defaults (e.g.,
            font_size=12). Both underscore (font_size) and dot (font.size)
            notation are supported.

        Raises
        ------
        TypeError
            If a preset name or list member is not a string.
        KeyError
            If the preset name is unknown or an override key is invalid.
        ValueError
            If an override value fails Matplotlib's rcParam validation. Rejected
            requests leave the active style and semantic tokens unchanged.

        Examples
        --------
        >>> import dartwork_mpl as dm
        >>> dm.style.use("scientific")
        >>> dm.style.use("presentation-kr", font_size=16)
        >>> dm.style.use(["scientific", "dark"])  # Stack multiple presets
        """
        # Reject name types before string suggestions or any live mutation.
        names = preset_name if isinstance(preset_name, list) else [preset_name]
        for name in names:
            if not isinstance(name, str):
                raise TypeError(
                    f"preset name must be str, got {type(name).__name__}"
                )
        if isinstance(preset_name, list):
            # Stack multiple presets in order
            style_list = []
            for name in preset_name:
                if name not in self.presets:
                    raise KeyError(self._unknown_preset_message(name))
                style_list.extend(self.presets[name])
        else:
            # Single preset
            if preset_name not in self.presets:
                raise KeyError(self._unknown_preset_message(preset_name))
            style_list = self.presets[preset_name]

        # Resolve aliases before validation so the last canonical-key value wins.
        # Keep normalized values: validating a supported one-shot iterable twice
        # would exhaust it before the live update.
        overrides = {_resolve_rcparam_key(k): v for k, v in kwargs.items()}
        validated_overrides = RcParams(overrides)

        self.stack(style_list)
        if kwargs:
            with _style_lock:
                plt.rcParams.update(validated_overrides)
                # Explicit kwargs are known caller intent, even at equal values.
                for key in validated_overrides:
                    _dm_preset_values.pop(key, None)

    @contextlib.contextmanager
    def context(
        self, preset_name: str, **kwargs: float | str
    ) -> Iterator[None]:
        """
        Temporarily apply a style, restoring rcParams, semantics and ownership.

        Body use() calls, exceptions and nested scopes restore the immediate
        outer tracking at exit. Preset-only normalized values are recorded before
        kwargs; inherited keys remain tracked. Non-string names raise TypeError
        before mutation; unknown strings retain KeyError suggestions.

        Parameters
        ----------
        preset_name : str
            Name of the preset to apply.
        **kwargs : float | str
            Additional rcParams to override.

        Examples
        --------
        >>> with dm.style.context("dark"):
        ...     plt.plot([1, 2, 3])

        Notes
        -----
        Not thread-safe: the underlying ``plt.rcParams`` mutation is
        process-global, and holding a lock across the ``yield`` would
        deadlock any body code that calls ``style.use``. Apply styles
        from one thread (matplotlib itself is not thread-safe for
        concurrent rcParams mutation).
        """
        if not isinstance(preset_name, str):
            raise TypeError(
                f"preset name must be str, got {type(preset_name).__name__}"
            )
        if preset_name not in self.presets:
            raise KeyError(self._unknown_preset_message(preset_name))

        names = self.presets[preset_name]
        style_list = [style_path(name) for name in names]
        incoming_keys = _style_declared_keys(names)
        overrides = RcParams(
            {_resolve_rcparam_key(k): v for k, v in kwargs.items()}
        )
        saved_ownership = copy.deepcopy(_dm_preset_values)

        import matplotlib.colors as mcolors

        from ._colors._semantic import SEMANTIC_TOKEN_NAMES, apply_semantic

        mapping = mcolors.get_named_colors_mapping()
        saved = {t: mapping.get(t) for t in SEMANTIC_TOKEN_NAMES}
        is_kr = preset_name.endswith("-kr") or any(
            "lang-kr" in s for s in self.presets[preset_name]
        )
        try:
            with plt.style.context(style_list):
                # Retain inherited silent-key ownership; snapshot before kwargs.
                with _style_lock:
                    _dm_preset_values.update(
                        {
                            key: copy.deepcopy(plt.rcParams[key])
                            for key in incoming_keys
                        }
                    )
                    plt.rcParams.update(overrides)
                    for key in overrides:
                        _dm_preset_values.pop(key, None)
                apply_semantic("kr" if is_kr else "default")
                yield
        finally:
            with _style_lock:
                _dm_preset_values.clear()
                _dm_preset_values.update(saved_ownership)
            for token, value in saved.items():
                if value is None:
                    mapping.pop(token, None)
                else:
                    mapping[token] = value

    def presets_dict(self) -> dict[str, list[str]]:
        """
        Return all available presets as a dictionary.

        Returns
        -------
        dict[str, list[str]]
            Dictionary mapping preset names (keys) to their constituent
            style lists (values).
        """
        return dict(self.presets.items())


style: Style = Style()
