import re

from flask import Flask, jsonify, request

_IDENTIFIER = r"[0-9A-Za-z-]+"
_NUMBER = r"(?:0|[1-9][0-9]*)"
_TAG_PATTERN = re.compile(
    rf"(?P<prefix>v)?"
    rf"(?P<major>{_NUMBER})\.(?P<minor>{_NUMBER})\.(?P<patch>{_NUMBER})"
    rf"(?:-(?P<pre>{_IDENTIFIER}(?:\.{_IDENTIFIER})*))?"
    rf"(?:\+{_IDENTIFIER}(?:\.{_IDENTIFIER})*)?"
)

_BUMPS = ("major", "minor", "patch")


def _parse_tag(tag):
    """Return (sort_key, prefix, core, is_prerelease) for a valid tag, None otherwise."""
    match = _TAG_PATTERN.fullmatch(tag)
    if match is None:
        return None
    core = tuple(int(match[name]) for name in ("major", "minor", "patch"))
    pre = match["pre"]
    if pre is None:
        pre_key = ()
    else:
        pre_key = tuple(
            (0, int(part), "") if part.isascii() and part.isdigit() else (1, 0, part)
            for part in pre.split(".")
        )
    # A final version (True) is greater than any pre-release (False) of the same X.Y.Z.
    key = (*core, pre is None, pre_key)
    return key, match["prefix"] or "", core, pre is not None


def _bump(core, is_prerelease, bump):
    major, minor, patch = core
    if bump == "major":
        if is_prerelease and minor == 0 and patch == 0:
            return major, minor, patch
        return major + 1, 0, 0
    if bump == "minor":
        if is_prerelease and patch == 0:
            return major, minor, patch
        return major, minor + 1, 0
    if is_prerelease:
        return major, minor, patch
    return major, minor, patch + 1


def _error(message):
    return jsonify({"error": message}), 400


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def next_version():
        body = request.get_json(force=True, silent=True)
        if not isinstance(body, dict):
            return _error("body must be a JSON object")

        tags = body.get("tags")
        if tags is None:
            return _error("tags is required")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return _error("tags must be a list of strings")

        bump = body.get("bump")
        if bump is None:
            return _error("bump is required")
        if not isinstance(bump, str) or bump not in _BUMPS:
            return _error("bump must be one of: major, minor, patch")

        if not tags:
            return _error("tags must not be empty")

        parsed = [_parse_tag(tag) for tag in tags]
        invalid = [tag for tag, result in zip(tags, parsed) if result is None]
        if invalid:
            return _error("invalid tags: " + ", ".join(invalid))

        # On equal versions, the "v" prefix wins.
        _, prefix, core, is_prerelease = max(parsed, key=lambda r: (r[0], r[1] == "v"))
        major, minor, patch = _bump(core, is_prerelease, bump)
        return jsonify({"next": f"{prefix}{major}.{minor}.{patch}"})

    return app
