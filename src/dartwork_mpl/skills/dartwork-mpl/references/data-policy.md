# Native data policy

Keep the user's observations and missing-value gaps unless a transformation was
requested; explain any removal. `dm.validate_data` returns `(x_array, y_array_or_None)`
and never writes to input storage. It does not draw or validate a figure.

## Choose explicitly

Omitting `policy`, or passing `policy=None`, keeps the exact legacy behavior:
numeric NaN and Inf observations are removed by default, while `allow_nan=True`
retains both. Legacy object passthrough, dimensional behavior, warnings, exceptions
and storage behavior also remain unchanged. Do not use the legacy path to infer
support for those inputs under an explicit policy.

For one or two numeric vectors, pass one of these case-sensitive policies:

| Policy | Outcome |
|---|---|
| `"strict"` | Reject any NaN or positive/negative Inf with `dm.DataPolicyError`; no cleanup. |
| `"preserve"` | Retain every value and its order, including NaN and Inf. |
| `"clean"` | Remove nonfinite observations; no filling, clipping, sorting or coercion. |

Every explicit policy requires `allow_nan` to be the boolean `False` (its default).
Passing `True`, even with `"preserve"`, raises `ValueError`; policy selects behavior.
Each input must convert with `np.asarray` to a one-dimensional signed integer,
unsigned integer or real floating array (`dtype.kind` in `iuf`). Masked arrays,
object arrays (including boxed NaN/Inf or None), strings, bool, complex, datetime,
scalars and multidimensional arrays are rejected with `ValueError`. There is no
implicit cast or flattening. `require_same_length` must be bool; `min_points`
must be a positive Python/NumPy integer, excluding bool.

Shapes, dtypes, lengths and each vector's original `min_points` are checked before
policy action. Equal original x/y lengths mean aligned observations, even with
`require_same_length=False`: clean removes the union of their nonfinite row indices
from both vectors. Unequal original lengths raise unless `require_same_length=False`;
then vectors stay independent and each is cleaned and checked separately. If clean
would leave either vector below `min_points`, it raises `dm.DataPolicyError` before
returning or emitting a success warning. No partial result is returned.

Finite successful inputs keep their `np.asarray` identity, dtype, strides and memory
sharing. Clean copies only a vector whose rows must be removed. Preserve retains Inf;
it does not establish plot/domain validity or make infinity safe to plot.

## Read the diagnostic record

Import the types as `dm.DataPolicyError` (`ValueError`) and
`dm.DataPolicyWarning` (`UserWarning`); both are also exported by
`dartwork_mpl.validate`. Successful preserve/clean with nonfinite issues emits one
warning at the caller; finite success emits none. Strict rejection and insufficient
clean survivors raise the error. Invalid options or unsupported inputs use ordinary
`ValueError`.

Both diagnostic types expose read-only attributes with immutable tuple records:

- `policy` and `alignment` (`"single"`, `"aligned"` or `"independent"`).
- `issues`: `(argument, original_zero_based_index, kind)` triples, x before y,
  ascending index, with kind `"nan"`, `"posinf"` or `"neginf"`.
- `removed_indices`, `kept_indices`, `proposed_removed_indices`: pairs of
  `(argument, tuple_of_original_indices)`, including every supplied argument.

Successful clean records the actual removals and retained indices, including finite
aligned partner rows. Preserve and errors record no actual removals and keep all
original indices; only a failed clean records proposed removals. Other proposed
removal tuples are empty. Text is bounded to 1,024 characters and shows at most ten
indices; use the complete records for accounting. Records cost O(n) memory when
issues exist; count each aligned removed row once across the pair.

This data-only example explicitly requests cleanup and inspects its record:

```python
"""Clean aligned observations and inspect original-index diagnostics."""

import warnings

import numpy as np

import dartwork_mpl as dm

x = np.array([0.0, 1.0, 2.0, 3.0])
y = np.array([10.0, np.nan, 12.0, 13.0])
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always", dm.DataPolicyWarning)
    clean_x, clean_y = dm.validate_data(x, y, policy="clean")

assert clean_x.tolist() == [0.0, 2.0, 3.0]
assert clean_y.tolist() == [10.0, 12.0, 13.0]
record = caught[0].message
assert isinstance(record, dm.DataPolicyWarning)
assert record.issues == (("y", 1, "nan"),)
assert record.removed_indices == (("x", (1,)), ("y", (1,)))
assert np.isnan(y[1])  # Original input is unchanged.
```

## MCP checks are separate

MCP `validate_plot_data` checks chart-specific input shapes and its optional report
contract. It is separate from native `dm.validate_data` and does not select these
policies. MCP tools, schemas, descriptions and report behavior are unchanged.
Keep native matplotlib `Figure`/`Axes`, preset styling and the requested edit scope;
a data policy is not a reason to restyle a chart or change unrelated observations.
