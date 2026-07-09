from __future__ import annotations

import json
from pathlib import Path

from mythings.engine import ClaudeCLIEngine, NoopEngine

from mydataanalysist import cli
from mydataanalysist.analysist import Result


def test_build_engine_noop_by_default() -> None:
    assert isinstance(cli.build_engine("noop"), NoopEngine)


def test_build_engine_claude_cli() -> None:
    assert isinstance(cli.build_engine("claude-cli"), ClaudeCLIEngine)


def test_analyze_prints_json(monkeypatch, tmp_path: Path, capsys) -> None:
    result = Result(
        outcome="success",
        file="data.csv",
        rows=2,
        columns={"price": {"type": "float", "nulls": 0}},
        insights="Prices are stable.",
        next_analysis="Check outliers.",
        detail="profiled data.csv",
    )

    class _StubAnalysist:
        def __init__(self, **kwargs: object) -> None:
            pass

        def analyze(self, file, *, issue=None, comment=False) -> Result:
            return result

    monkeypatch.setattr(cli, "Analysist", _StubAnalysist)
    code = cli.main(
        [
            "analyze",
            "--file",
            str(tmp_path / "data.csv"),
            "--ledger",
            str(tmp_path / "ledger.jsonl"),
            "--json",
        ]
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["rows"] == 2
    assert out["insights"] == "Prices are stable."


def test_analyze_prints_insights_without_json_flag(monkeypatch, tmp_path: Path, capsys) -> None:
    result = Result(
        outcome="success",
        file="data.csv",
        rows=1,
        columns={},
        insights="the insight",
        detail="d",
    )

    class _StubAnalysist:
        def __init__(self, **kwargs: object) -> None:
            pass

        def analyze(self, file, *, issue=None, comment=False) -> Result:
            return result

    monkeypatch.setattr(cli, "Analysist", _StubAnalysist)
    cli.main(
        [
            "analyze",
            "--file",
            str(tmp_path / "data.csv"),
            "--ledger",
            str(tmp_path / "ledger.jsonl"),
        ]
    )
    assert capsys.readouterr().out.strip() == "the insight"
