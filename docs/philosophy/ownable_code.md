# Ownable & Transparent Code

dartwork-mpl believes that the best components are the ones you fully control. We draw inspiration from [shadcn/ui](https://ui.shadcn.com/), a revolutionary approach in the frontend world, which advocates for copying component code into your project rather than installing it as a black-box dependency.

This provides:

- Full ownership and control over the code
- No dependency version conflicts
- Freedom to modify without forking

## No Black Boxes

Users are often hesitant about third-party chart dependencies:

- What if the library is abandoned?
- What if an update breaks my existing code?
- Do I need to understand the entire codebase to use it safely?
- Can I debug issues without diving into unfamiliar source code?

**No one wants a dependency that requires understanding its entire internal codebase to use safely.**

When something doesn't work as expected with dartwork-mpl, you can:

1. **Inspect the utility source**: Our utilities are short and readable.
2. **Debug with standard tools**: Everything is matplotlib under the hood.
3. **Copy and modify**: Extract the utility, adjust it for your needs.
4. **Skip the utility entirely**: Use pure matplotlib if preferred.

## Thin and Simple Design

To make code ownable, it must be readable. Every dartwork-mpl utility is as simple as possible. We prioritize code that is easy to understand over code that handles every edge case.

```python
# Our approach: thin, ownable utility
def fs(n: int | float) -> float:
    """Return base font size + n."""
    return plt.rcParams["font.size"] + n

# Not this: extensible but black-box
def font_size(delta=0, unit='pt', relative_to='base',
              min_size=None, max_size=None, scale_factor=1.0):
    # ... 50 lines of handling edge cases
    pass
```

## Copy-Paste Ready

Many dartwork-mpl utilities can be extracted and used standalone in any project without installing the library:

```python
# These can be copied into any project without dartwork-mpl

def cm2in(cm: float) -> float:
    """Convert centimeters to inches."""
    return cm / 2.54

def mix_colors(color1, color2, alpha=0.5):
    """Mix two colors."""
    c1 = mcolors.to_rgb(color1)
    c2 = mcolors.to_rgb(color2)
    return tuple(alpha * a + (1 - alpha) * b for a, b in zip(c1, c2))
```

> **Roadmap:** We plan to add a pure-matplotlib export feature that resolves
> dartwork-mpl utilities (color names, `cm2in` values) into standard matplotlib
> code, so you can completely remove the dependency when the project is done.
