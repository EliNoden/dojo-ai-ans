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

## POST /next-version

Computes the next version from a list of tags.

```bash
curl -X POST http://localhost:8080/next-version \
  -H "Content-Type: application/json" \
  -d '{"tags": ["v1.2.3", "1.3.0-rc.1"], "bump": "patch"}'
# {"next":"v1.3.0"}
```

Errors return status 400 with `{"error": "<message>"}`.

