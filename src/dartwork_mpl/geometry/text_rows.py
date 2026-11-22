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
        offsets: Callable[[RendererBase], tuple[float, ...]],
    ) -> None:
        """Carry the original styling and the new native runs."""
        super().__init__(text=text)  # pyright: ignore[reportUnknownMemberType]
        self.update_from(source)
        self.set_zorder(source.get_zorder())
        self.set_in_layout(source.get_in_layout())
        self.pieces = pieces
        self.planned_text = text
        self.offsets = offsets
        self.edited = Text()  # pyright: ignore[reportUnknownMemberType]
        self.origin = origin
        self.renderer: RendererBase | None = None

    def place(self, renderer: RendererBase) -> tuple[Text, ...]:
        """Place the original runs, or one ordinary Text for edited content."""
        self.renderer = renderer
        origin = Affine2D().translate(*self.origin(renderer))
        if self.get_text() != self.planned_text:
            fig = self.get_figure(root=False)
            if fig is not None:
                self.edited.set_figure(fig)
            self.edited.update_from(self)
            self.edited.set_text(self.get_text())
            self.edited.set_horizontalalignment("left")
            self.edited.set_verticalalignment("baseline")
            self.edited.set_transform(origin)
            return (self.edited,)
        for piece, offset in zip(
            self.pieces, self.offsets(renderer), strict=True
        ):
            piece.xyann = (offset, 0)
            piece.set_color(self.get_color())
            piece.set_alpha(self.get_alpha())
            piece.set_fontproperties(self.get_fontproperties())
            piece.xycoords = origin
        return self.pieces

    def draw(self, renderer: RendererBase) -> None:
        """Draw each native annotation in this row."""
        if self.get_visible():
            for piece in self.place(renderer):
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
        return Bbox.union(
            [
                piece.get_window_extent(renderer)
                for piece in self.place(renderer)
            ]
        )
