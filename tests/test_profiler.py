from __future__ import annotations

from pathlib import Path

from mydataanalysist.profiler import profile_csv


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_profile_infers_types_counts_nulls_and_numeric_stats(tmp_path: Path) -> None:
    csv_text = (
        "id,price,active,name\n"
        "1,9.5,true,alice\n"
        "2,10.0,false,bob\n"
        "3,,true,\n"
    )
    path = _write(tmp_path, "data.csv", csv_text)
    result = profile_csv(path)

    assert result.ok
    assert result.rows == 3
    assert result.columns["id"].type == "int"
    assert result.columns["id"].nulls == 0
    assert result.columns["price"].type == "float"
    assert result.columns["price"].nulls == 1
    assert result.columns["price"].mean == 9.75
    assert result.columns["price"].min == 9.5
    assert result.columns["price"].max == 10.0
    assert result.columns["active"].type == "bool"
    assert result.columns["name"].type == "str"
    assert result.columns["name"].nulls == 1


def test_profile_skips_when_row_count_exceeds_cap(tmp_path: Path) -> None:
    rows = "\n".join(str(i) for i in range(5))
    csv_text = "x\n" + rows + "\n"
    path = _write(tmp_path, "data.csv", csv_text)
    result = profile_csv(path, max_rows=3, max_bytes=10_000_000)

    assert not result.ok
    assert result.reason == "too_many_rows"


def test_profile_skips_when_file_exceeds_byte_cap(tmp_path: Path) -> None:
    path = _write(tmp_path, "data.csv", "x\n" + "1\n" * 100)
    result = profile_csv(path, max_rows=50_000, max_bytes=10)

    assert not result.ok
    assert result.reason == "too_large"


def test_profile_skips_on_empty_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "data.csv", "")
    result = profile_csv(path)

    assert not result.ok
    assert result.reason == "empty"


def test_profile_skips_on_missing_file(tmp_path: Path) -> None:
    result = profile_csv(tmp_path / "missing.csv")

    assert not result.ok
    assert result.reason == "not_found"
