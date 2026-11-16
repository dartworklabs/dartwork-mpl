"""Training curves for a paper in two stacked panels at 3.4 in: hand-placed (a)/(b) letters, a tick at every epoch, a grid."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")

epoch = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
train_loss = [1.92, 1.41, 1.10, 0.91, 0.78, 0.69, 0.62, 0.57, 0.53, 0.50]
val_loss = [1.98, 1.52, 1.25, 1.09, 0.99, 0.94, 0.92, 0.91, 0.92, 0.94]
val_acc = [0.41, 0.55, 0.63, 0.69, 0.72, 0.75, 0.76, 0.77, 0.77, 0.78]

fig, (a, b) = plt.subplots(2, 1, figsize=(3.4, 4.2), sharex=True)
a.plot(epoch, train_loss, "o-", ms=3, lw=1.2, label="Training", color="C0")
a.plot(epoch, val_loss, "s--", ms=3, lw=1.2, label="Validation", color="C3")
a.set_ylabel("Loss")
a.legend(frameon=False)
b.plot(epoch, val_acc, "o-", ms=3, lw=1.2, color="C2")
b.set_ylabel("Validation accuracy")
b.set_xlabel("Epoch")
for ax, letter, y, va in ((a, "(a)", 0.04, "bottom"), (b, "(b)", 0.95, "top")):
    ax.text(0.02, y, letter, transform=ax.transAxes, va=va, fontweight="bold")
    ax.grid(alpha=0.3, lw=0.4)
b.set_xticks(epoch)

dm.simple_layout(fig)
dm.save_formats(fig, "output/paper_two_panel", formats=("png",))
