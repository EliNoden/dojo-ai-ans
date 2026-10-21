import http.client
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


@pytest.fixture(scope="module")
def base_url() -> Iterator[str]:
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "gunicorn", "-b", f"127.0.0.1:{port}"]
        + ["specs:create_app()"]
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"{url}/hello", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("server did not start")
        yield url
    finally:
        server.terminate()
        server.wait(timeout=10)


def send(
    url: str,
    method: str = "POST",
    data: bytes | None = None,
    content_type: str = "application/json",
) -> tuple[int, dict[str, str], Any]:
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": content_type}
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers), json.load(response)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), json.load(e)


def assert_json(
    result: tuple[int, dict[str, str], Any], status: int, body: dict[str, str]
) -> None:
    assert result[0] == status
    assert result[1]["Content-Type"] == "application/json"
    assert result[2] == body


def test_nominal(base_url: str) -> None:
    data = b'{"tags": ["v1.2.3", "1.3.0-rc.1"], "bump": "patch"}'
    assert_json(send(f"{base_url}/next-version", data=data), 200, {"next": "1.3.0"})


def test_invalid_tag(base_url: str) -> None:
    data = b'{"tags": ["1.2"], "bump": "patch"}'
    assert_json(
        send(f"{base_url}/next-version", data=data),
        400,
        {"error": "invalid tags: 1.2"},
    )


def test_malformed_json(base_url: str) -> None:
    assert_json(
        send(f"{base_url}/next-version", data=b"{"),
        400,
        {"error": "body must be valid JSON"},
    )


def test_non_json_content_type(base_url: str) -> None:
    assert_json(
        send(f"{base_url}/next-version", data=b"{}", content_type="text/plain"),
        415,
        {"error": "content type must be application/json"},
    )


def test_body_too_large(base_url: str) -> None:
    # The server answers 413 from Content-Length and closes without reading the
    # body, so only the headers are sent (uploading 1 MB would break the pipe).
    conn = http.client.HTTPConnection(base_url.removeprefix("http://"), timeout=5)
    conn.putrequest("POST", "/next-version")
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Content-Length", str(1024 * 1024 + 1))
    conn.endheaders()
    response = conn.getresponse()
    result = (response.status, dict(response.headers), json.load(response))
    conn.close()
    assert_json(result, 413, {"error": "request body too large"})


def test_wrong_method_keeps_allow_header(base_url: str) -> None:
    result = send(f"{base_url}/next-version", method="GET")
    assert_json(result, 405, {"error": "method not allowed"})
    assert "POST" in result[1]["Allow"]
