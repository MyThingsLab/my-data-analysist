from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mythings.engine import Engine, EngineRequest, NoopEngine
from mythings.github import Runner, _gh
from mythings.isolation import in_github_actions
from mythings.ledger import Ledger
from mythings.policy import ALLOW, Action, Decision, Policy, PolicyResult

from mydataanalysist.profiler import ProfileResult, profile_csv

_ENGINE_SYSTEM = (
    "You write a short narrative about a CSV profile and suggest one follow-up "
    'analysis. Reply with only a JSON object: {"insights": str, "next_analysis": '
    "str}. insights must be 2-3 sentences; next_analysis must name exactly one "
    "concrete follow-up analysis. Never invent data not present in the profile."
)


class _AllowPolicy:
    def evaluate(self, action: Action) -> PolicyResult:
        return ALLOW


@dataclass(frozen=True)
class Result:
    outcome: str  # success | skipped
    file: str
    rows: int = 0
    columns: dict[str, Any] | None = None
    insights: str = ""
    next_analysis: str = ""
    detail: str = ""
    comment_url: str | None = None


class Analysist:
    def __init__(
        self,
        *,
        ledger: Ledger,
        repo: str | None = None,
        runner: Runner = _gh,
        engine: Engine | None = None,
        policy: Policy | None = None,
        max_rows: int = 50_000,
        max_bytes: int = 10_000_000,
    ) -> None:
        self.ledger = ledger
        self.repo = repo
        self.runner = runner
        self.engine: Engine = engine or NoopEngine()
        self.policy: Policy = policy or _AllowPolicy()
        self.max_rows = max_rows
        self.max_bytes = max_bytes

    def analyze(
        self,
        file: str | Path,
        *,
        issue: int | None = None,
        comment: bool = False,
    ) -> Result:
        file = Path(file)
        profile = profile_csv(file, max_rows=self.max_rows, max_bytes=self.max_bytes)
        if not profile.ok:
            result = Result(
                outcome="skipped",
                file=str(file),
                detail=f"skipped: {profile.reason}",
            )
            self._record(result)
            return result

        columns = profile.columns_as_dict()
        reply = self._analyze(file, profile, columns)
        comment_url = self._comment(issue, file, profile, reply) if comment else None

        result = Result(
            outcome="success",
            file=str(file),
            rows=profile.rows,
            columns=columns,
            insights=reply["insights"],
            next_analysis=reply["next_analysis"],
            detail=f"profiled {file}",
            comment_url=comment_url,
        )
        self._record(result)
        return result

    def _analyze(
        self, file: Path, profile: ProfileResult, columns: dict[str, Any]
    ) -> dict[str, Any]:
        context = {"file": str(file), "rows": profile.rows, "columns": columns}
        prompt = "CSV profile:\n" + json.dumps(context, indent=2)
        reply = self.engine.run(
            EngineRequest(prompt=prompt, system=_ENGINE_SYSTEM, context=context)
        )
        parsed = _parse_reply(reply.text)
        if parsed is not None:
            return parsed
        return {"insights": "", "next_analysis": ""}

    def _comment(
        self,
        issue: int | None,
        file: Path,
        profile: ProfileResult,
        reply: dict[str, Any],
    ) -> str | None:
        if self.repo is None or issue is None:
            return None
        body_data = {
            "file": str(file),
            "rows": profile.rows,
            "columns": profile.columns_as_dict(),
            **reply,
        }
        body = f"Profiled {file}:\n\n```json\n{json.dumps(body_data, indent=2)}\n```"
        argv = ["issue", "comment", str(issue), "--repo", self.repo, "--body", body]
        action = Action(kind="bash", payload={"command": "gh " + " ".join(argv[:3])})
        decision = self.policy.evaluate(action).under(unattended=in_github_actions())
        if decision is not Decision.ALLOW:
            return None
        return self.runner(argv).strip() or None

    def _record(self, result: Result) -> None:
        self.ledger.record(
            tool="mydataanalysist",
            kind="analysis",
            outcome=result.outcome,
            detail=result.detail,
            file=result.file,
            rows=result.rows,
            columns=result.columns or {},
            comment_url=result.comment_url,
        )


def _parse_reply(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None

    insights = obj.get("insights") if isinstance(obj.get("insights"), str) else ""
    next_analysis = (
        obj.get("next_analysis") if isinstance(obj.get("next_analysis"), str) else ""
    )
    return {"insights": insights, "next_analysis": next_analysis}
