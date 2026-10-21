import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator

import pytest
from werkzeug.serving import make_server

from specs import create_app


@pytest.fixture(scope="module")
def base_url() -> Iterator[str]:
    server = make_server("127.0.0.1", 0, create_app())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()


def post(
    url: str, data: bytes, content_type: str = "application/json"
) -> tuple[int, str, object]:
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": content_type}, method="POST"
    )
    try:
        with urllib.request.urlopen(request) as response:
            return (
                response.status,
                response.headers["Content-Type"],
                json.load(response),
            )
    except urllib.error.HTTPError as e:
        return e.code, e.headers["Content-Type"], json.load(e)


def test_nominal(base_url: str) -> None:
    body = json.dumps({"tags": ["1.2.3", "v1.2.3"], "bump": "minor"}).encode()
    assert post(f"{base_url}/next-version", body) == (
        200,
        "application/json",
        {"next": "v1.3.0"},
    )


def test_invalid_tags(base_url: str) -> None:
    body = json.dumps({"tags": ["x", "1.2.3"], "bump": "patch"}).encode()
    assert post(f"{base_url}/next-version", body) == (
        400,
        "application/json",
        {"error": "invalid tags: x"},
    )


def test_not_json(base_url: str) -> None:
    status, content_type, body = post(f"{base_url}/next-version", b"x", "text/plain")
    assert (status, content_type) == (415, "application/json")
    assert isinstance(body, dict) and set(body) == {"error"}
