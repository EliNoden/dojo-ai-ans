import json

from flask import Flask, Response, abort, jsonify, request
from werkzeug.exceptions import HTTPException

from versioning import EmptyTagsError, InvalidTagsError, next_version

BUMPS = ("major", "minor", "patch")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    @app.errorhandler(HTTPException)
    def json_error(error: HTTPException) -> Response:
        # Keep the status and headers (e.g. Allow on 405) but not the HTML body:
        # get_response() would render it and fail on lone surrogates.
        # json.dumps escapes them (ensure_ascii).
        response = Response(
            json.dumps({"error": error.description}),
            status=error.code,
            headers=error.get_headers(),
        )
        response.content_type = "application/json"
        return response

    @app.get("/hello")
    def hello() -> Response:
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def next_version_route() -> Response:
        if not request.is_json:
            abort(415, "Content-Type must be application/json")
        # A body with Content-Length gets its 413 from Werkzeug up front. A body
        # without one (chunked) is silently cut at MAX_CONTENT_LENGTH; reading past
        # the cut makes Werkzeug raise the 413. Only do that extra read when there is
        # no Content-Length: gunicorn sets wsgi.input_terminated on every request,
        # so the extra read would also reject a Content-Length body of exactly 1 MiB.
        if request.content_length is None:
            request.get_data()
            request.stream.read()
        try:
            body = request.get_json(silent=True)
        except RecursionError:  # too deeply nested: not a ValueError, so not silenced
            body = None
        if not isinstance(body, dict):
            abort(400, "body must be a JSON object")
        tags = body.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            abort(400, "tags must be a list of strings")
        bump = body.get("bump")
        if bump not in BUMPS:
            abort(400, "bump must be one of: " + ", ".join(BUMPS))
        try:
            return jsonify({"next": next_version(tags, bump)})
        except (EmptyTagsError, InvalidTagsError) as error:
            abort(400, str(error))

    return app
