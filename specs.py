import json

from flask import Flask, Response, abort, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response as WerkzeugResponse

from versioning import next_version

ERROR_MESSAGES = {
    404: "not found",
    405: "method not allowed",
    413: "request body too large",
    415: "content type must be application/json",
}
BUMPS = ("major", "minor", "patch")
FIELDS = ("tags", "bump")


def bad_request(message: str) -> tuple[Response, int]:
    return jsonify({"error": message}), 400


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    @app.errorhandler(HTTPException)
    def handle_http_error(e: HTTPException) -> WerkzeugResponse:
        response = e.get_response()
        message = ERROR_MESSAGES.get(response.status_code, e.name.lower())
        response.data = json.dumps({"error": message})
        response.content_type = "application/json"
        return response

    @app.get("/hello")
    def hello() -> Response:
        return jsonify({"message": "Hello, the specs server is running"})

    @app.post("/next-version")
    def next_version_route() -> Response | tuple[Response, int]:
        if not request.is_json:
            abort(415)
        try:
            body = json.loads(request.get_data().decode())
        except ValueError, RecursionError:
            return bad_request("body must be valid JSON")
        if not isinstance(body, dict):
            return bad_request("body must be a JSON object")
        unknown = [field for field in body if field not in FIELDS]
        if unknown:
            return bad_request(f"unknown fields: {', '.join(unknown)}")
        if "tags" not in body:
            return bad_request("tags is required")
        tags = body["tags"]
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return bad_request("tags must be a list of strings")
        if "bump" not in body:
            return bad_request("bump is required")
        bump = body["bump"]
        if bump not in BUMPS:
            return bad_request(f"bump must be one of: {', '.join(BUMPS)}")
        try:
            return jsonify({"next": next_version(tags, bump)})
        except ValueError as e:
            return bad_request(str(e))

    return app
