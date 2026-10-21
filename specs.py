import json

from flask import Flask, Response, abort, jsonify, request
from werkzeug.exceptions import HTTPException

from versioning import BUMPS, next_version


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    @app.errorhandler(HTTPException)
    def http_error(e: HTTPException) -> tuple[Response, int, list[tuple[str, str]]]:
        # Keep headers such as `Allow` (405), drop the HTML Content-Type.
        headers = [(k, v) for k, v in e.get_headers() if k.lower() != "content-type"]
        return jsonify(error=e.description), e.code or 500, headers

    @app.get("/hello")
    def hello() -> Response:
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def next_version_route() -> Response:
        if not request.is_json:
            abort(415)
        data = request.get_data()
        # A chunked body is silently truncated at MAX_CONTENT_LENGTH by Werkzeug;
        # reading past the limit is what raises 413.
        request.stream.read(1)
        try:
            body = json.loads(data)
        except ValueError, RecursionError:
            abort(400, description="body must be valid JSON")
        if not isinstance(body, dict):
            abort(400, description="body must be a JSON object")
        tags = body.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            abort(400, description="tags must be a list of strings")
        bump = body.get("bump")
        if bump not in BUMPS:
            abort(400, description="bump must be one of: major, minor, patch")
        try:
            return jsonify(next=next_version(tags, bump))
        except ValueError as e:
            abort(400, description=str(e))

    return app
