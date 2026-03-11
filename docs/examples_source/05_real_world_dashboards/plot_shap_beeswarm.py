"""
SHAP Feature Importance Beeswarm
================================

A standard in Explainable AI (XAI) and machine learning model diagnostics.
This beeswarm plot visualizes both the magnitude of a feature's effect on
the model prediction (x-axis) and the actual value of the feature itself
(color-coded).

We use ``dc.cool_warm`` to represent low (cool) to high (warm) feature values,
providing immediate visual intuition for model behavior.
"""

import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use('report')

np.random.seed(42)

# Synthetic SHAP value data
features = [
    "Age", "Income", "Credit Score", "Debt Ratio", 
    "Has Dependents", "Months on Job", "Recent Defaults"
]
n_features = len(features)
n_samples = 300

shap_values = []
feature_values = []

for i in range(n_features):
    scale = max(0.5, 4.0 - i * 0.5)
    corr_dir = 1 if i % 2 == 0 else -1
    
    f_val = np.random.uniform(-1, 1, n_samples)
    s_val = corr_dir * f_val * scale + np.random.normal(0, scale * 0.3, n_samples)
    
    shap_values.append(s_val)
    feature_values.append(f_val)

fig, ax = plt.subplots(figsize=(dm.SW * 1.5, dm.SW * 1.3))

cmap = plt.get_cmap('dc.cool_warm')

for i in range(n_features):
    y_pos = n_features - 1 - i
    s_vals = shap_values[i]
    f_vals = feature_values[i]
    
    colors = cmap((f_vals + 1) / 2)
    
    # Add vertical jitter to prevent overplotting (beeswarm approximation)
    hist, bin_edges = np.histogram(s_vals, bins=20)
    bin_indices = np.digitize(s_vals, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, len(hist) - 1)
    
    jitter = np.random.uniform(-1, 1, n_samples) * (hist[bin_indices] / max(hist)) * 0.3
    
    ax.scatter(s_vals, y_pos + jitter,
               c=colors, s=dm.fs(-1)**2, alpha=0.8, edgecolors='none', zorder=2)

ax.set_yticks(range(n_features))
ax.set_yticklabels(reversed(features), fontsize=dm.fs(0.5), weight='bold')

ax.axvline(0, color='oc.gray4', lw=1.5, zorder=1, ls='--')

ax.set_xlabel("SHAP value (impact on model output)", fontsize=dm.fs(0), weight='bold', labelpad=10)
ax.set_title("Model Feature Importance (Beeswarm)", fontsize=dm.fs(1.5), weight='bold', pad=20)

# Add a colorbar acting as the legend
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=-1, vmax=1))
cb = fig.colorbar(sm, ax=ax, aspect=40, shrink=0.5, pad=0.05)
cb.set_ticks([-1, 1])
cb.set_ticklabels(['Low', 'High'])
cb.ax.tick_params(labelsize=dm.fs(0))
cb.set_label("Feature Value", fontsize=dm.fs(0), weight='bold')
if hasattr(cb, 'outline'):
    cb.outline.set_visible(False)

for spine in ['top', 'right', 'left']:
    ax.spines[spine].set_visible(False)

fig.tight_layout(pad=1.5)
