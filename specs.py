from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import (
    BadRequest,
    HTTPException,
    RequestEntityTooLarge,
    UnsupportedMediaType,
)

from versions import next_version

MAX_CONTENT_LENGTH = 1024 * 1024


def _json_object() -> dict[str, object]:
    if not request.is_json:
        raise UnsupportedMediaType()
    # Werkzeug silently truncates a chunked body at its limit instead of
    # raising; its limit is one byte above ours so that overflow is detectable.
    if len(request.get_data()) > MAX_CONTENT_LENGTH:
        raise RequestEntityTooLarge()
    try:
        body = request.get_json(silent=True)
    except RecursionError:  # very deeply nested JSON
        body = None
    if not isinstance(body, dict):
        raise BadRequest("body must be a JSON object")
    return body


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH + 1

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> Response:
        response = jsonify({"error": error.description})
        response.status_code = error.code or 500
        # keep headers such as Allow (error.get_response() would HTML-encode
        # the description and fail on lone surrogates)
        response.headers.extend(
            (name, value)
            for name, value in error.get_headers()
            if name != "Content-Type"
        )
        return response

    @app.get("/hello")
    def hello() -> Response:
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def post_next_version() -> Response:
        body = _json_object()
        tags = body.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise BadRequest("tags must be a list of strings")
        try:
            return jsonify({"next": next_version(tags, body.get("bump"))})
        except ValueError as error:
            raise BadRequest(str(error)) from error

    return app
