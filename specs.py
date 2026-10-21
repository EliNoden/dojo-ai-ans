import re

from flask import Flask, jsonify, request

SEMVER_TAG = re.compile(r"^(v?)(\d+)\.(\d+)\.(\d+)$")
BUMPS = ("major", "minor", "patch")


def next_version(tags, bump):
    versions = [
        (tuple(int(part) for part in match.groups()[1:]), match.group(1))
        for match in (SEMVER_TAG.match(tag) for tag in tags)
        if match
    ]
    (major, minor, patch), prefix = max(versions, default=((0, 0, 0), ""))

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
    def post_next_version():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Body must be a JSON object"}), 400

        tags = body.get("tags")
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            return jsonify({"error": "'tags' must be an array of strings"}), 400

        bump = body.get("bump")
        if bump not in BUMPS:
            return jsonify({"error": "'bump' must be one of: major, minor, patch"}), 400

        return jsonify({"next": next_version(tags, bump)})

    return app
