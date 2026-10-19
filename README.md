# Specs server

The documentation of the server for the specs services.

## Install

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Optional: set `CLIENT_URL` (CORS origin, default `http://localhost:5173`) in a `.env` file.

## Local run

```bash
uv run gunicorn -w 2 -b 0.0.0.0:8080 "specs:create_app()" --timeout 180 --log-level=debug
```

Server listens on http://localhost:8080. Check it runs:

```bash
curl http://localhost:8080/hello
# {"message":"Hello, the specs server is running"}
```

## Dev

Run tests:

```bash
uv run pytest
```

Before committing, make sure you run `ruff`.

```bash
uv run ruff format .
uv run ruff check --fix
```
