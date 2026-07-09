# my-data-analysist

[![CI](https://github.com/MyThingsLab/my-data-analysist/actions/workflows/ci.yml/badge.svg)](https://github.com/MyThingsLab/my-data-analysist/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/MyThingsLab/my-data-analysist/branch/main/graph/badge.svg)](https://codecov.io/gh/MyThingsLab/my-data-analysist) ![Python](https://img.shields.io/badge/python-3.11%2B-blue) [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Given a local CSV file, deterministically profiles it (schema/type inference,
row count, per-column null counts, basic numeric stats) and uses **one Engine
call** to write a short narrative plus one concrete follow-up analysis — a
stateless, single-file utility built for anyone who wants a quick, cited read
on a dataset without reaching for pandas.

## How it works

Deterministic pre-work (stdlib `csv`/`statistics` only — no pandas/numpy):

1. Size-cap the file first, before any parsing (50,000 rows / 10MB) — over
   the cap skips the Engine call entirely.
2. Sniff the CSV and read the header row.
3. Infer each column's type (`int`/`float`/`bool`/`str`) by sampling values.
4. Count total rows and, per column, null/empty count.
5. For numeric columns, compute mean/min/max/stdev over the non-null values.

If profiling succeeds, **one Engine call** turns the aggregated profile (never
raw row data) into `{insights, next_analysis}` — a 2-3 sentence narrative plus
exactly one suggested follow-up analysis. Against `NoopEngine`, both fields
are empty strings and only the raw profile is returned — no insights, same
honest degrade as MyScraper's `fields.raw_text`.

No `Workspace` worktree — read-only, no edits, no PR. The only side effect is
an optional `--comment`, which posts the profile + insights to a GitHub issue
as `Action(kind="bash", ...)` routed through `Policy` (`ALLOW` by default).
Writes exactly one `kind=analysis` ledger entry per run.

## Usage

```bash
mydataanalysist analyze --file data.csv --json
mydataanalysist analyze --file data.csv --repo owner/name --issue 12 --comment
```

## In the fleet loop

Standalone today (no other tool calls it yet) — a building block designed per
the [design doc](../my-things-core/docs/tools/my-data-analysist.md). See the
[org README](../README.md) for how the shipped tools chain together.

## Install (development)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ../my-things-core -e ".[dev]"
pytest
```

## License

MIT — see [`LICENSE`](LICENSE).
