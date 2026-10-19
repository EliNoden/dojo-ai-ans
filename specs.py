import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

load_dotenv()


def create_app():
    app = Flask(__name__)
    CORS(app, origins=[os.getenv("CLIENT_URL", "http://localhost:5173")])

    @app.get("/hello")
    def hello():
        return jsonify({"message": "Hello, the specs server is running"})

    return app
