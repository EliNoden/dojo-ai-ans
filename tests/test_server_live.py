"""Tests against a real gunicorn process (real sockets, real worker)."""

import http.client
import json
import re
import socket
import subprocess
import sys
from collections.abc import Iterable, Iterator
from email.message import Message
from pathlib import Path
from typing import NamedTuple

import pytest

ROOT = Path(__file__).resolve().parent.parent
MEGABYTE = 1024 * 1024
JSON = {"Content-Type": "application/json"}
BUMP_MESSAGE = "bump must be one of: major, minor, patch"


class Server(NamedTuple):
    port: int
    log: Path


class Response(NamedTuple):
    status: int
    headers: Message
    body: bytes

    def json(self) -> object:
        return json.loads(self.body)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


def _request(
    server: Server,
    method: str,
    path: str,
    body: bytes | Iterable[bytes] | None = None,
    headers: dict[str, str] | None = None,
    *,
    chunked: bool = False,
) -> Response:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=60)
    try:
        try:
            connection.request(
                method, path, body=body, headers=headers or {}, encode_chunked=chunked
            )
        except BrokenPipeError, ConnectionResetError:
            pass  # the server answered (e.g. 413) before reading the whole body
        response = connection.getresponse()
        return Response(response.status, response.msg, response.read())
    finally:
        connection.close()


def _post(server: Server, raw: bytes, headers: dict[str, str] = JSON) -> Response:
    return _request(server, "POST", "/next-version", raw, headers)


def _post_json(server: Server, payload: object) -> Response:
    return _post(server, json.dumps(payload).encode())


def _assert_error(response: Response, status: int, message: str | None = None) -> None:
    assert response.status == status, response.body[:200]
    assert response.headers["Content-Type"] == "application/json"
    body = response.json()
    assert isinstance(body, dict)
    assert set(body) == {"error"}
    assert isinstance(body["error"], str)
    if message is not None:
        assert body["error"] == message


def _wait_until_ready(server: Server, process: subprocess.Popen[bytes]) -> None:
    for _ in range(100):
        assert process.poll() is None, server.log.read_text()
        try:
            if _request(server, "GET", "/hello").status == 200:
                return
        except OSError:
            pass
        try:
            process.wait(timeout=0.1)
        except subprocess.TimeoutExpired:
            pass
    pytest.fail(f"gunicorn not ready:\n{server.log.read_text()}")


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Server]:
    log = tmp_path_factory.mktemp("gunicorn") / "gunicorn.log"
    live = Server(_free_port(), log)
    command = [
        sys.executable,
        "-m",
        "gunicorn",
        "-w",
        "1",  # a single worker: any crash shows up as a restart in the log
        "-b",
        f"127.0.0.1:{live.port}",
        "--timeout",
        "60",
        "--log-level",
        "info",
        "specs:create_app()",
    ]
    with log.open("wb") as log_file:
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=log_file, stderr=subprocess.STDOUT
        )
    try:
        _wait_until_ready(live, process)
        yield live
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.fixture(autouse=True)
def worker_stays_healthy(server: Server) -> Iterator[None]:
    """After each test: same worker (never restarted), no traceback, still serving."""
    yield
    log = server.log.read_text()
    assert len(re.findall(r"Booting worker", log)) == 1, log
    assert "Traceback" not in log, log
    assert _request(server, "GET", "/hello").status == 200


def test_hello(server: Server) -> None:
    response = _request(server, "GET", "/hello")
    assert response.status == 200
    assert response.json() == {"message": "Hello, the specs server is running"}


@pytest.mark.parametrize(
    ("tags", "bump", "expected"),
    [
        (["v1.2.3", "v1.2.4"], "patch", "v1.2.5"),
        (["1.9.0", "1.10.0"], "minor", "1.11.0"),
        (["1.2.9", "1.3.0-rc.1"], "patch", "1.3.0"),
        (["v1.2.3", "1.2.3"], "patch", "v1.2.4"),
        (["0.0.0"], "major", "1.0.0"),
    ],
)
def test_nominal(server: Server, tags: list[str], bump: str, expected: str) -> None:
    response = _post_json(server, {"tags": tags, "bump": bump})
    assert response.status == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == {"next": expected}


def test_json_content_type_with_charset(server: Server) -> None:
    response = _post(
        server,
        b'{"tags": ["1.2.3"], "bump": "patch"}',
        {"Content-Type": "application/json; charset=utf-8"},
    )
    assert response.status == 200
    assert response.json() == {"next": "1.2.4"}


@pytest.mark.parametrize(
    "raw",
    [b"[]", b'"x"', b"42", b"null", b"{", b"", b"not json"],
)
def test_body_must_be_a_json_object(server: Server, raw: bytes) -> None:
    _assert_error(_post(server, raw), 400, "body must be a JSON object")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"bump": "patch"}, "tags must be a list of strings"),
        ({"tags": "1.2.3", "bump": "patch"}, "tags must be a list of strings"),
        ({"tags": [1, 2], "bump": "patch"}, "tags must be a list of strings"),
        ({"tags": None, "bump": "patch"}, "tags must be a list of strings"),
        ({"tags": ["1.2.3"]}, BUMP_MESSAGE),
        ({"tags": ["1.2.3"], "bump": "MAJOR"}, BUMP_MESSAGE),
        ({"tags": ["1.2.3"], "bump": 1}, BUMP_MESSAGE),
        ({"tags": ["1.2.3"], "bump": None}, BUMP_MESSAGE),
        ({"tags": [], "bump": "patch"}, "tags must not be empty"),
        ({"tags": [], "bump": "x"}, BUMP_MESSAGE),
        (
            {"tags": ["1.2.3", "foo", "01.2.3", "bar", "foo"], "bump": "patch"},
            "invalid tags: foo, 01.2.3, bar, foo",
        ),
        ({"tags": ["V1.2.3"], "bump": "patch"}, "invalid tags: V1.2.3"),
        ({"tags": ["١.٢.٣"], "bump": "patch"}, "invalid tags: ١.٢.٣"),
    ],
)
def test_validation_errors(server: Server, payload: object, message: str) -> None:
    _assert_error(_post_json(server, payload), 400, message)


def test_component_with_5000_digits_is_invalid(server: Server) -> None:
    tag = "9" * 5000 + ".0.0"
    response = _post_json(server, {"tags": [tag], "bump": "patch"})
    _assert_error(response, 400, f"invalid tags: {tag}")


def test_unknown_route_is_json_404(server: Server) -> None:
    _assert_error(_request(server, "GET", "/nope"), 404)


def test_get_is_json_405_with_allow(server: Server) -> None:
    response = _request(server, "GET", "/next-version")
    _assert_error(response, 405)
    assert "POST" in response.headers["Allow"].split(", ")


def test_post_on_other_route_is_405_with_allow(server: Server) -> None:
    response = _request(server, "POST", "/hello", b"{}", JSON)
    _assert_error(response, 405)
    assert "GET" in response.headers["Allow"].split(", ")


@pytest.mark.parametrize("content_type", ["text/plain", "application/xml", None])
def test_non_json_content_type_is_415(server: Server, content_type: str | None) -> None:
    headers = {} if content_type is None else {"Content-Type": content_type}
    _assert_error(_post(server, b'{"tags": ["1.2.3"], "bump": "patch"}', headers), 415)


def test_body_over_one_megabyte_is_413(server: Server) -> None:
    raw = b'{"tags": ["' + b"a" * MEGABYTE + b'"], "bump": "patch"}'
    _assert_error(_post(server, raw), 413)


def test_body_at_the_limit_is_accepted(server: Server) -> None:
    raw = b'{"tags": ["1.2.3"], "bump": "patch"}'
    raw += b" " * (MEGABYTE - len(raw))
    assert len(raw) == MEGABYTE
    response = _post(server, raw)
    assert response.status == 200
    assert response.json() == {"next": "1.2.4"}


@pytest.mark.parametrize("filler", [b" ", b"a"], ids=["whitespace", "garbage"])
def test_chunked_body_over_one_megabyte_without_content_length_is_413(
    server: Server, filler: bytes
) -> None:
    chunk = filler * 65536
    body = [b'{"tags": ["1.2.3"], "bump": "patch"}'] + [chunk] * 24  # 1.5 MiB
    response = _request(
        server,
        "POST",
        "/next-version",
        body,
        {**JSON, "Transfer-Encoding": "chunked"},
        chunked=True,
    )
    _assert_error(response, 413)


def test_chunked_body_at_the_limit_is_accepted(server: Server) -> None:
    head = b'{"tags": ["1.2.3"], "bump": "patch"}'
    body = [head, b" " * (MEGABYTE - len(head))]
    response = _request(
        server,
        "POST",
        "/next-version",
        body,
        {**JSON, "Transfer-Encoding": "chunked"},
        chunked=True,
    )
    assert response.status == 200
    assert response.json() == {"next": "1.2.4"}


def test_chunked_body_is_read_without_content_length(server: Server) -> None:
    body = [b'{"tags": ["v1.', b'2.3"], "bump": "patch"}']
    response = _request(
        server,
        "POST",
        "/next-version",
        body,
        {**JSON, "Transfer-Encoding": "chunked"},
        chunked=True,
    )
    assert response.status == 200
    assert response.json() == {"next": "v1.2.4"}


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (
            b'{"tags": ' + b"[" * 500_000 + b"]" * 500_000 + b', "bump": "patch"}',
            "body must be a JSON object",
        ),
        (
            b'{"tags": ' + b"[" * 100_000 + b"]" * 100_000 + b', "bump": "patch"}',
            "tags must be a list of strings",
        ),
        (
            b'{"":' * 200_000 + b"1" + b"}" * 200_000,
            "body must be a JSON object",
        ),
    ],
    ids=["array-500k", "array-100k", "object-200k"],
)
def test_deeply_nested_json_is_400_and_worker_survives(
    server: Server, raw: bytes, message: str
) -> None:
    _assert_error(_post(server, raw), 400, message)
    follow_up = _post_json(server, {"tags": ["1.2.3"], "bump": "patch"})
    assert follow_up.status == 200
    assert follow_up.json() == {"next": "1.2.4"}


def test_lone_surrogate_escape_in_tag_is_400(server: Server) -> None:
    raw = b'{"tags": ["\\ud800"], "bump": "patch"}'
    response = _post(server, raw)
    _assert_error(response, 400, "invalid tags: \ud800")
    response.body.decode("ascii")  # the error body itself stays plain ASCII JSON


def test_lone_surrogate_encoded_in_utf8_is_not_a_5xx(server: Server) -> None:
    raw = b'{"tags": ["\xed\xa0\x80"], "bump": "patch"}'
    _assert_error(_post(server, raw), 400, "invalid tags: \ud800")


@pytest.mark.parametrize(
    "raw",
    [
        b'{"tags": ["\xff"], "bump": "patch"}',
        b"\xff\xfe\xfd",
        b'{"tags": ["\xc3("], "bump": "patch"}',
    ],
)
def test_non_utf8_json_is_400(server: Server, raw: bytes) -> None:
    _assert_error(_post(server, raw), 400, "body must be a JSON object")


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-32", "utf-8-sig"])
def test_json_in_other_unicode_encoding_or_with_bom_is_accepted(
    server: Server, encoding: str
) -> None:
    # json.loads(bytes) auto-detects UTF-8/16/32 (RFC 4627); documented, not a 5xx.
    raw = json.dumps({"tags": ["1.2.3"], "bump": "patch"}).encode(encoding)
    response = _post(server, raw)
    assert response.status == 200
    assert response.json() == {"next": "1.2.4"}
