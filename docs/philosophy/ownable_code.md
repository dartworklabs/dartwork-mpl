# Ownable & Transparent Code

dartwork-mpl is designed so that every utility is simple enough to **copy into your project** and fully understand. You're never locked into the library — if you decide to leave, take the code with you.

:::{tip}
This approach draws inspiration from [shadcn/ui](https://ui.shadcn.com/) in the
frontend world, which advocates copying component code into your project rather
than installing opaque dependencies.
:::

## No Black Boxes

When something doesn't work as expected, you can:

1. **Inspect the utility source** — our utilities are short and readable.
2. **Debug with standard tools** — everything is matplotlib under the hood.
3. **Copy and modify** — extract the utility, adjust it for your needs.
4. **Skip the utility entirely** — use pure matplotlib if preferred.

## Thin and Simple Design

To make code ownable, it must be readable. We prioritize code that is easy to understand over code that handles every edge case:

```python
# Our approach: thin, ownable utility
def fs(n: int | float) -> float:
    """Return base font size + n."""
    return plt.rcParams["font.size"] + n

# Not this: extensible but hard to own
def font_size(delta=0, unit='pt', relative_to='base',
              min_size=None, max_size=None, scale_factor=1.0):
    # ... 50 lines of handling edge cases
    pass
```

## Copy-Paste Ready

Many dartwork-mpl utilities can be extracted and used standalone:

```python
# These work without dartwork-mpl installed

def cm2in(cm: float) -> float:
    """Convert centimeters to inches."""
    return cm / 2.54

def simple_layout(fig, margin=0.05):
    """Measure visible artists and place GridSpec edges deterministically."""
    gs = fig.axes[0].get_gridspec()
    # ... standard matplotlib extent measurement + GridSpec arithmetic
```

> **Zero lock-in:** At every level, dartwork-mpl is designed to be optional.
> You can adopt it incrementally, and if you outgrow it, take the code with you.
