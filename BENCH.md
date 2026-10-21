# Bench `/next-version`

Scores any implementation of `POST /next-version` over HTTP, so iterations (light prompt, full prompt, prompt + skills...) can be compared.

## Contract (given in every prompt)

`POST /next-version`, body `{"tags": [...], "bump": "major|minor|patch"}`, response `{"next": "<version>"}`.

## Categories

- `core` (54 cases): same result under any reasonable reading of the contract (basic bumps, numeric sort, build metadata, big numbers up to 1001 digits, a fixed sample of "next > every tag", invalid input → 4xx and never 5xx including JSON nested 100 000 levels deep, `405` with `Allow`). Measures the effect of tooling (TDD, CLAUDE.md).
- `intent` (36 cases): product choices of `docs/specs/next-version.md` (optional `v`, prefix of the max, tie → `v`, pre-releases counted with SemVer precedence and `semver` bump, `invalid tags: ...` and `tags must not be empty` errors). Measures the effect of specs. Ids ending in `-rewritten` are `tests/test_test.py` cases whose expectation was recomputed to match the spec.
- `hardening` (12 cases): HTTP robustness rarely asked for (5 representative bad inputs answer JSON `{"error": str}`; 404/405 in JSON, 415 on missing/`text/plain`/form Content-Type, 413 on a body over 1 MB). Measures whether the agent thinks of it alone.

## Run

```bash
# in the iteration's checkout
uv run gunicorn -w 2 -b 0.0.0.0:8080 "specs:create_app()" &
git fetch origin bench && git show origin/bench:bench.py > /tmp/bench.py && uv run --with requests python /tmp/bench.py
# other server: ... python /tmp/bench.py http://host:port
```

The run includes the heavy cases (a 1 MB body and a JSON array nested 100 000 levels deep); each request times out after 10 s.

Output: one `FAIL [category] id: status body` line per failed case, then `passed/total (%)` per category and in total.
Exit code is 0 whenever the server answers (it's a score, not a gate) and 2 when the server is unreachable.
