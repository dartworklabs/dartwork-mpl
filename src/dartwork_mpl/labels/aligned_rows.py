"""An artist whose text is drawn as several pieces on one baseline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib.text import Text
from matplotlib.transforms import Affine2D, Bbox

from ..geometry import canvas_renderer

if TYPE_CHECKING:
    from collections.abc import Callable

    from matplotlib.artist import Artist
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
        self.source = source
        self.source_text = source.get_text()
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

    def get_text(self) -> str:
        """Return a later source edit until the caller realigns the group."""
        source = self.source.get_text()
        return source if source != self.source_text else super().get_text()

    def get_children(self) -> list[Artist]:
        """Expose the constituent artists through Matplotlib inspection."""
        if self.get_text() != self.planned_text:
            return [self.edited]
        return list(self.pieces)

    def remove(self) -> None:
        """Remove the aligned overlay and restore its still-attached source."""
        axes = self.axes
        super().remove()
        if self.source.axes is axes:
            self.source.set_visible(True)

    def place(self, renderer: RendererBase) -> tuple[Text, ...]:
        """Place the original runs, or one ordinary Text for edited content."""
        self.renderer = renderer
        x, y = self.origin(renderer)
        dx, dy = self.get_unitless_position()
        fig = self.get_figure(root=True)
        pixels = fig.dpi / 72 if fig is not None else 1.0
        origin = Affine2D().translate(x + dx * pixels, y + dy * pixels)
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
