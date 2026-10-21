import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterable, Iterator

import pytest
from werkzeug.serving import make_server

from specs import create_app

BIG = json.dumps({"tags": ["1.2.3"] * 200000, "bump": "patch"}).encode()


@pytest.fixture(scope="module")
def base_url() -> Iterator[str]:
    server = make_server("127.0.0.1", 0, create_app())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()


def chunked(data: bytes) -> Iterable[bytes]:
    # An iterable body without Content-Length makes urllib send it chunked.
    return iter([data[i : i + 65536] for i in range(0, len(data), 65536)])


@pytest.mark.parametrize(
    ("method", "path", "data", "content_type", "status", "body"),
    [
        (
            "POST",
            "/next-version",
            b'{"tags": ["1.2.3", "v1.2.3"], "bump": "minor"}',
            "application/json",
            200,
            {"next": "v1.3.0"},
        ),
        (
            "POST",
            "/next-version",
            b'{"tags": ["x", "1.2.3"], "bump": "patch"}',
            "application/json",
            400,
            {"error": "invalid tags: x"},
        ),
        (
            "POST",
            "/next-version",
            b"{bad",
            "application/json",
            400,
            {"error": "body must be valid JSON"},
        ),
        ("POST", "/next-version", b"x", "text/plain", 415, None),
        ("POST", "/next-version", BIG, "application/json", 413, None),
        ("POST", "/next-version", chunked(BIG), "application/json", 413, None),
        ("GET", "/next-version", None, None, 405, None),
        ("GET", "/nope", None, None, 404, None),
    ],
    ids=[
        "nominal",
        "invalid-tags",
        "malformed",
        "415",
        "413-content-length",
        "413-chunked",
        "405",
        "404",
    ],
)
def test_route(
    base_url: str,
    method: str,
    path: str,
    data: bytes | Iterable[bytes] | None,
    content_type: str | None,
    status: int,
    body: dict[str, str] | None,
) -> None:
    headers = {"Content-Type": content_type} if content_type else {}
    request = urllib.request.Request(
        base_url + path, data=data, headers=headers, method=method
    )
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as e:
        response = e
    with response:
        assert response.status == status
        assert response.headers["Content-Type"] == "application/json"
        payload = json.load(response)
        if status == 405:
            assert "POST" in response.headers["Allow"]
    if body is None:
        assert set(payload) == {"error"}
    else:
        assert payload == body
