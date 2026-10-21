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

Computes the next semver version from a list of git tags.

```bash
curl -X POST http://localhost:8080/next-version \
  -H "Content-Type: application/json" \
  -d '{"tags": ["v1.2.3", "v1.10.0", "v1.9.9"], "bump": "minor"}'
# {"next":"v1.11.0"}
```

- `tags` : tags in the form `X.Y.Z` or `vX.Y.Z`. Other tags (pre-releases, arbitrary names) are ignored.
- `bump` : `major`, `minor` or `patch`.
- The highest version is bumped, keeping its `v` prefix. With no valid tags, the base is `0.0.0`.
- Invalid body → `400` with `{"error": "..."}`.
