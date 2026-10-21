# Specs server

The documentation of the server for the specs services.

## Install

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Local run

```bash
uv run gunicorn -w 2 -b 0.0.0.0:8080 "specs:create_app()" --timeout 180 --log-level=debug
```

Server listens on http://localhost:8080. Check it runs:

```bash
curl http://localhost:8080/hello
# {"message":"Hello, the specs server is running"}
```


## Routes

### `POST /next-version`

Returns the next release tag from the existing git tags and a bump type (`major`, `minor` or `patch`). SemVer 2.0 precedence, npm bump semantics, and the `v` prefix of the highest tag is kept.

```bash
curl -i -X POST http://localhost:8080/next-version \
  -H 'Content-Type: application/json' \
  -d '{"tags": ["v1.2.3", "1.3.0-rc.1"], "bump": "patch"}'
# HTTP/1.1 200 OK
# Content-Type: application/json
# {"next":"1.3.0"}
```

Errors are JSON `{"error": "<message>"}` (400, 404, 405, 413, 415). Full rules, error messages and edge cases: [docs/specs/next-version.md](docs/specs/next-version.md).

## Dev

```bash
uv sync                                     # install
uv run pytest                               # tests (unit, test client, live gunicorn server)
uv run ruff format . && uv run ruff check --fix
uv run mypy .                               # typing
uv run mutmut run && uv run mutmut results  # mutation testing (versioning.py)
```
