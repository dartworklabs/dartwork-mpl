"""An artist whose text is drawn as several pieces on one baseline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib.text import Text
from matplotlib.transforms import Affine2D, Bbox

from .renderer import canvas_renderer

if TYPE_CHECKING:
    from collections.abc import Callable

    from matplotlib.backend_bases import RendererBase
    from matplotlib.text import Annotation


class AlignedTextRow(Text):
    """One layout and check box for a row of native annotations."""

    def __init__(
        self,
        source: Text,
        text: str,
        pieces: tuple[Annotation, ...],
        origin: Callable[[RendererBase], tuple[float, float]],
    ) -> None:
        """Carry the original styling and the new native runs."""
        super().__init__(text=text)  # pyright: ignore[reportUnknownMemberType]
        self.update_from(source)
        self.set_zorder(source.get_zorder())
        self.set_in_layout(source.get_in_layout())
        self.pieces = pieces
        self.origin = origin
        self.renderer: RendererBase | None = None

    def place(self, renderer: RendererBase) -> None:
        """Put every piece on the same baseline for this renderer."""
        self.renderer = renderer
        origin = Affine2D().translate(*self.origin(renderer))
        for piece in self.pieces:
            piece.set_color(self.get_color())
            piece.set_alpha(self.get_alpha())
            piece.set_fontproperties(self.get_fontproperties())
            piece.xycoords = origin

    def draw(self, renderer: RendererBase) -> None:
        """Draw each native annotation in this row."""
        if self.get_visible():
            self.place(renderer)
            for piece in self.pieces:
                piece.draw(renderer)
        self.stale = False

    def get_window_extent(
        self, renderer: RendererBase | None = None, dpi: float | None = None
    ) -> Bbox:
        """The union of visible runs, in the current display coordinates."""
        fig = self.get_figure(root=True)
        if renderer is None and fig is not None:
            renderer = canvas_renderer(fig) or self.renderer
        if not self.get_visible() or renderer is None:
            return super().get_window_extent(renderer, dpi)
        self.place(renderer)
        return Bbox.union(
            [piece.get_window_extent(renderer) for piece in self.pieces]
        )
