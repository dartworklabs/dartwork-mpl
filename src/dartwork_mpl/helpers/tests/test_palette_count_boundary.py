"""A negative series count cannot describe a length-n palette."""

import pytest

from dartwork_mpl.helpers.colors import make_palette


@pytest.mark.parametrize("kind", ["categorical", "sequential", "diverging"])
@pytest.mark.parametrize("n", [-1, -9])
def test_negative_count_rejected_instead_of_slicing_from_end(kind, n):
    """Reject negative counts rather than returning unrelated colors or []."""
    with pytest.raises(ValueError, match="n must be non-negative"):
        make_palette(n, kind=kind)
