"""Font management utilities for Matplotlib.

Registers custom fonts from the package's asset/font directory with
matplotlib's internal font manager.
"""

import threading
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from matplotlib import font_manager

__all__ = [
    "FONTS",
    "FontFamily",
    "css_font_face_name",
    "ensure_loaded",
    "font_families",
    "get_font_dir",
    "list_registered",
]

# Rough sanity floor for the bundled font set. We expect at least a
# handful of files spanning Roboto + Paperlogy + NotoSansCJK +
# NotoSansMath cores. Falling below this hints that the install is
# missing assets — likely a slim install or accidental deletion.
_EXPECTED_MIN_FONTS: int = 5

# Bundled font directory — single source, also consumed by
# ``diagnostics._fonts.plot_fonts`` (which used to rebuild the same
# path with os.path idioms).
_FONT_DIR: Path = Path(__file__).parent / "asset" / "font"
_FONT_SUFFIXES: frozenset[str] = frozenset({".ttf", ".otf"})
_BUNDLED_FONT_WEIGHT_OVERRIDES: Mapping[str, int] = MappingProxyType(
    {
        # Both files report OS/2 weight 250, which makes Matplotlib choose
        # either one for a light request according to cache/discovery order.
        "Paperlogy-1Thin.ttf": 100,
        "Paperlogy-2ExtraLight.ttf": 200,
    }
)
_CHART_GLYPHS: tuple[str, ...] = ("−", "×", "±", "→", "°", "μ", "σ", "Δ")  # noqa: RUF001
_DIGIT_ADVANCE_PROBE: str = "0123456789"
_HANGUL_SAMPLE: str = "한글"
_FIXED_WIDTH_PROBE: str = "0123456789ilW"

FontRole = Literal[
    "body", "display", "kr-body", "serif", "mono", "mono-kr", "fallback-tail"
]


@dataclass(frozen=True)
class FontFaceMeasurement:
    """Measured facts for one bundled font file."""

    file: str
    weight: int
    italic: bool
    stretch: str
    tnum_available: bool
    digit_widths_uniform: bool
    fixed_pitch: bool
    chart_glyphs: tuple[str, ...]
    hangul: bool
    license: str

    @property
    def tnum(self) -> bool:
        """Backward-compatible alias for browser tabular-numeral support."""
        return self.tnum_available


@dataclass(frozen=True)
class FontMeasurement:
    """Measured facts aggregated at matplotlib-family level."""

    family: str
    files: tuple[FontFaceMeasurement, ...]
    weights: tuple[int, ...]
    italic: bool
    tnum_available: bool
    default_digit_widths_uniform: bool
    fixed_pitch: bool
    chart_glyphs: tuple[str, ...]
    hangul: bool
    licenses: tuple[str, ...]

    @property
    def tnum(self) -> bool:
        """Backward-compatible alias for browser tabular-numeral support."""
        return self.tnum_available


@dataclass(frozen=True)
class FontFamily:
    """Curated job record for a bundled matplotlib font family."""

    name: str
    role: FontRole
    job: str
    alternates: tuple[str, ...] = ()
    quirks: tuple[str, ...] = ()
    weight_exceptions: tuple[int, ...] = ()

    @property
    def weights(self) -> tuple[int, ...]:
        return _measure(self.name).weights

    @property
    def italic(self) -> bool:
        return _measure(self.name).italic

    @property
    def tnum(self) -> bool:
        return _measure(self.name).tnum_available

    @property
    def tnum_available(self) -> bool:
        return _measure(self.name).tnum_available

    @property
    def mono(self) -> bool:
        return _measure(self.name).fixed_pitch

    @property
    def numeric_axes(self) -> bool:
        measurement = _measure(self.name)
        return (
            measurement.default_digit_widths_uniform or measurement.fixed_pitch
        )

    @property
    def chart_glyphs(self) -> tuple[str, ...]:
        return _measure(self.name).chart_glyphs

    @property
    def hangul(self) -> bool:
        return _measure(self.name).hangul

    @property
    def licenses(self) -> tuple[str, ...]:
        return _measure(self.name).licenses


def _alternates(name: str, ordered: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(family for family in ordered if family != name)


_BODY_FAMILIES: tuple[str, ...] = (
    "Roboto",
    "Inter",
    "IBM Plex Sans",
    "Source Sans 3",
    "Noto Sans",
)
_KR_BODY_FAMILIES: tuple[str, ...] = (
    "Paperlogy",
    "Pretendard",
    "Noto Sans CJK KR",
)
_SERIF_FAMILIES: tuple[str, ...] = (
    "Source Serif 4",
    "Noto Serif",
    "IBM Plex Serif",
)
_MONO_FAMILIES: tuple[str, ...] = (
    "JetBrains Mono",
    "IBM Plex Mono",
    "Roboto Mono",
    "Source Code Pro",
)
_FALLBACK_TAIL_FAMILIES: tuple[str, ...] = (
    "Noto Sans Math",
    "Noto Sans Symbols",
    "Noto Sans Symbols 2",
)

FONTS: Mapping[str, FontFamily] = MappingProxyType(
    {
        "Roboto": FontFamily(
            name="Roboto",
            role="body",
            job="Default neutral body face for chart labels, ticks, legends, and captions.",
            alternates=_alternates("Roboto", _BODY_FAMILIES),
            quirks=("Thin ships as OS/2 250 - upstream quirk.",),
            weight_exceptions=(250,),
        ),
        "Inter": FontFamily(
            name="Inter",
            role="body",
            job="Screen-native body alternate for dashboards and dense interface figures.",
            alternates=_alternates("Inter", _BODY_FAMILIES),
        ),
        "IBM Plex Sans": FontFamily(
            name="IBM Plex Sans",
            role="body",
            job="Technical editorial body alternate that pairs with IBM Plex Mono.",
            alternates=_alternates("IBM Plex Sans", _BODY_FAMILIES),
        ),
        "Source Sans 3": FontFamily(
            name="Source Sans 3",
            role="body",
            job="Humanist editorial body alternate for captions and longer annotations.",
            alternates=_alternates("Source Sans 3", _BODY_FAMILIES),
        ),
        "Noto Sans": FontFamily(
            name="Noto Sans",
            role="body",
            job="Pan-script body alternate and width-variant source for tight labels.",
            alternates=_alternates("Noto Sans", _BODY_FAMILIES),
        ),
        "Inter Display": FontFamily(
            name="Inter Display",
            role="display",
            job="Display cut for large chart titles, section heads, and poster-scale numbers.",
        ),
        "Paperlogy": FontFamily(
            name="Paperlogy",
            role="kr-body",
            job="Default Korean body face for Hangul chart titles, labels, and values.",
            alternates=_alternates("Paperlogy", _KR_BODY_FAMILIES),
            quirks=(
                "Thin and ExtraLight both ship as OS/2 250 - upstream quirk.",
            ),
            weight_exceptions=(250,),
        ),
        "Pretendard": FontFamily(
            name="Pretendard",
            role="kr-body",
            job="Modern Korean-Latin alternate for bilingual figures and interface-like charts.",
            alternates=_alternates("Pretendard", _KR_BODY_FAMILIES),
        ),
        "Noto Sans CJK KR": FontFamily(
            name="Noto Sans CJK KR",
            role="kr-body",
            job="CJK coverage fallback when Korean, Japanese, or Chinese glyph breadth matters.",
            alternates=_alternates("Noto Sans CJK KR", _KR_BODY_FAMILIES),
        ),
        "Source Serif 4": FontFamily(
            name="Source Serif 4",
            role="serif",
            job="Serif body for journal- and book-matched figures where a serif voice is wanted.",
            alternates=_alternates("Source Serif 4", _SERIF_FAMILIES),
            quirks=(
                "Opt-in family - not wired into any preset fallback chain. "
                "No Korean serif is bundled (명조): a legible Hangul serif "
                "would add several MB, so KR serif is out of scope by design.",
            ),
        ),
        "Noto Serif": FontFamily(
            name="Noto Serif",
            role="serif",
            job="Serif sibling of Noto Sans for journal-matched multilingual figures.",
            alternates=_alternates("Noto Serif", _SERIF_FAMILIES),
            quirks=(
                "Opt-in family - not wired into any preset fallback chain.",
                "Pan-script metrics are matched to Noto Sans.",
            ),
        ),
        "IBM Plex Serif": FontFamily(
            name="IBM Plex Serif",
            role="serif",
            job="Completes the Plex superfamily — serif voice that pairs with IBM Plex Sans and IBM Plex Mono.",
            alternates=_alternates("IBM Plex Serif", _SERIF_FAMILIES),
            quirks=(
                "Opt-in family - not wired into any preset fallback chain.",
            ),
        ),
        "JetBrains Mono": FontFamily(
            name="JetBrains Mono",
            role="mono",
            job="Default monospace for code, timestamps, aligned values, and dense numeric columns.",
            alternates=_alternates("JetBrains Mono", _MONO_FAMILIES),
        ),
        "IBM Plex Mono": FontFamily(
            name="IBM Plex Mono",
            role="mono",
            job="Technical monospace companion for IBM Plex Sans figures.",
            alternates=_alternates("IBM Plex Mono", _MONO_FAMILIES),
        ),
        "Roboto Mono": FontFamily(
            name="Roboto Mono",
            role="mono",
            job="Neutral monospace companion for Roboto-led charts.",
            alternates=_alternates("Roboto Mono", _MONO_FAMILIES),
            quirks=(
                "Static files have equal glyph advances but post.isFixedPitch is 0.",
            ),
        ),
        "Source Code Pro": FontFamily(
            name="Source Code Pro",
            role="mono",
            job="Adobe monospace companion for Source Sans 3 editorial figures.",
            alternates=_alternates("Source Code Pro", _MONO_FAMILIES),
        ),
        "D2Coding": FontFamily(
            name="D2Coding",
            role="mono-kr",
            job="Monospaced Hangul for code blocks and aligned Korean tables.",
        ),
        "Noto Sans Math": FontFamily(
            name="Noto Sans Math",
            role="fallback-tail",
            job="First math and operator fallback for scientific chart glyphs and mathtext.",
            alternates=_alternates("Noto Sans Math", _FALLBACK_TAIL_FAMILIES),
        ),
        "Noto Sans Symbols": FontFamily(
            name="Noto Sans Symbols",
            role="fallback-tail",
            job="Symbol fallback for arrows, signs, and miscellaneous scientific marks.",
            alternates=_alternates(
                "Noto Sans Symbols", _FALLBACK_TAIL_FAMILIES
            ),
        ),
        "Noto Sans Symbols 2": FontFamily(
            name="Noto Sans Symbols 2",
            role="fallback-tail",
            job="Final symbol fallback for dingbats, enclosed marks, and pictographic signs.",
            alternates=_alternates(
                "Noto Sans Symbols 2", _FALLBACK_TAIL_FAMILIES
            ),
        ),
    }
)


def get_font_dir() -> Path:
    """Return the resolved bundled font asset directory."""
    return _FONT_DIR.resolve()


def css_font_face_name(font_file: str | Path) -> str:
    """Return the CSS ``@font-face`` family name for a bundled font file."""
    return f"dm-{Path(font_file).stem}"


def font_families() -> Mapping[str, FontFamily]:
    """Return the curated bundled-font family registry."""
    return FONTS


def _is_bundled_font_entry(
    entry: font_manager.FontEntry, bundle_dir: Path
) -> bool:
    """Return whether a matplotlib font entry points inside the bundle."""
    try:
        fname = Path(entry.fname).resolve()
        return fname.is_relative_to(bundle_dir)
    except (OSError, ValueError):
        return False


def _bundled_font_entries() -> tuple[font_manager.FontEntry, ...]:
    ensure_loaded()
    bundle_dir = get_font_dir()
    # ``FontManager.addfont`` *appends* without dedup, so a bundled file
    # registered more than once — e.g. a direct ``_add_fonts()`` call after
    # the import-time registration — appears multiple times in ``ttflist``.
    # Measure each physical file once so per-family facts reflect the
    # bundled asset set on disk, not registration bookkeeping.
    seen: set[str] = set()
    entries: list[font_manager.FontEntry] = []
    for entry in font_manager.fontManager.ttflist:
        if not _is_bundled_font_entry(entry, bundle_dir):
            continue
        try:
            key = str(Path(entry.fname).resolve())
        except (OSError, ValueError):
            key = entry.fname
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return tuple(sorted(entries, key=lambda entry: (entry.name, entry.fname)))


def _entries_for_family(family: str) -> tuple[font_manager.FontEntry, ...]:
    entries = tuple(
        entry for entry in _bundled_font_entries() if entry.name == family
    )
    if not entries:
        raise KeyError(f"bundled font family not found: {family}")
    return entries


def _cmap_mapping(ttfont: Any) -> dict[int, str]:
    cmap: dict[int, str] = {}
    for table in ttfont["cmap"].tables:
        if table.isUnicode():
            cmap.update(table.cmap)
    return cmap


def _has_tnum_feature(ttfont: Any) -> bool:
    if "GSUB" not in ttfont:
        return False
    feature_list = getattr(ttfont["GSUB"].table, "FeatureList", None)
    if feature_list is None:
        return False
    return any(
        record.FeatureTag == "tnum" for record in feature_list.FeatureRecord
    )


def _has_uniform_digit_advances(ttfont: Any, cmap: Mapping[int, str]) -> bool:
    hmtx = ttfont["hmtx"]
    widths: list[int] = []
    for char in _DIGIT_ADVANCE_PROBE:
        glyph = cmap.get(ord(char))
        if glyph is None:
            return False
        widths.append(int(hmtx[glyph][0]))
    return len(set(widths)) == 1


def _has_fixed_width_advances(ttfont: Any, cmap: Mapping[int, str]) -> bool:
    hmtx = ttfont["hmtx"]
    widths: list[int] = []
    for char in _FIXED_WIDTH_PROBE:
        glyph = cmap.get(ord(char))
        if glyph is None:
            return False
        widths.append(int(hmtx[glyph][0]))
    return len(set(widths)) == 1


def _is_fixed_pitch(ttfont: Any, cmap: Mapping[int, str]) -> bool:
    return bool(ttfont["post"].isFixedPitch) or _has_fixed_width_advances(
        ttfont, cmap
    )


def _default_numeric_face(
    faces: list[FontFaceMeasurement],
) -> FontFaceMeasurement:
    upright = [face for face in faces if not face.italic]
    candidates = upright or faces
    normal_width = [face for face in candidates if face.stretch == "normal"]
    candidates = normal_width or candidates
    return min(candidates, key=lambda face: (abs(face.weight - 400), face.file))


def _classify_license(ttfont: Any) -> str:
    text_parts: list[str] = []
    for record in ttfont["name"].names:
        if int(record.nameID) not in {0, 13, 14}:
            continue
        try:
            text_parts.append(record.toUnicode())
        except UnicodeDecodeError:
            continue

    text = " ".join(text_parts).lower()
    if "apache" in text:
        return "Apache-2.0"
    if "open font license" in text or "ofl" in text:
        return "OFL-1.1"
    return "unknown"


@cache
def _family_codepoints(family: str) -> frozenset[int]:
    from fontTools.ttLib import TTFont

    codepoints: set[int] = set()
    for entry in _entries_for_family(family):
        ttfont: Any = TTFont(str(entry.fname), lazy=True)
        try:
            codepoints.update(_cmap_mapping(ttfont))
        finally:
            ttfont.close()
    return frozenset(codepoints)


@cache
def _measure(family: str) -> FontMeasurement:
    from fontTools.ttLib import TTFont

    faces: list[FontFaceMeasurement] = []
    family_codepoints: set[int] = set()
    for entry in _entries_for_family(family):
        path = Path(entry.fname)
        if path.suffix.lower() not in _FONT_SUFFIXES:
            continue
        ttfont: Any = TTFont(str(path), lazy=False)
        try:
            cmap = _cmap_mapping(ttfont)
            codepoints = set(cmap)
            family_codepoints.update(codepoints)
            faces.append(
                FontFaceMeasurement(
                    file=path.name,
                    weight=int(ttfont["OS/2"].usWeightClass),
                    italic=str(entry.style) == "italic",
                    stretch=str(entry.stretch),
                    tnum_available=_has_tnum_feature(ttfont),
                    digit_widths_uniform=_has_uniform_digit_advances(
                        ttfont, cmap
                    ),
                    fixed_pitch=_is_fixed_pitch(ttfont, cmap),
                    chart_glyphs=tuple(
                        glyph
                        for glyph in _CHART_GLYPHS
                        if ord(glyph) in codepoints
                    ),
                    hangul=all(
                        ord(char) in codepoints for char in _HANGUL_SAMPLE
                    ),
                    license=_classify_license(ttfont),
                )
            )
        finally:
            ttfont.close()

    if not faces:
        raise KeyError(f"no bundled font files measured for family: {family}")

    default_face = _default_numeric_face(faces)
    return FontMeasurement(
        family=family,
        files=tuple(sorted(faces, key=lambda face: face.file)),
        weights=tuple(sorted({face.weight for face in faces})),
        italic=any(face.italic for face in faces),
        tnum_available=any(face.tnum_available for face in faces),
        default_digit_widths_uniform=default_face.digit_widths_uniform,
        fixed_pitch=any(face.fixed_pitch for face in faces),
        chart_glyphs=tuple(
            glyph for glyph in _CHART_GLYPHS if ord(glyph) in family_codepoints
        ),
        hangul=all(ord(char) in family_codepoints for char in _HANGUL_SAMPLE),
        licenses=tuple(sorted({face.license for face in faces})),
    )


def list_registered() -> list[str]:
    """Return sorted bundled font family names registered in matplotlib."""
    ensure_loaded()
    bundle_dir = get_font_dir()
    return sorted(
        {
            entry.name
            for entry in font_manager.fontManager.ttflist
            if _is_bundled_font_entry(entry, bundle_dir)
        }
    )


def _promote_bundled_fonts() -> None:
    """Move bundled font entries to the front of ``fontManager.ttflist``.

    ``FontManager.addfont`` *appends* each bundled ``FontEntry`` to
    ``ttflist``, so the bundled entries land *after* the system fonts
    that matplotlib scanned when it built the manager. But
    :meth:`FontManager._findfont_cached` scores every entry and keeps the
    **first** among equal best scores (``if score < best_score`` — a
    strict inequality). A system-installed copy of a bundled family
    (e.g. ``/Library/Fonts/Roboto-Regular.ttf``) therefore ties the
    bundled copy on family+style and, being earlier, silently wins —
    masking the shipped assets and breaking the eager-registration
    contract on any machine with same-named system fonts.

    Partitioning ``ttflist`` so the bundled entries sit first makes them
    deterministically win those ties. This changes **only** tie-breaks:
    a system font that scores *strictly* better for a different
    family/style still has the minimum score and still wins regardless of
    position. The relative order of bundled entries (and of non-bundled
    entries) is preserved, so nothing else reshuffles.

    Idempotent: once the bundled entries are already at the front this is
    a no-op (no reordering, no cache clear), so repeated registration
    paths never reshuffle endlessly.
    """
    ttflist = font_manager.fontManager.ttflist
    bundle_dir = get_font_dir()

    bundled: list[font_manager.FontEntry] = []
    others: list[font_manager.FontEntry] = []
    for entry in ttflist:
        is_bundled = _is_bundled_font_entry(entry, bundle_dir)
        (bundled if is_bundled else others).append(entry)

    if not bundled:
        return

    # Already at the front (same objects, same order)? Leave untouched so
    # the operation is a fixed point under repeated calls.
    already_front = len(ttflist) >= len(bundled) and all(
        existing is promoted
        for existing, promoted in zip(
            ttflist[: len(bundled)], bundled, strict=True
        )
    )
    if already_front:
        return

    # In-place slice assignment preserves the list object matplotlib's
    # fontManager holds a reference to.
    ttflist[:] = bundled + others
    # Mirror ``addfont``: any cached resolution predates the new order.
    font_manager.fontManager._findfont_cached.cache_clear()  # type: ignore[attr-defined]


def _correct_bundled_weight_metadata() -> None:
    """Correct known upstream weight metadata errors for bundled faces."""
    bundle_dir = get_font_dir()
    ttflist = font_manager.fontManager.ttflist
    corrected = False
    for index, entry in enumerate(ttflist):
        if not _is_bundled_font_entry(entry, bundle_dir):
            continue
        intended_weight = _BUNDLED_FONT_WEIGHT_OVERRIDES.get(
            Path(entry.fname).name
        )
        if intended_weight is not None:
            ttflist[index] = replace(entry, weight=intended_weight)
            corrected = True
    if corrected:
        font_manager.fontManager._findfont_cached.cache_clear()  # type: ignore[attr-defined]


def _add_fonts() -> None:
    """Register bundled custom fonts with matplotlib's font manager.

    Scans the ``asset/font`` directory for font files and registers them
    with matplotlib's font manager so they can be used in charts, then
    promotes them ahead of same-named system fonts so the eager
    registration contract holds even on machines where those families are
    installed system-wide (see :func:`_promote_bundled_fonts`). Emits a
    :class:`UserWarning` when the bundle looks emptied so that the
    Korean/CJK fallback chain degradation is visible to users.

    Notes
    -----
    This function is called automatically once when the library is
    imported; users do not need to call it directly.
    """
    found = font_manager.findSystemFonts([_FONT_DIR])
    for font in found:
        font_manager.fontManager.addfont(font)

    _correct_bundled_weight_metadata()

    # ``addfont`` appends, so bundled entries lose score ties to earlier
    # system fonts of the same family. Promote them to the front so the
    # shipped assets deterministically win those ties.
    _promote_bundled_fonts()

    # Graceful warning if the bundle looks emptied. This catches
    # accidental asset deletion and any future slim-install variant
    # (e.g. a [fonts] extra) that shipped without the bundled corpus.
    if len(found) < _EXPECTED_MIN_FONTS:
        warnings.warn(
            f"dartwork-mpl found only {len(found)} bundled font file(s) "
            f"in {_FONT_DIR}. The Korean/CJK fallback chain may "
            f"degrade to system fonts. Reinstall the package to "
            f"restore the bundled assets.",
            UserWarning,
            # Points at the ``_add_fonts()`` call inside
            # ``ensure_loaded`` — a stable in-package frame. The
            # previous ``stacklevel=3`` walked one frame further into
            # whatever happened to import the package, which was never
            # a useful location.
            stacklevel=2,
        )


_loaded: bool = False
_lock: threading.Lock = threading.Lock()


def ensure_loaded() -> None:
    """Ensure custom fonts are loaded and registered.

    Thread-safe: uses double-checked locking to avoid duplicate
    font registration when called concurrently from multiple threads.
    """
    global _loaded

    # Fast path: skip lock once already loaded.
    if _loaded:
        return

    with _lock:
        if _loaded:
            return
        _add_fonts()
        _loaded = True
