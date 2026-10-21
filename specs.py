import re

from flask import Flask, jsonify, request

IDENTS = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
NUM = r"0|[1-9][0-9]*"
TAG_RE = re.compile(rf"(v?)({NUM})\.({NUM})\.({NUM})(?:-({IDENTS}))?(?:\+{IDENTS})?")
BUMPS = ("major", "minor", "patch")


def parse_tag(tag):
    m = TAG_RE.fullmatch(tag)
    if not m:
        return None
    prefix, x, y, z, pre = m.groups()
    # Semver precedence: numeric ids < alphanumeric ids; final release > any pre-release.
    pre_key = (
        tuple((0, int(i), "") if i.isdigit() else (1, 0, i) for i in pre.split("."))
        if pre
        else ()
    )
    return (int(x), int(y), int(z), pre is None, pre_key, prefix == "v"), prefix


def next_version(tags, bump):
    (x, y, z, is_final, _, _), prefix = max(map(parse_tag, tags))
    # A pre-release base is not bumped, just terminated: 1.3.0-rc.1 -> 1.3.0
    if not is_final:
        pass
    elif bump == "major":
        x, y, z = x + 1, 0, 0
    elif bump == "minor":
        y, z = y + 1, 0
    else:
        z += 1
    return f"{prefix}{x}.{y}.{z}"


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def next_version_route():
        def error(message):
            return jsonify({"error": message}), 400

        body = request.get_json(force=True, silent=True)
        if not isinstance(body, dict):
            return error("body must be a JSON object")
        tags, bump = body.get("tags"), body.get("bump")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return error("tags must be a list of strings")
        if bump not in BUMPS:
            return error("bump must be one of: major, minor, patch")
        if not tags:
            return error("tags must not be empty")
        invalid = [t for t in tags if not parse_tag(t)]
        if invalid:
            return error(f"invalid tags: {', '.join(invalid)}")
        return jsonify({"next": next_version(tags, bump)})

    return app
