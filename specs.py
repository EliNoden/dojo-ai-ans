from flask import Flask, jsonify


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        return jsonify({"message": "Hello, the specs server is running"})

    return app
