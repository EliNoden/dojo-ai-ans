import re

from flask import Flask, jsonify, request

TAG_PATTERN = re.compile(r"^(v?)(\d+)\.(\d+)\.(\d+)$")
BUMPS = ("major", "minor", "patch")


def compute_next_version(tags, bump):
    """Return the next version from the highest valid X.Y.Z (optionally v-prefixed) tag."""
    best = None
    for tag in tags:
        match = TAG_PATTERN.match(tag)
        if not match:
            continue
        version = tuple(int(part) for part in match.groups()[1:])
        if best is None or version > best[1]:
            best = (match.group(1), version)

    prefix, (major, minor, patch) = best if best else ("", (0, 0, 0))
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{prefix}{major}.{minor}.{patch}"


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def next_version():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Body must be a JSON object"}), 400

        tags = body.get("tags")
        bump = body.get("bump")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return jsonify({"error": "'tags' must be a list of strings"}), 400
        if bump not in BUMPS:
            return jsonify({"error": "'bump' must be one of: major, minor, patch"}), 400

        return jsonify({"next": compute_next_version(tags, bump)})

    return app
