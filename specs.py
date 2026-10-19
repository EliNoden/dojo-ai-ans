import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

load_dotenv()

# ponytail: in-memory refs, move to a file/DB if they need to change without a redeploy
REFS = {
    "branches": ["main", "develop"],
    "tags": ["2.1.0", "2.2.0.rc-1"],
}


def create_app():
    app = Flask(__name__)
    CORS(app, origins=[os.getenv("CLIENT_URL", "http://localhost:5173")])

    @app.get("/refs")
    def list_refs():
        return jsonify(REFS)

    return app
