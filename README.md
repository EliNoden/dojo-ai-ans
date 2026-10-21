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

Computes the next version from a list of tags (`X.Y.Z`, optional `v` prefix; other tags are ignored). Starts from `0.0.0` if no valid tag.

```bash
curl -X POST http://localhost:8080/next-version \
  -H "Content-Type: application/json" \
  -d '{"tags": ["v1.2.3", "v1.10.0"], "bump": "minor"}'
# {"next":"v1.11.0"}
```

`bump` is `major`, `minor` or `patch`. Invalid body returns `400`.

