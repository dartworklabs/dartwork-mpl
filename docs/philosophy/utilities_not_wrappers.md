# Utilities, Not Wrappers

Most visualization libraries aim to reduce boilerplate by providing high-level abstractions:

```python
# Typical high-level library approach
chart = SomeLib.line_chart(
    data=df,
    x='date',
    y='value',
    theme='modern',
    title='My Chart',
    show_legend=True
)
chart.save('output.png')
```

While this looks convenient for simple cases, it creates several problems.

## Additional Abstraction Layers

Every wrapper library introduces a new layer between you and matplotlib. When you need to customize something beyond the library's API:

1. You must understand both the wrapper's API **and** matplotlib's API.
2. You need to find escape hatches to access underlying matplotlib objects.
3. The wrapper's design decisions may conflict with your requirements.

## Diminishing Returns for Custom Visualizations

The more customized your visualization needs to be, the less value these wrappers provide:

```python
# When you need fine-grained control, wrappers become obstacles
chart = SomeLib.create_chart(data, theme='custom')
# How do I adjust the spine thickness?
# How do I add a secondary y-axis with specific formatting?
# How do I position a legend outside the plot area precisely?

# You end up doing this:
ax = chart.get_underlying_axes()  # escape hatch
ax.spines['top'].set_visible(False)  # back to matplotlib
# ... mixing two APIs becomes confusing
```

## You're Still Writing matplotlib

With dartwork-mpl, your code remains fundamentally matplotlib code. We provide utilities that **enhance** matplotlib, not wrappers that **replace** it:

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# Apply style (sets rcParams, nothing more)
dm.style.use('scientific')

# Standard matplotlib figure creation — dm.figsize returns the
# inches tuple plt.figure already expects
fig = plt.figure(figsize=dm.figsize("9cm", "7cm"))
ax = fig.add_subplot(111)

# Standard matplotlib plotting
x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), color='dc.red2', linewidth=0.7)  # only color is extended
ax.set_xlabel('Time [s]')
ax.set_ylabel('Amplitude')
ax.legend(fontsize=dm.fs(-1))  # utility for relative font size

# Utility for layout optimization
dm.simple_layout(fig)

# Standard matplotlib or utility for saving
fig.savefig('output.png')
```

Every line is recognizable matplotlib. The dartwork-mpl additions are clearly utilities.

## Predictable Behavior

matplotlib's API is well-documented and behaves consistently. When you write:

```python
ax.plot(x, y, color='red', linewidth=2)
ax.set_xlim(0, 10)
```

You know exactly what will happen. There are no hidden transformations or automatic adjustments that might surprise you. You retain **low-level control** over every aspect of your figure, backed by extensive official documentation and decades of community knowledge.

**Summary:** We believe you shouldn't have to learn a new plotting paradigm. matplotlib knowledge combined with minimal dartwork-mpl familiarity is all you need to create publication-quality visualizations.
