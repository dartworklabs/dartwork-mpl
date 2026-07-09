"""Matplotlib style management utilities.

This module provides functions and classes for loading and applying
matplotlib styles from the package's built-in style library.
"""

import contextlib
import difflib
import json
import threading
from collections.abc import Iterator
from pathlib import Path

import matplotlib.pyplot as plt

__all__ = ["Style", "list_styles", "load_style_dict", "style", "style_path"]


# Module-level lock guarding global matplotlib state mutations
# (rcParams, style.use). Without this, concurrent ``dm.style.use(...)``
# calls from multiple threads can interleave rcParams updates and
# corrupt the active style.
_style_lock: threading.Lock = threading.Lock()

# Keys that any dartwork-mpl preset has declared during this process.
# Used to tell *the user's own* rcParams apart from residue left by a
# previously-applied dm preset, so switching presets performs a clean
# swap instead of leaking the prior theme (a "franken-theme").
_dm_managed_keys: set[str] = set()


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


def _snapshot_user_rcparams(exclude: set[str]) -> dict[str, object]:
    """Capture rcParams the *user* set away from matplotlib's default.

    Used by :meth:`Style.stack` to preserve caller configuration across
    the ``rcParams.update(rcParamsDefault)`` reset that style switching
    performs. Keys in ``exclude`` (those any dm preset has managed) are
    skipped: a value differing from the default there is residue from a
    previously-applied preset, not user intent, and preserving it would
    leak the prior theme into the next preset.
    """
    defaults = plt.rcParamsDefault  # type: ignore[attr-defined]
    overrides: dict[str, object] = {}
    for key in list(plt.rcParams):
        if key not in defaults or key in exclude:
            continue
        current = plt.rcParams[key]
        if _rcparam_differs(current, defaults[key]):
            overrides[key] = current
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
    ValueError
        If the specified style name cannot be found.
    """
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
        values set by earlier ones for the same keys.

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
            # Snapshot rcParams the *user* set away from matplotlib's
            # default *before* the reset below, so genuine caller config
            # (svg.hashsalt for reproducible builds, savefig.dpi, …)
            # survives the switch. Exclude keys any dm preset has managed
            # — a differing value there is residue from the previously
            # applied preset, and preserving it would leak the old theme.
            user_overrides = _snapshot_user_rcparams(exclude=_dm_managed_keys)
            plt.rcParams.update(plt.rcParamsDefault)  # type: ignore[attr-defined]
            plt.style.use(
                [style_path(style_name) for style_name in style_names]
            )
            # Reinstate user overrides for keys the incoming preset does
            # not declare; the preset wins on every key it declares.
            _restore_untouched_user_rcparams(user_overrides, incoming_keys)
            # Remember these keys so the next switch treats their values
            # as preset residue rather than user intent.
            _dm_managed_keys.update(incoming_keys)

            # Locale-aware semantic tokens (dc.pos/neg/ref/hl) applied at the
            # choke point use() funnels through, so direct stack() callers and
            # use() both get locale semantics. KR is detected from the STYLE
            # names (they carry "lang-kr" for Korean presets). Under the lock
            # for the same reason the rcParams mutation above is.
            from .colors._semantic import apply_semantic

            is_kr = any(
                "lang-kr" in nm or nm.endswith("-kr") for nm in style_names
            )
            apply_semantic("kr" if is_kr else "default")

    def use(self, preset_name: str | list[str], **kwargs: float | str) -> None:
        """
        Apply a preset style configuration or a list of presets.

        This is the recommended way to apply styles in this module.
        Presets are pre-optimized combinations of styles for specific use cases.

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
        KeyError
            If the requested preset name is not found in the presets dictionary.

        Examples
        --------
        >>> import dartwork_mpl as dm
        >>> dm.style.use("scientific")
        >>> dm.style.use("presentation-kr", font_size=16)
        >>> dm.style.use(["scientific", "dark"])  # Stack multiple presets
        """
        # Handle both single string and list of strings
        if isinstance(preset_name, list):
            # Stack multiple presets in order
            style_list = []
            for name in preset_name:
                if name not in self.presets:
                    raise KeyError(self._unknown_preset_message(name))
                style_list.extend(self.presets[name])
            self.stack(style_list)
        else:
            # Single preset
            if preset_name not in self.presets:
                raise KeyError(self._unknown_preset_message(preset_name))
            self.stack(self.presets[preset_name])

        if kwargs:
            overrides = {}
            for k, v in kwargs.items():
                overrides[_resolve_rcparam_key(k)] = v
            with _style_lock:
                plt.rcParams.update(overrides)

    @contextlib.contextmanager
    def context(
        self, preset_name: str, **kwargs: float | str
    ) -> Iterator[None]:
        """
        Context manager that temporarily applies a style within a code block.

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
        if preset_name not in self.presets:
            raise KeyError(self._unknown_preset_message(preset_name))

        style_list: list[Path | dict[str, float | str]] = [
            style_path(style_name) for style_name in self.presets[preset_name]
        ]

        if kwargs:
            overrides: dict[str, float | str] = {}
            for k, v in kwargs.items():
                overrides[_resolve_rcparam_key(k)] = v
            style_list.append(overrides)

        import matplotlib.colors as mcolors

        from .colors._semantic import SEMANTIC_TOKEN_NAMES, apply_semantic

        mapping = mcolors.get_named_colors_mapping()
        saved = {t: mapping.get(t) for t in SEMANTIC_TOKEN_NAMES}
        is_kr = preset_name.endswith("-kr") or any(
            "lang-kr" in s for s in self.presets[preset_name]
        )
        try:
            with plt.style.context(style_list):
                apply_semantic("kr" if is_kr else "default")
                yield
        finally:
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
