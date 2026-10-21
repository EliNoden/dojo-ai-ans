import re

from flask import Flask, jsonify, request

# Strict release tags only: "1.2.3" or "v1.2.3". Pre-releases and other tags are ignored.
TAG_PATTERN = re.compile(r"^(v?)(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
BUMPS = ("major", "minor", "patch")


def next_version(tags, bump):
    """Return the next version after the highest valid tag.

    Keeps the "v" prefix of the highest tag. With no valid tag, starts from 0.0.0.
    """
    versions = []
    for tag in tags:
        match = TAG_PATTERN.match(tag.strip())
        if match:
            prefix, major, minor, patch = match.groups()
            versions.append(((int(major), int(minor), int(patch)), prefix))

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
    def next_version_route():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "body must be a JSON object"}), 400

        tags = body.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return jsonify({"error": "'tags' must be an array of strings"}), 400

        bump = body.get("bump")
        if bump not in BUMPS:
            return jsonify({"error": "'bump' must be one of: major, minor, patch"}), 400

        return jsonify({"next": next_version(tags, bump)})

    return app
