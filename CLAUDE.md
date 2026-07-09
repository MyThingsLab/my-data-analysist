# my-data-analysist — agent instructions

You are developing **my-data-analysist**, a MyThingsLab My[X] tool.

**Inherited rules:** obey [`./HARNESS.md`](./HARNESS.md) in full — the vendored
MyThingsLab build-harness rules. Do not restate or override them. Anything not
covered here defers to `HARNESS.md`, then `my-things-core/docs/CONVENTIONS.md`.

## This tool

- **Purpose:** given a local CSV file, deterministically profile it
  (schema/type inference, row count, per-column null counts, basic numeric
  stats) and use the Engine to write a short narrative + one concrete
  follow-up suggestion (`mydataanalysist analyze`). v0 input scope is a local
  file path only — no issue-attachment parsing, no URLs.
- **The single Engine call:** "given this deterministic CSV profile, write a
  short narrative plus one concrete follow-up analysis" — replies with
  `{insights, next_analysis}`, a 2-3 sentence narrative plus exactly one
  suggested follow-up analysis. Input is the profile only, never raw row
  data: `context = {"file": str, "rows": int, "columns": {...}}`. Against
  `NoopEngine`: no insights — `insights`/`next_analysis` are empty strings,
  only the raw profile is returned.
- **Invariants / rules:**
  - Deterministic pre-work is stdlib `csv`/`statistics` only — no
    pandas/numpy, per the harness's dependency-free-runtime rule.
  - Size-capped at 50,000 rows / 10MB, checked **before** parsing — over the
    cap skips the Engine call entirely, `outcome=skipped`.
  - No raw row values ever reach the Engine prompt — only the aggregated
    profile (types, counts, stats).
  - **No `Workspace`, no PR.** Read-only utility: output to stdout
    (`--json`) and, if `--issue` + `--repo` + `--comment` are given, an
    issue comment via `Action(kind="bash", ...)` routed through
    `Policy.evaluate()`. Never commits to a repo, never writes back to the
    source file.
  - Stateless: each run is independent, no cross-run corpus, writes exactly
    one `kind=analysis` ledger entry per run.
- **Backlog label:** `my-data-analysist`.

See the design plan for full detail:
[`my-things-core/docs/tools/my-data-analysist.md`](../my-things-core/docs/tools/my-data-analysist.md).
