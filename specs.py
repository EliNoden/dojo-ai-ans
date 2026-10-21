from flask import Flask, jsonify, request

from versions import BUMPS, next_version


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def next_version_route():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _error("body must be a JSON object (Content-Type: application/json)")

        tags = body.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return _error("tags must be a list of strings")

        bump = body.get("bump")
        if bump not in BUMPS:
            return _error("bump must be one of: major, minor, patch")

        try:
            return jsonify({"next": next_version(tags, bump)})
        except ValueError as e:
            return _error(str(e))

    return app


def _error(message):
    return jsonify({"error": message}), 400
