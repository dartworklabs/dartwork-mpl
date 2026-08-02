"""Independent numeric oracles shared by color-documentation tests."""


def chroma_r_squared() -> float:
    """Recompute ordinary in-sample R² for the authored chroma catalog."""
    from dartwork_mpl._colors import _recipe as recipe

    observed = [params.cmax for params in recipe.FAMILY_PARAMS.values()]
    fitted = [
        recipe.fourier_eval(recipe.FOURIER["cmax_k3"], recipe.mid_hue(params))
        for params in recipe.FAMILY_PARAMS.values()
    ]
    mean = sum(observed) / len(observed)
    residual = sum(
        (actual - predicted) ** 2
        for actual, predicted in zip(observed, fitted, strict=True)
    )
    total = sum((actual - mean) ** 2 for actual in observed)
    return 1.0 - residual / total
