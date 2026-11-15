"""A figure's locale: the default convention or Korea's.

Platform vocabulary: ``style`` reads it off a preset and ``color`` binds the
role colours for it; pure, no matplotlib import.
"""

from .model import DefaultLocale, KoreanLocale, Locale

__all__ = ["DefaultLocale", "KoreanLocale", "Locale"]
