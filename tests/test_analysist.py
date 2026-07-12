from __future__ import annotations

import json
from pathlib import Path

from mythings.engine import NoopEngine
from mythings.ledger import Ledger
from mythings.policy import Action, Decision, PolicyResult

from conftest import ScriptedEngine, fake_gh
from mydataanalysist.analysist import Analysist


class DenyPolicy:
    def evaluate(self, action: Action) -> PolicyResult:
        return PolicyResult(Decision.DENY, reason="no", rule="test")


def _write_csv(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "data.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_analyze_uses_engine_reply(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    csv_path = _write_csv(tmp_path, "id,price\n1,9.5\n2,10.0\n")
    engine = ScriptedEngine(
        json.dumps(
            {
                "insights": "Prices cluster tightly around $10.",
                "next_analysis": "Check for seasonal price trends.",
            }
        )
    )
    analysist = Analysist(ledger=ledger, engine=engine)
    result = analysist.analyze(csv_path)

    assert result.outcome == "success"
    assert result.rows == 2
    assert result.insights == "Prices cluster tightly around $10."
    assert result.next_analysis == "Check for seasonal price trends."
    entries = list(ledger)
    assert entries[-1].kind == "analysis"
    assert entries[-1].data["rows"] == 2


def test_analyze_degrades_to_empty_insights_against_noop_engine(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    csv_path = _write_csv(tmp_path, "id,price\n1,9.5\n2,10.0\n")
    analysist = Analysist(ledger=ledger, engine=NoopEngine())
    result = analysist.analyze(csv_path)

    assert result.outcome == "success"
    assert result.insights == ""
    assert result.next_analysis == ""
    assert result.columns["price"]["mean"] == 9.75


def test_analyze_skips_engine_call_when_over_size_cap(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    rows = "\n".join(str(i) for i in range(5))
    csv_path = _write_csv(tmp_path, "x\n" + rows + "\n")
    engine = ScriptedEngine("should never be called")
    analysist = Analysist(ledger=ledger, engine=engine, max_rows=3)

    result = analysist.analyze(csv_path)

    assert result.outcome == "skipped"
    assert "too_many_rows" in result.detail
    assert engine.calls == []
    entries = list(ledger)
    assert entries[-1].outcome == "skipped"


def test_analyze_skips_engine_call_on_unparseable_file(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    csv_path = _write_csv(tmp_path, "")
    engine = ScriptedEngine("should never be called")
    analysist = Analysist(ledger=ledger, engine=engine)

    result = analysist.analyze(csv_path)

    assert result.outcome == "skipped"
    assert engine.calls == []


def test_no_raw_row_data_reaches_engine_prompt(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    csv_path = _write_csv(tmp_path, "secret\nhunter2\ncorrect-horse\n")
    engine = ScriptedEngine(json.dumps({"insights": "", "next_analysis": ""}))
    analysist = Analysist(ledger=ledger, engine=engine)

    analysist.analyze(csv_path)

    assert "hunter2" not in engine.calls[0].prompt
    assert "correct-horse" not in engine.calls[0].prompt


def test_comment_posts_profile_and_insights_when_requested(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    csv_path = _write_csv(tmp_path, "id,price\n1,9.5\n2,10.0\n")
    fake = fake_gh()
    analysist = Analysist(
        ledger=ledger, repo="owner/name", runner=fake, engine=NoopEngine()
    )
    result = analysist.analyze(csv_path, issue=5, comment=True)

    assert result.comment_url is not None
    assert fake.calls[0][:2] == ["issue", "comment"]


def test_comment_skipped_without_issue(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    csv_path = _write_csv(tmp_path, "id\n1\n")
    analysist = Analysist(ledger=ledger, repo="owner/name", engine=NoopEngine())
    result = analysist.analyze(csv_path, comment=True)
    assert result.comment_url is None


def test_comment_skipped_without_repo(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    csv_path = _write_csv(tmp_path, "id\n1\n")
    analysist = Analysist(ledger=ledger, engine=NoopEngine())
    result = analysist.analyze(csv_path, issue=5, comment=True)
    assert result.comment_url is None


def test_comment_denied_by_policy_is_not_posted(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    csv_path = _write_csv(tmp_path, "id\n1\n")
    fake = fake_gh()
    analysist = Analysist(
        ledger=ledger,
        repo="owner/name",
        runner=fake,
        engine=NoopEngine(),
        policy=DenyPolicy(),
    )
    result = analysist.analyze(csv_path, issue=5, comment=True)
    assert result.comment_url is None
    assert fake.calls == []


def test_non_json_engine_reply_degrades_to_empty_insights(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    csv_path = _write_csv(tmp_path, "id\n1\n")
    analysist = Analysist(ledger=ledger, engine=ScriptedEngine("not json"))
    result = analysist.analyze(csv_path)
    assert result.insights == ""
    assert result.next_analysis == ""
