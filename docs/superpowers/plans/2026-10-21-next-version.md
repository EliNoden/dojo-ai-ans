# Next-version route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /next-version` computing the next SemVer version from a list of tags.

**Architecture:** Pure logic in `versioning.py` (no Flask import) parses tags with the `semver` lib after stripping an optional lowercase `v`, picks the max, bumps with `Version.next_version`. `specs.py` validates the JSON body, delegates, and maps `ValueError` to 400. Global error handlers render every HTTP error as `{"error": ...}`.

**Tech Stack:** Python 3.14, Flask, `semver` 3.x, pytest, ruff, mypy, mutmut, uv.

**Spec:** `docs/specs/next-version.md` (read it: the edge-case table is the test oracle).

## Global Constraints

- Follow `CLAUDE.md` (TDD, KISS, Definition of Done) — tests first, see them fail.
- Runtime dep added: `semver` only (`uv add semver`). Dev deps: `uv add --dev mypy mutmut`.
- Error body always `{"error": "<message>"}`; exact messages:
  - `"body must be valid JSON"`, `"body must be a JSON object"`, `"tags must be a list of strings"`,
    `"bump must be one of: major, minor, patch"`, `"tags must not be empty"`, `"invalid tags: <t1>, <t2>"`.
- Validation order: JSON → object → tags type → bump → empty → invalid tags.
- `MAX_CONTENT_LENGTH = 1024 * 1024`; non-JSON `Content-Type` → 415; 404/405 JSON (405 keeps `Allow`).
- No `# type: ignore` / `Any` without justification comment.

## Review Focus

1. Prefix tie independent of input order: `["1.2.3","v1.2.3"]` and `["v1.2.3","1.2.3"]` → `v1.2.4`.
2. Final beats pre-release even when the pre-release has `v`: `["v1.3.0-rc.1","1.3.0"]` patch → `1.3.1`.
3. Unicode digits / uppercase / whitespace rejected: `"١.2.3"`, `"V1.2.3"`, `" 1.2.3"`, `"vv1.2.3"`, `"v"`.
4. `bump` of wrong JSON type (`["patch"]`, `{}`, `1`, `null`) → 400, never 500; `tags` containing `null`/`1`/`[]` → 400.
5. Malformed / non-UTF-8 / deeply nested (`"[" * 100000`) JSON with JSON content type → 400, not 500.

---

### Task 1: Pure versioning logic

**Files:**
- Create: `versioning.py`
- Test: `tests/test_versioning.py`
- Modify: `pyproject.toml` (deps; `[tool.mutmut]` with `paths_to_mutate = ["versioning.py"]`, tests dir `tests/`; `[tool.mypy]` `strict = true`, exclude `.venv`/`mutants`)
- Modify: `.gitignore` (`mutants/`, `.mutmut-cache`)

**Interfaces:**
- Produces: `Bump = Literal["major", "minor", "patch"]`, `BUMPS: tuple[Bump, ...] = ("major", "minor", "patch")`,
  `next_version(tags: list[str], bump: Bump) -> str` — raises `ValueError("tags must not be empty")` or
  `ValueError("invalid tags: a, b")`.

- [x] **Step 1: Add deps** — `uv add semver && uv add --dev mypy mutmut`.
- [x] **Step 2: Write failing tests** — one `pytest.mark.parametrize` table over every 200 row of the spec table
  (`assert next_version(tags, bump) == expected`) plus Review Focus 1–3; one test per error:
  `with pytest.raises(ValueError, match=r"^tags must not be empty$")`, and
  `next_version(["1.2", "1.2.3", "V1.2.3", "01.2.3"], "patch")` → `match=r"^invalid tags: 1\.2, V1\.2\.3, 01\.2\.3$"`,
  `["x","x"]` → `"invalid tags: x, x"`, and a parametrized list of each invalid string from the spec + Review Focus 3
  asserting `str(exc) == f"invalid tags: {tag}"`.
- [x] **Step 3: Run** `uv run pytest tests/test_versioning.py -v` → FAIL (`ModuleNotFoundError: versioning`).
- [x] **Step 4: Implement** `next_version` in `versioning.py`. Parse: `has_v = tag.startswith("v")`, `semver.Version.parse(tag.removeprefix("v"))` (catch `ValueError`), collect invalids in input order.
  Pick highest with `max(parsed, key=lambda p: (p.version, p.has_v))` — `Version` is orderable and ignores build in comparison; `has_v` as tiebreaker makes `v` win. Result: `("v" if has_v else "") + str(version.next_version(bump))` (`next_version` drops build and terminates pre-releases npm-style).
- [x] **Step 5: Run** tests → PASS. `uv run mypy .`, `uv run ruff format . && uv run ruff check --fix` clean.
- [x] **Step 6: Mutation** — `uv run mutmut run && uv run mutmut results`: zero survivors on `versioning.py` (add tests or remove code otherwise).
- [x] **Step 7: Commit** `feat: add next-version computation logic`.

### Task 2: HTTP route + JSON error handlers

**Files:**
- Modify: `specs.py`
- Test: `tests/test_api.py` (Flask test client), `tests/test_server.py` (real server)
- Modify: `README.md` (route + curl example, test/lint commands)

**Interfaces:**
- Consumes: `next_version`, `BUMPS` from `versioning`.
- Produces: `create_app() -> Flask` with `POST /next-version`.

- [ ] **Step 1: Write failing client tests** in `tests/test_api.py` (fixture `client = create_app().test_client()`):
  - nominal: `post("/next-version", json={"tags": ["v1.2.3", "1.0.0"], "bump": "patch"})` → 200, `is_json`, `{"next": "v1.2.4"}`.
  - each exact error message from Global Constraints with status 400, e.g. `data=b"{bad", content_type="application/json"` → `"body must be valid JSON"`; `data=b"\xff\xfe"` → same; `data=b"[" * 100000` → 400 (any message); `json=[]` → `"body must be a JSON object"`; tags `None`/`"1.2.3"`/`[1]`/`[None]`/missing → tags message; bump missing/`"Patch"`/`["patch"]`/`{}`/`1`/`None` → bump message; `[]` tags → empty message; invalid tags message.
  - `data="x", content_type="text/plain"` → 415 JSON; `json={"tags": ["1.2.3"] * 200000, "bump": "patch"}` (>1 MiB) → 413 JSON; `get("/next-version")` → 405 JSON with `"POST" in headers["Allow"]`; `get("/nope")` → 404 JSON.
- [ ] **Step 2: Run** → FAIL (404 on route).
- [ ] **Step 3: Implement** in `specs.py`: `app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024`;
  `@app.errorhandler(HTTPException)` returning `jsonify(error=e.description)`, `e.code`, and `e.get_headers()` minus Content-Type (keeps `Allow`).
  Route: `if not request.is_json: abort(415)`; `body = request.get_json(silent=True)` — but distinguish malformed from `null`: use `json.loads(request.get_data())` in try/except `(ValueError, RecursionError)` → 400 `"body must be valid JSON"` (`get_data` raises 413 itself). Then type checks in spec order, `try: next_version(...) except ValueError as e: 400 str(e)`.
  Helper `bad_request(msg)` = `abort(400, description=msg)` via the global handler. Narrow `bump` with `bump not in BUMPS` then `cast(Bump, bump)` (comment why).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Real-server test** `tests/test_server.py`: module fixture starts `werkzeug.serving.make_server("127.0.0.1", 0, create_app())` in a thread, uses `urllib.request` to assert nominal 200 + `{"next": ...}` and one 400 (invalid tags) + one 415, checking `Content-Type: application/json`. Shut down in teardown.
- [ ] **Step 6: Quality gates** — `uv run pytest`, ruff, mypy, mutmut (still zero survivors).
- [ ] **Step 7: README** — document `POST /next-version` with a curl example and the dev commands.
- [ ] **Step 8: Commit** `feat: add POST /next-version route`.
