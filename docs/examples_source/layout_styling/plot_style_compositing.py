"""
Style Compositing
=================

Dartwork-mpl styles are designed to be composited (layered).  Start from a
base, then add font presets, spine options, or language packs.  This example
renders the same data under several style stacks to show the effect.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm


# ---------------------------------------------------------------------------
# Shared plotting function
# ---------------------------------------------------------------------------
def plot_example(title=""):
    """Draw a small two-panel figure to visualise the active style."""
    x = np.linspace(0, 10, 100)
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(dm.cm2in(13), dm.cm2in(10)), dpi=300
    )

    ax1.plot(x, np.sin(x), label="sin(x)")
    ax1.plot(x, np.cos(x), label="cos(x)")
    ax1.set_title(title or "Trigonometric Functions")
    ax1.set_xlabel("x")
    ax1.set_ylabel("y")
    ax1.legend()

    y3 = np.sin(x) * np.exp(-0.2 * x)
    ax2.plot(x, y3, label="sin(x) × exp(−0.2x)")
    ax2.fill_between(x, 0, y3, alpha=0.3)
    ax2.set_title("Damped Sine Wave")
    ax2.set_xlabel("x")
    ax2.set_ylabel("Amplitude")
    ax2.legend()

    dm.simple_layout(fig)
    return fig


# %%
# Base style only
# ---------------
dm.style.stack(["base"])
plot_example("Base Style")
plt.show()

# %%
# Base + spine removal
# --------------------
dm.style.stack(["base", "spine-no"])
plot_example("Base + Spine-No")
plt.show()

# %%
# Scientific preset
# -----------------
dm.style.use("presentation")
plot_example("Scientific Preset")
plt.show()

# %%
# Scientific + Korean
# --------------------
dm.style.use("scientific-kr")
plot_example("Scientific-KR Preset")
plt.show()

# %%
# Presentation preset
# --------------------
dm.style.use("presentation")
plot_example("Presentation Preset")
plt.show()
