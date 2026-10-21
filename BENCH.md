# Bench `/next-version`

Scores any implementation of `POST /next-version` over HTTP, so iterations (light prompt, full prompt, prompt + skills...) can be compared.

## Contract (given in every prompt)

`POST /next-version`, body `{"tags": [...], "bump": "major|minor|patch"}`, response `{"next": "<version>"}`.

## Categories

- `core`: same result under any reasonable reading of the contract (basic bumps, numeric sort, build metadata, big numbers, invalid input → 4xx and never 5xx, `405` with `Allow`). Measures the effect of tooling (TDD, CLAUDE.md).
- `intent`: product choices of `docs/specs/next-version.md` (optional `v`, prefix of the max, tie → `v`, pre-releases counted, `invalid tags: ...` and `tags must not be empty` errors). Measures the effect of specs. Ids ending in `-rewritten` are `tests/test_test.py` cases whose expectation was recomputed to match the spec.
- `hardening`: HTTP robustness rarely asked for (JSON `{"error"}` everywhere, 404/405 in JSON, 415 on non-JSON Content-Type, 413 over 1 MB). Measures whether the agent thinks of it alone.

## Run

```bash
# in the iteration's checkout
uv run gunicorn -w 2 -b 0.0.0.0:8080 "specs:create_app()" &
git show bench:bench.py > /tmp/bench.py
uv run --with requests python /tmp/bench.py            # or: ... /tmp/bench.py http://host:port
```

Output: one `FAIL [category] id: status body` line per failed case, then `passed/total (%)` per category and in total.
Exit code is 0 whenever the server answers (it's a score, not a gate) and 2 when the server is unreachable.
