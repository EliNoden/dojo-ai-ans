from flask import Flask, Response, jsonify


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/hello")
    def hello() -> Response:
        return jsonify({"message": "Hello, the specs server is running"})

    return app
