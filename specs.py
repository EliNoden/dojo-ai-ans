import re

from flask import Flask, jsonify, request

SEMVER = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
BUMPS = ("major", "minor", "patch")


def next_version(tags, bump):
    # ponytail: only plain X.Y.Z (optional "v" prefix); pre-release/build tags are ignored
    versions = [tuple(map(int, m.groups())) for t in tags if (m := SEMVER.fullmatch(t))]
    major, minor, patch = max(versions, default=(0, 0, 0))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def post_next_version():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "body must be a JSON object"}), 400
        tags, bump = body.get("tags"), body.get("bump")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return jsonify({"error": "tags must be an array of strings"}), 400
        if bump not in BUMPS:
            return jsonify({"error": f"bump must be one of {', '.join(BUMPS)}"}), 400
        return jsonify({"next": next_version(tags, bump)})

    return app
