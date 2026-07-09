from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_MAX_ROWS = 50_000
_DEFAULT_MAX_BYTES = 10_000_000


@dataclass(frozen=True)
class ColumnProfile:
    type: str  # int | float | bool | str
    nulls: int
    mean: float | None = None
    min: float | None = None
    max: float | None = None
    stdev: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type, "nulls": self.nulls}
        if self.mean is not None:
            data["mean"] = self.mean
            data["min"] = self.min
            data["max"] = self.max
            data["stdev"] = self.stdev
        return data


@dataclass(frozen=True)
class ProfileResult:
    ok: bool
    # set when ok is False: "not_found" | "empty" | "too_many_rows" | "too_large" | "unparseable"
    reason: str = ""
    rows: int = 0
    columns: dict[str, ColumnProfile] = field(default_factory=dict)

    def columns_as_dict(self) -> dict[str, Any]:
        return {name: col.to_dict() for name, col in self.columns.items()}


def _infer_type(value: str) -> str:
    if value.strip().lower() in ("true", "false"):
        return "bool"
    try:
        int(value)
        return "int"
    except ValueError:
        pass
    try:
        float(value)
        return "float"
    except ValueError:
        pass
    return "str"


def _widen(current: str, candidate: str) -> str:
    order = ("bool", "int", "float", "str")
    if current == candidate:
        return current
    # str is the catch-all; once any value forces it, the column stays str.
    if current == "str" or candidate == "str":
        return "str"
    return order[max(order.index(current), order.index(candidate))]


def profile_csv(
    path: str | Path,
    *,
    max_rows: int = _DEFAULT_MAX_ROWS,
    max_bytes: int = _DEFAULT_MAX_BYTES,
) -> ProfileResult:
    path = Path(path)
    if not path.exists():
        return ProfileResult(ok=False, reason="not_found")

    size = path.stat().st_size
    if size == 0:
        return ProfileResult(ok=False, reason="empty")
    if size > max_bytes:
        return ProfileResult(ok=False, reason="too_large")

    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            return ProfileResult(ok=False, reason="empty")

        columns = list(reader.fieldnames)
        types: dict[str, str] = {}
        nulls: dict[str, int] = dict.fromkeys(columns, 0)
        numeric_values: dict[str, list[float]] = {c: [] for c in columns}
        row_count = 0

        for row_count, row in enumerate(reader, start=1):
            if row_count > max_rows:
                return ProfileResult(ok=False, reason="too_many_rows")
            for col in columns:
                raw = row.get(col)
                value = raw.strip() if raw is not None else ""
                if not value:
                    nulls[col] += 1
                    continue
                inferred = _infer_type(value)
                types[col] = _widen(types.get(col, inferred), inferred)
                if inferred in ("int", "float"):
                    numeric_values[col].append(float(value))

    if row_count == 0:
        return ProfileResult(ok=False, reason="empty")

    result_columns: dict[str, ColumnProfile] = {}
    for col in columns:
        col_type = types.get(col, "str")
        values = numeric_values[col] if col_type in ("int", "float") else []
        if values:
            mean = statistics.fmean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0.0
            result_columns[col] = ColumnProfile(
                type=col_type,
                nulls=nulls[col],
                mean=mean,
                min=min(values),
                max=max(values),
                stdev=stdev,
            )
        else:
            result_columns[col] = ColumnProfile(type=col_type, nulls=nulls[col])

    return ProfileResult(ok=True, rows=row_count, columns=result_columns)
