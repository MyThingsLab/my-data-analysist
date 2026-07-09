from __future__ import annotations

import argparse
import json
from pathlib import Path

from mythings.engine import ClaudeCLIEngine, Engine, NoopEngine
from mythings.ledger import Ledger

from mydataanalysist.analysist import Analysist

_ENGINE_NAMES = ("noop", "claude-cli")


def build_engine(name: str, *, model: str | None = None) -> Engine:
    if name == "claude-cli":
        return ClaudeCLIEngine(model=model)
    return NoopEngine()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mydataanalysist",
        description="Given a local CSV, profile it and narrate insights.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    analyze = sub.add_parser("analyze", help="profile a CSV and narrate insights")
    analyze.add_argument("--file", required=True, type=Path)
    analyze.add_argument("--repo", help="GitHub slug owner/name, needed for --comment")
    analyze.add_argument("--issue", type=int, help="issue to comment on with --comment")
    analyze.add_argument(
        "--comment", action="store_true", help="also post the profile + insights to the issue"
    )
    analyze.add_argument("--json", action="store_true")
    analyze.add_argument("--ledger", type=Path, default=Path(".mythings/ledger.jsonl"))
    analyze.add_argument("--engine", choices=sorted(_ENGINE_NAMES), default="noop")
    analyze.add_argument("--engine-model", help="model for --engine claude-cli")

    args = parser.parse_args(argv)
    engine = build_engine(args.engine, model=args.engine_model)

    analysist = Analysist(
        ledger=Ledger(args.ledger),
        repo=args.repo,
        engine=engine,
    )
    result = analysist.analyze(args.file, issue=args.issue, comment=args.comment)

    if args.json:
        print(
            json.dumps(
                {
                    "outcome": result.outcome,
                    "file": result.file,
                    "rows": result.rows,
                    "columns": result.columns,
                    "insights": result.insights,
                    "next_analysis": result.next_analysis,
                    "detail": result.detail,
                    "comment_url": result.comment_url,
                }
            )
        )
    else:
        print(result.insights or result.detail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
