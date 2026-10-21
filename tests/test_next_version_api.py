import json
from typing import Any

import pytest
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from specs import create_app


@pytest.fixture
def client() -> FlaskClient:
    return create_app().test_client()


def assert_json(response: TestResponse, status: int, body: dict[str, Any]) -> None:
    assert response.status_code == status
    assert response.content_type == "application/json"
    assert response.get_json() == body


def test_hello_unchanged(client: FlaskClient) -> None:
    assert_json(
        client.get("/hello"), 200, {"message": "Hello, the specs server is running"}
    )


def test_unknown_route_is_json_404(client: FlaskClient) -> None:
    assert_json(client.get("/nope"), 404, {"error": "not found"})


def test_wrong_method_on_hello_is_json_405_with_allow(client: FlaskClient) -> None:
    response = client.post("/hello")
    assert_json(response, 405, {"error": "method not allowed"})
    assert "GET" in response.headers["Allow"]


@pytest.mark.parametrize(
    ("tags", "bump", "expected"),
    [
        (["1.2.3"], "patch", "1.2.4"),
        (["1.2.3"], "minor", "1.3.0"),
        (["1.2.3"], "major", "2.0.0"),
        (["v1.2.3", "1.3.0-rc.1"], "patch", "1.3.0"),
        (["v1.2.4", "1.2.3"], "patch", "v1.2.5"),
    ],
)
def test_next_version(
    client: FlaskClient, tags: list[str], bump: str, expected: str
) -> None:
    response = client.post("/next-version", json={"tags": tags, "bump": bump})
    assert_json(response, 200, {"next": expected})


def test_json_content_type_with_charset_is_accepted(client: FlaskClient) -> None:
    response = client.post(
        "/next-version",
        data='{"tags": ["1.2.3"], "bump": "patch"}',
        content_type="application/json; charset=utf-8",
    )
    assert_json(response, 200, {"next": "1.2.4"})


@pytest.mark.parametrize("content_type", [None, "text/plain", "application/xml"])
def test_non_json_content_type_is_415(
    client: FlaskClient, content_type: str | None
) -> None:
    response = client.post(
        "/next-version",
        data='{"tags": ["1.2.3"], "bump": "patch"}',
        content_type=content_type,
    )
    assert_json(response, 415, {"error": "content type must be application/json"})


def test_body_too_large_is_413(client: FlaskClient) -> None:
    body = '{"tags": ["' + "1" * (1024 * 1024) + '"], "bump": "patch"}'
    response = client.post("/next-version", data=body, content_type="application/json")
    assert_json(response, 413, {"error": "request body too large"})


def test_body_just_under_limit_is_not_413(client: FlaskClient) -> None:
    filler = " " * (1024 * 1024 - 40)
    body = '{"tags": ["1.2.3"], "bump": "patch"}' + filler
    assert len(body) <= 1024 * 1024
    response = client.post("/next-version", data=body, content_type="application/json")
    assert_json(response, 200, {"next": "1.2.4"})


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"{",
        b'{"tags": ["1.2.3"], "bump": "patch"',
        b"\xff\xfe\x00",
        b'{"tags": ["\xe9"], "bump": "patch"}',
        b"[" * 500_000 + b"]" * 500_000,
        b'{"":' * 200_000 + b"1" + b"}" * 200_000,
        b"NaN-ish",
        '{"tags": ["1.2.3"], "bump": "patch"}'.encode("utf-16"),
        '{"tags": ["1.2.3"], "bump": "patch"}'.encode("utf-32-le"),
    ],
    ids=[
        "empty",
        "open-brace",
        "truncated",
        "binary",
        "latin-1",
        "deep-array",
        "deep-object",
        "garbage",
        "utf-16",
        "utf-32",
    ],
)
def test_invalid_json_is_400(client: FlaskClient, data: bytes) -> None:
    response = client.post("/next-version", data=data, content_type="application/json")
    assert_json(response, 400, {"error": "body must be valid JSON"})


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ([], "body must be a JSON object"),
        ("x", "body must be a JSON object"),
        (1, "body must be a JSON object"),
        (None, "body must be a JSON object"),
        (
            {"foo": 1, "tags": ["1.2.3"], "bar": 2, "bump": "patch"},
            "unknown fields: foo, bar",
        ),
        ({"foo": 1}, "unknown fields: foo"),
        ({"bump": "patch"}, "tags is required"),
        ({}, "tags is required"),
        ({"tags": "1.2.3", "bump": "patch"}, "tags must be a list of strings"),
        ({"tags": None, "bump": "patch"}, "tags must be a list of strings"),
        ({"tags": {"a": "1.2.3"}, "bump": "patch"}, "tags must be a list of strings"),
        ({"tags": ["1.0.0", 1], "bump": "patch"}, "tags must be a list of strings"),
        ({"tags": [["1.0.0"]], "bump": "patch"}, "tags must be a list of strings"),
        ({"tags": ["1.2.3"]}, "bump is required"),
        ({"tags": []}, "bump is required"),
        (
            {"tags": ["1.2.3"], "bump": "PATCH"},
            "bump must be one of: major, minor, patch",
        ),
        (
            {"tags": ["1.2.3"], "bump": "prerelease"},
            "bump must be one of: major, minor, patch",
        ),
        ({"tags": ["1.2.3"], "bump": 1}, "bump must be one of: major, minor, patch"),
        (
            {"tags": ["1.2.3"], "bump": None},
            "bump must be one of: major, minor, patch",
        ),
        (
            {"tags": ["1.2.3"], "bump": ["patch"]},
            "bump must be one of: major, minor, patch",
        ),
        ({"tags": [], "bump": "PATCH"}, "bump must be one of: major, minor, patch"),
        ({"tags": [], "bump": "patch"}, "tags must not be empty"),
        (
            {"tags": ["1.0.0", "V1.0.0", "x", "1.0.0", "x"], "bump": "patch"},
            "invalid tags: V1.0.0, x, x",
        ),
    ],
)
def test_invalid_body_is_400(client: FlaskClient, body: Any, error: str) -> None:
    # json.dumps keeps key order (the test client's json= sorts keys)
    response = client.post(
        "/next-version", data=json.dumps(body), content_type="application/json"
    )
    assert_json(response, 400, {"error": error})


@pytest.mark.parametrize(
    ("data", "error"),
    [
        (b"[" * 100_000 + b"]" * 100_000, "body must be a JSON object"),
        (b'{"a":' * 100_000 + b"1" + b"}" * 100_000, "unknown fields: a"),
    ],
    ids=["deep-array", "deep-object"],
)
def test_deeply_nested_json_parsed_by_python_is_400(
    client: FlaskClient, data: bytes, error: str
) -> None:
    # Python 3.14's json parses 100 000 levels; it must still be a 400, never a 500.
    response = client.post("/next-version", data=data, content_type="application/json")
    assert_json(response, 400, {"error": error})


def test_get_next_version_is_405_with_allow(client: FlaskClient) -> None:
    response = client.get("/next-version")
    assert_json(response, 405, {"error": "method not allowed"})
    assert "POST" in response.headers["Allow"]
