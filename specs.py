from flask import Flask, jsonify, request

from versions import BUMPS, bump, highest, parse_tag


def _error(message):
    return jsonify({"error": message}), 400


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def next_version():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _error("body must be a JSON object (Content-Type: application/json)")

        tags = body.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return _error("tags must be a list of strings")

        kind = body.get("bump")
        if kind not in BUMPS:
            return _error("bump must be one of: major, minor, patch")

        if not tags:
            return _error("tags must not be empty")

        parsed = [parse_tag(t) for t in tags]
        invalid = [t for t, v in zip(tags, parsed) if v is None]
        if invalid:
            return _error(f"invalid tags: {', '.join(invalid)}")

        return jsonify({"next": bump(highest(parsed), kind)})

    return app
