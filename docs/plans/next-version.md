# Plan: `POST /next-version`

Spec: `docs/specs/next-version.md` (the source of truth for rules, messages and edge cases).
Follow CLAUDE.md strictly: TDD (write the test, watch it fail for the right reason, then implement), KISS, ruff, mypy, mutmut.

## Facts already checked

- `semver` 3.1.0 (`semver.Version`): `Version.is_valid` / `Version.parse` reject
  `01.2.3`, `1.2.3-01`, `1.2.3-rc..1`, `1.2.3+`, `1.2.3-`, `1.2`, `" 1.2.3"` and
  `"1.2.3\n"`. `compare` ignores build metadata, and a pre-release sorts below
  its final version. Only the `v` prefix is handled by our code: strip at most
  one lowercase `v`, so `vv1.2.3` stays invalid.

## Steps

### 0. Tooling
- `uv add semver`
- `uv add --dev mypy mutmut`
- In `pyproject.toml`:
  - mutmut: run only on `versioning.py`.
  - mypy: `strict = true`; the code must pass, test files included.

### 1. Business logic: `versioning.py` (pure, no Flask)
Public API: `next_version(tags: list[str], bump: Literal["major","minor","patch"]) -> str`.
- It raises `InvalidTagsError(tags: list[str])` for invalid tags (input order, repeats kept),
  and `ValueError("tags must not be empty")` for an empty list (or one dedicated exception type; keep it simple).
- Parse each tag into `(prefix, Version)`.
- Base = the max of `(version, prefix == "v")`, compared with `Version` order
  (build ignored) and then by "has `v`", so `v` wins a tie.
- If the base has a pre-release, the result is `X.Y.Z` with no bump.
  Otherwise use `bump_major` / `bump_minor` / `bump_patch`.
- Return `prefix + f"{major}.{minor}.{patch}"` (no pre-release, no build).
- Tests in `tests/test_versioning.py`: every logic row of the spec's edge-case
  table. A small parametrized hypothesis test is welcome if cheap
  (e.g. the result is always a valid final version above every input), but optional.

### 2. HTTP layer: `specs.py`
- Global error handlers: `HTTPException` → `{"error": e.description}` with the
  same status and headers (keeps `Allow` on 405).
- `MAX_CONTENT_LENGTH = 1 MB` → 413 JSON.
- `POST /next-version`:
  1. `Content-Type` not JSON (`request.is_json` false) → 415.
  2. `request.get_json(silent=True)`; also catch `RecursionError` /
     `UnicodeDecodeError` if they leak. If the result is not a `dict`, return
     400 `body must be a JSON object`.
  3. `tags` is not a `list` of only `str` → 400 `tags must be a list of strings`.
  4. `bump` not in `{"major","minor","patch"}` → 400 `bump must be one of: major, minor, patch`
     (watch for non-hashable values such as lists or dicts: check `isinstance(str)` first).
  5. Delegate to `next_version`. Map its exceptions to 400 with the spec
     messages (`tags must not be empty`, then `invalid tags: a, b`).
- Annotate `create_app() -> Flask`. Handlers stay thin.

### 3. HTTP tests
- `tests/test_api.py` with the Flask `test_client`: nominal case; each error in
  the table, including priority (`[]` with a bad bump → bump error);
  malformed JSON; non-UTF-8 bytes; deep nesting (e.g. `"[" * 100000`);
  `text/plain` → 415; > 1 MB → 413; GET → 405 with `Allow`; unknown route → 404.
  Every error body is `{"error": ...}` JSON.
- `tests/test_server.py`: start gunicorn for real on a free port (fixture with
  `subprocess`, wait until `/hello` responds, then terminate). Use `urllib`
  from the stdlib for the nominal case plus a 400, 415 and 405.

### 4. Quality gates (Definition of Done)
- `uv run pytest`, `uv run ruff format . && uv run ruff check --fix`, `uv run mypy .`
- `uv run mutmut run && uv run mutmut results`: no surviving mutant on `versioning.py`.
- README: document `POST /next-version` with a curl example and the error format.

### 5. Out of scope for the implementation agent
- The manual `curl` check and the final review are done by the separate
  testing agent.
- Do not commit.
