"""Pure, bounded v1 data reports; proposals never apply or execute changes.

Only declared template fields are inspected. Original numeric lexemes are kept
as tokens, including values outside binary64, so serialization cannot round them.
"""

import copy
import json
import math
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from typing import TypeAlias

from ._data_repair_json import (
    _REPORT_BYTES,
    _constant,
    _DuplicateKey,
    _encode,
    _Json,
    _Limit,
    _NonfiniteToken,
    _Number,
    _pairs,
    _preflight,
    _string_size,
    _unicode_valid,
)

__all__ = [
    "DataRepairReport",
    "build_data_repair_report",
    "serialize_data_repair_report",
]

_RECORDS = 100
_PORTABLE_INTEGER = 2**53 - 1
_NUMBER = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?\Z")
_FIELDS = {
    "scatter": ("x", "y"),
    "bar": ("categories", "values"),
    "bar_horizontal": ("categories", "values"),
    "histogram": ("values", "bins"),
    "heatmap": ("matrix",),
}
_REASON = "Declared numeric value; JSON type changes, review meaning."
_PAIR_ACTION = (
    "Restore the intended aligned observations from the source; choose which "
    "measurement is missing or extra."
)


_Record: TypeAlias = dict[str, _Json]


@dataclass(frozen=True)
class _Context:
    """Normalized caller facts and the five-type declared validation scope."""

    plot_type: str
    recognized: bool
    fields: tuple[str, ...]


@dataclass(frozen=True)
class _Admitted:
    """An admitted original plus independently checked, detached proposals."""

    context: _Context
    raw_json: str
    data: _Json
    unvalidated_paths: tuple[str, ...]
    issues: tuple[_Record, ...]
    changes: tuple[_Record, ...]
    candidate: "_Candidate | None" = None


@dataclass(frozen=True)
class _Candidate:
    """A detached candidate and freshly evaluated remaining scoped issues."""

    data: _Json
    remaining_issues: tuple[_Record, ...]


@dataclass(frozen=True)
class _SyntaxRejected:
    """Bounded text failed strict JSON parsing; its exact raw text is retained."""

    context: _Context
    raw_json: str
    issue: _Record


@dataclass(frozen=True)
class _EncodingRejected:
    """Invalid UTF-8 text has no honestly representable exact JSON raw payload."""

    context: _Context
    offset: int


@dataclass(frozen=True)
class _LimitRejected:
    """A resource refusal contains no payload, candidate, or proposed changes."""

    context: _Context
    limit: _Limit


DataRepairReport: TypeAlias = (
    _Admitted | _SyntaxRejected | _EncodingRejected | _LimitRejected
)


def _pointer(key: str) -> str:
    """Escape an object member as one RFC 6901 root-relative pointer."""
    return "/" + key.replace("~", "~0").replace("/", "~1")


def _kind(value: _Json) -> str:
    """Describe JSON types without treating booleans as numeric values."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float, _Number)):
        return "number"
    if isinstance(value, str):
        return "string"
    return "array" if isinstance(value, list) else "object"


def _nonzero(token: str) -> bool:
    """Determine mathematical nonzero without constructing a huge exponent."""
    mantissa = token.lower().split("e", 1)[0]
    return any(char in "123456789" for char in mantissa)


def _in_range(token: str) -> bool:
    """Check finite binary64 range while retaining the original numeric token."""
    value = float(token)
    return math.isfinite(value) and (value != 0 or not _nonzero(token))


def _conversion(token: str) -> int | float | None:
    """Propose only exact-decimal, portable and sign-preserving type changes."""
    if not _NUMBER.fullmatch(token) or not _in_range(token):
        return None
    if token.startswith("-") and not _nonzero(token):
        return None
    number = float(token)
    if number.is_integer() and abs(number) > _PORTABLE_INTEGER:
        return None
    # Zero's exponent is immaterial, even beyond Decimal's exponent capacity.
    if not _nonzero(token):
        return 0
    try:
        if Decimal(token) != Decimal(json.dumps(number, allow_nan=False)):
            return None
    except InvalidOperation:
        return None
    return int(number) if number.is_integer() else number


@dataclass
class _Inspection:
    """Collect bounded diagnostics and proposals during one scoped traversal."""

    issues: list[_Record] = field(default_factory=list)
    changes: list[_Record] = field(default_factory=list)
    limit: _Limit | None = None

    def issue(
        self, code: str, path: str, message: str, action: str, **details: _Json
    ) -> None:
        """Append one actionable issue; stop retaining records at the first overflow."""
        if self.limit is not None:
            return
        if len(self.issues) == _RECORDS:
            self.limit = _Limit("issues", _RECORDS, _RECORDS + 1)
            return
        self.issues.append(
            {
                "code": code,
                "path": path,
                "message": message,
                "action": action,
                **details,
            }
        )

    def number(self, value: _Json, path: str) -> None:
        """Check one declared numeric element, optionally adding a review proposal."""
        if self.limit is not None:
            return
        if isinstance(value, _Number):
            if not _in_range(value.token):
                self.issue(
                    "numeric_range",
                    path,
                    "Number is outside finite binary64 range.",
                    "Restore a finite numeric value from the source without overflow or nonzero underflow.",
                    observed={"token": value.token},
                )
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value):
                self.issue(
                    "numeric_range",
                    path,
                    "Number is outside finite binary64 range.",
                    "Restore a finite numeric value from the source.",
                )
        elif isinstance(value, str):
            after = _conversion(value)
            if after is None:
                self.issue(
                    "unsafe_conversion",
                    path,
                    "String cannot be safely proposed as a numeric value.",
                    "Supply the intended numeric measurement from the source; do not guess its representation.",
                    observed={"type": "string", "value": value},
                )
            else:
                self.issue(
                    "numeric_string",
                    path,
                    "Declared numeric element is a string.",
                    "Review the proposed JSON type change and confirm that this is a measurement rather than a label. Its binary64 representation may still be approximate.",
                    observed={"type": "string"},
                )
                if self.limit is not None:
                    return
                if len(self.changes) == _RECORDS:
                    self.limit = _Limit("changes", _RECORDS, _RECORDS + 1)
                    return
                self.changes.append(
                    {
                        "path": path,
                        "before": value,
                        "after": after,
                        "reason": _REASON,
                        "requires_review": True,
                    }
                )
        else:
            self.issue(
                "expected_number",
                path,
                "Declared numeric element is not a number.",
                "Supply the intended numeric measurement from the source; booleans and null are not measurements.",
                observed={"type": _kind(value)},
            )

    def array(self, value: _Json, path: str) -> list[_Json] | None:
        """Require a nonempty array while preserving an empty array for shape checks."""
        if not isinstance(value, list):
            self.issue(
                "expected_array",
                path,
                "Expected a JSON array.",
                "Supply the intended ordered observations as a JSON array.",
                observed={"type": _kind(value)},
            )
            return None
        if not value:
            self.issue(
                "empty_array",
                path,
                "Required array is empty.",
                "Restore the intended observations from the source.",
                observed={"length": 0},
            )
        return value


def _inspect(context: _Context, data: _Json) -> _Inspection:
    """Validate declared fields in stable field/index order, without mutating data."""
    result = _Inspection()
    if not isinstance(data, dict):
        result.issue(
            "expected_object",
            "",
            "Expected a JSON object.",
            "Supply an object containing the declared plot fields.",
            observed={"type": _kind(data)},
        )
        return result
    for name in context.fields:
        if name not in data and not (
            name == "bins" and context.plot_type == "histogram"
        ):
            result.issue(
                "missing_field",
                _pointer(name),
                "Required field is missing.",
                f"Supply the intended {name} observations from the source.",
            )
            continue
        if name not in data:
            continue
        if name == "bins":
            _bins(result, data[name])
        elif name == "matrix":
            _matrix(result, data[name])
        else:
            values = result.array(data[name], _pointer(name))
            if values is not None:
                for index, value in enumerate(values):
                    path = f"/{name}/{index}"
                    if name == "categories":
                        if not isinstance(value, str):
                            result.issue(
                                "expected_string",
                                path,
                                "Category label is not a string.",
                                "Supply the intended category label explicitly as a string.",
                                observed={"type": _kind(value)},
                            )
                    else:
                        result.number(value, path)
    if context.plot_type in ("scatter", "bar", "bar_horizontal"):
        first, second = context.fields
        left, right = data.get(first), data.get(second)
        if (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) != len(right)
        ):
            result.issue(
                "length_mismatch",
                f"/{first}",
                "Paired vectors have unequal lengths.",
                _PAIR_ACTION,
                related_paths=[f"/{second}"],
                observed={"lengths": [len(left), len(right)]},
            )
    order = {name: index for index, name in enumerate(context.fields)}
    result.issues.sort(key=lambda issue: _path_order(str(issue["path"]), order))
    return result


def _path_order(
    path: str, fields: dict[str, int]
) -> tuple[int, tuple[int, ...]]:
    """Place parent diagnostics before children and preserve numeric index order."""
    parts = path.split("/")
    return fields.get(parts[1] if len(parts) > 1 else "", -1), tuple(
        int(part) for part in parts[2:]
    )


def _matrix(result: _Inspection, value: _Json) -> None:
    """Diagnose each row and ragged relationships without rectangularization."""
    matrix = result.array(value, "/matrix")
    if matrix is None:
        return
    rows = []
    for index, row in enumerate(matrix):
        parsed = result.array(row, f"/matrix/{index}")
        if parsed is not None:
            rows.append((index, parsed))
    if rows and len({len(row) for _, row in rows}) > 1:
        result.issue(
            "ragged_matrix",
            f"/matrix/{rows[0][0]}",
            "Matrix rows have unequal lengths.",
            "Restore the intended rectangular measurements from the source; choose the missing or extra entries without padding or dropping data.",
            related_paths=[f"/matrix/{index}" for index, _ in rows[1:]],
            observed={"lengths": [len(row) for _, row in rows]},
        )
    for index, row in rows:
        for column, item in enumerate(row):
            result.number(item, f"/matrix/{index}/{column}")


def _bins(result: _Inspection, value: _Json) -> None:
    """Validate scalar counts or nondecreasing edge vectors; never coerce counts."""
    token = _numeric_token(value)
    if (
        token is not None
        and re.fullmatch(r"[0-9]+", token)
        and _in_range(token)
    ):
        number = float(token)
        if number > 0 and number.is_integer():
            return
    elif isinstance(value, list):
        if len(value) < 2:
            result.issue(
                "invalid_bins",
                "/bins",
                "Histogram edges require at least two values.",
                "Supply at least two intended numeric bin edges in nondecreasing order.",
                observed={"length": len(value)},
            )
        comparable: list[Decimal | None] = []
        for index, item in enumerate(value):
            result.number(item, f"/bins/{index}")
            token = _numeric_token(item)
            if token is not None and _in_range(token):
                comparable.append(
                    Decimal(token) if _nonzero(token) else Decimal(0)
                )
            else:
                comparable.append(None)
        if any(
            a is not None and b is not None and a > b
            for a, b in pairwise(comparable)
        ):
            result.issue(
                "invalid_bins",
                "/bins",
                "Histogram edges decrease.",
                "Restore the intended nondecreasing bin edges from the source; do not sort observations implicitly.",
            )
        return
    result.issue(
        "invalid_bins",
        "/bins",
        "Bins must be a positive integer count or numeric edge array.",
        "Supply an intended positive integer count, or at least two numeric edges in nondecreasing order.",
        observed={"type": _kind(value)},
    )


def _numeric_token(value: _Json) -> str | None:
    """Read original tokens or known finite candidate numbers, excluding booleans."""
    if isinstance(value, _Number):
        return value.token
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return json.dumps(value, allow_nan=False)
    return None


def _candidate(data: _Json, changes: list[_Record]) -> _Json:
    """Apply only proposed numeric elements to a deep copy owned by this report."""
    candidate = copy.deepcopy(data)
    for change in changes:
        parts = str(change["path"]).split("/")[1:]
        current = candidate
        for part in parts[:-1]:
            if isinstance(current, list):
                current = current[int(part)]
            elif isinstance(current, dict):
                current = current[part]
        if isinstance(current, list):
            current[int(parts[-1])] = change["after"]
        elif isinstance(current, dict):
            current[parts[-1]] = change["after"]
    return candidate


def _syntax(
    context: _Context, raw: str, code: str, offset: int | None = None
) -> _SyntaxRejected:
    """Return a parser refusal with exact text and a character offset if known."""
    issue: _Record = {
        "code": code,
        "path": "",
        "message": "Input is not unambiguous strict JSON.",
        "action": "Correct the JSON source without duplicate members, nonfinite constants, trailing content or invalid Unicode.",
    }
    if offset is not None:
        issue["observed"] = {"offset": offset}
    return _SyntaxRejected(context, raw, issue)


def build_data_repair_report(
    plot_type: str, data_json: str, *, recognized: bool
) -> DataRepairReport:
    """Parse once and return admitted, syntax, encoding or budget outcomes.

    The caller supplies catalog membership. This function performs no I/O and
    never applies proposals; serialization preserves original numeric tokens.
    """
    name = plot_type.lower()
    context = _Context(name, recognized, _FIELDS.get(name, ()))
    if _string_size(name) > _REPORT_BYTES:
        return _name_refusal(name)
    try:
        limit = _preflight(data_json)
    except UnicodeEncodeError as error:
        return _bounded(_EncodingRejected(context, error.start))
    if limit is not None:
        return _bounded(_LimitRejected(context, limit))
    try:
        data = json.loads(
            data_json,
            parse_int=_Number,
            parse_float=_Number,
            parse_constant=_constant,
            object_pairs_hook=_pairs,
        )
    except json.JSONDecodeError as error:
        return _bounded(_syntax(context, data_json, "invalid_json", error.pos))
    except _DuplicateKey:
        return _bounded(_syntax(context, data_json, "duplicate_key"))
    except _NonfiniteToken:
        return _bounded(_syntax(context, data_json, "nonfinite_token"))
    if not _unicode_valid(data):
        return _bounded(_syntax(context, data_json, "invalid_json"))
    unknown = (
        tuple(
            sorted(_pointer(key) for key in data if key not in context.fields)
        )
        if isinstance(data, dict)
        else ()
    )
    if not context.fields:
        issue: _Record = {
            "code": "unsupported_plot_type",
            "path": "",
            "message": "This plot type has no declared repair coverage.",
            "action": "Choose a supported plot type or validate the intended fields manually.",
            "observed": {"recognized": recognized},
        }
        return _bounded(
            _Admitted(context, data_json, data, unknown, (issue,), ())
        )
    inspected = _inspect(context, data)
    if inspected.limit is not None:
        return _bounded(_LimitRejected(context, inspected.limit))
    proposal = None
    if inspected.changes:
        candidate = _candidate(data, inspected.changes)
        checked = _inspect(context, candidate)
        if checked.limit is not None:
            return _bounded(_LimitRejected(context, checked.limit))
        issue_count = len(inspected.issues) + len(checked.issues)
        if issue_count > _RECORDS:
            return _bounded(
                _LimitRejected(context, _Limit("issues", _RECORDS, issue_count))
            )
        proposal = _Candidate(candidate, tuple(checked.issues))
    return _bounded(
        _Admitted(
            context,
            data_json,
            data,
            unknown,
            tuple(inspected.issues),
            tuple(inspected.changes),
            proposal,
        )
    )


def _wire(report: DataRepairReport) -> _Record:
    """Map every closed outcome to its v1 presence and status contract."""
    context = report.context
    output: _Record = {
        "version": 1,
        "plot_type": context.plot_type,
        "recognized": context.recognized,
        "supported": bool(context.fields),
        "scope": {
            "fields": list(context.fields),
            "unvalidated_paths": list(report.unvalidated_paths)
            if isinstance(report, _Admitted)
            else [],
            "validity": "declared_fields_only",
        },
        "requires_review": False,
        "effects": "none",
    }
    if isinstance(report, _LimitRejected):
        limit = report.limit
        observed: _Record = {
            "limit": limit.name,
            "maximum": limit.maximum,
            "observed": limit.observed,
            "field": limit.field,
        }
        if limit.field_bytes is not None:
            observed["field_bytes"] = limit.field_bytes
        output.update(
            status="rejected",
            issues=[
                {
                    "code": "limit_exceeded",
                    "path": "",
                    "message": "Report admission or output budget exceeded.",
                    "action": "Reduce the submitted data or plot name to fit the stated budget.",
                    "observed": observed,
                }
            ],
        )
    elif isinstance(report, _EncodingRejected):
        output.update(
            status="rejected",
            issues=[
                {
                    "code": "invalid_json",
                    "path": "",
                    "message": "Input contains invalid UTF-8 text.",
                    "action": "Supply valid Unicode text before JSON parsing.",
                    "observed": {
                        "offset": report.offset,
                        "type": "invalid_utf8",
                    },
                }
            ],
            changes=[],
        )
    elif isinstance(report, _SyntaxRejected):
        output.update(
            status="rejected",
            original={"raw_json": report.raw_json},
            issues=[report.issue],
            changes=[],
        )
    else:
        status = (
            "unsupported"
            if not context.fields
            else "proposal"
            if report.changes
            else "needs_input"
            if report.issues
            else "valid"
        )
        output.update(
            status=status,
            original={"raw_json": report.raw_json, "data": report.data},
            issues=list(report.issues),
            changes=list(report.changes),
            requires_review=bool(report.changes),
        )
        if report.candidate is not None:
            output["candidate"] = {
                "data": report.candidate.data,
                "valid": not report.candidate.remaining_issues,
                "remaining_issues": list(report.candidate.remaining_issues),
            }
    return output


def _name_refusal(
    name: str, report_bytes: int = _REPORT_BYTES + 1
) -> _LimitRejected:
    """Use the approved empty-name fallback only when name echo cannot fit."""
    return _LimitRejected(
        _Context("", False, ()),
        _Limit(
            "report_bytes",
            _REPORT_BYTES,
            max(_string_size(name), report_bytes),
            "plot_type",
            _string_size(name),
        ),
    )


def _bounded(report: DataRepairReport) -> DataRepairReport:
    """Replace any oversized report with one bounded, payload-free refusal."""
    _, size = _encode(_wire(report))
    if size <= _REPORT_BYTES:
        return report
    refusal = _LimitRejected(
        report.context, _Limit("report_bytes", _REPORT_BYTES, size)
    )
    _, refusal_size = _encode(_wire(refusal))
    return (
        refusal
        if refusal_size <= _REPORT_BYTES
        else _name_refusal(report.context.plot_type, refusal_size)
    )


def serialize_data_repair_report(report: DataRepairReport) -> str:
    """Serialize a built report as strict, bounded, deterministic JSON text."""
    return _encode(_wire(_bounded(report)))[0]
