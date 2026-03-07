"""
Image Display
=============

Render images with different colormaps, interpolation, outlines, and grid overlays for quick QA.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Apply presentation style for web docs
# Default: font.size=7.5, lines.linewidth=0.5, axes.linewidth=0.3
dm.style.use("presentation")

# Generate sample image data
data1 = np.random.rand(20, 20)
data2 = np.random.rand(20, 20)
data3 = np.random.rand(20, 20)

# Create figure
# Square layout for balanced comparisons
fig = plt.figure(figsize=(dm.cm2in(16), dm.cm2in(12)), dpi=300)

# Create GridSpec for 4 subplots
gs = fig.add_gridspec(
    nrows=2,
    ncols=2,
    left=0.08,
    right=0.98,
    top=0.92,
    bottom=0.12,
    wspace=0.2,
    hspace=0.45,
)

# Panel A: imshow with colormap
ax1 = fig.add_subplot(gs[0, 0])
# Explicit parameters: cmap='dm.Spectral', interpolation='bilinear'
im1 = ax1.imshow(
    data1,
    cmap="dm.Spectral",
    interpolation="bilinear",
    aspect="auto",
    origin="lower",
)
ax1.set_xlabel("X index", fontsize=dm.fs(0))
ax1.set_ylabel("Y index", fontsize=dm.fs(0))
ax1.set_title("Colormap: Spectral", fontsize=dm.fs(1))
# Add colorbar with explicit fontsize
cbar1 = fig.colorbar(im1, ax=ax1)
cbar1.set_label("Intensity", fontsize=dm.fs(-1))
cbar1.ax.tick_params(labelsize=dm.fs(-1))

# Panel B: Image with different colormap
ax2 = fig.add_subplot(gs[0, 1])
# Explicit parameters: cmap='dm.coolwarm', interpolation='nearest'
im2 = ax2.imshow(
    data2,
    cmap="dm.coolwarm",
    interpolation="nearest",
    aspect="auto",
    origin="lower",
)
ax2.set_xlabel("X index", fontsize=dm.fs(0))
ax2.set_ylabel("Y index", fontsize=dm.fs(0))
ax2.set_title("Colormap: Coolwarm", fontsize=dm.fs(1))
# Add colorbar
cbar2 = fig.colorbar(im2, ax=ax2)
cbar2.set_label("Intensity", fontsize=dm.fs(-1))
cbar2.ax.tick_params(labelsize=dm.fs(-1))

# Panel C: Multiple images comparison
ax3 = fig.add_subplot(gs[1, 0])
# Explicit parameters: cmap='viridis', interpolation='bicubic'
im3 = ax3.imshow(
    data3,
    cmap="viridis",
    interpolation="bicubic",
    aspect="auto",
    origin="lower",
)
ax3.set_xlabel("X index", fontsize=dm.fs(0))
ax3.set_ylabel("Y index", fontsize=dm.fs(0))
ax3.set_title("Colormap: Viridis", fontsize=dm.fs(1))
# Add colorbar
cbar3 = fig.colorbar(im3, ax=ax3)
cbar3.set_label("Intensity", fontsize=dm.fs(-1))
cbar3.ax.tick_params(labelsize=dm.fs(-1))


# Panel D: Edge detection overlay
ax4 = fig.add_subplot(gs[1, 1])
edges = np.abs(np.gradient(data1, axis=0)) + np.abs(np.gradient(data1, axis=1))
im4 = ax4.imshow(
    edges,
    cmap="dm.Greys",
    interpolation="nearest",
    aspect="auto",
    origin="lower",
)
ax4.set_title("Edge Map Overlay", fontsize=dm.fs(1))
ax4.set_xlabel("X index", fontsize=dm.fs(0))
ax4.set_ylabel("Y index", fontsize=dm.fs(0))
fig.colorbar(im4, ax=ax4).set_label("Edge strength", fontsize=dm.fs(-1))

# Optimize layout
dm.simple_layout(fig, gs=gs)

# Show plot
plt.show()
