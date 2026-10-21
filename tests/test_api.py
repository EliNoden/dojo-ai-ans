import json
from typing import Any

import pytest
from flask.testing import FlaskClient

from specs import create_app

TAGS_ERROR = "tags must be a list of strings"
BUMP_ERROR = "bump must be one of: major, minor, patch"


@pytest.fixture
def client() -> FlaskClient:
    return create_app().test_client()


def assert_error(response: Any, status: int, message: str | None = None) -> None:
    assert response.status_code == status
    assert response.is_json
    body = response.get_json()
    assert set(body) == {"error"}
    assert isinstance(body["error"], str)
    if message is not None:
        assert body["error"] == message


def test_nominal(client: FlaskClient) -> None:
    response = client.post(
        "/next-version", json={"tags": ["v1.2.3", "1.0.0"], "bump": "patch"}
    )
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"next": "v1.2.4"}


@pytest.mark.parametrize(
    "content_type",
    ["application/json; charset=utf-8", "application/vnd.api+json"],
)
def test_json_content_type_variants(client: FlaskClient, content_type: str) -> None:
    response = client.post(
        "/next-version",
        data=b'{"tags": ["1.2.3"], "bump": "minor"}',
        content_type=content_type,
    )
    assert response.status_code == 200
    assert response.get_json() == {"next": "1.3.0"}


@pytest.mark.parametrize(
    "data",
    [
        b"{bad",
        b"\xff\xfe",
        b"",
        pytest.param(b"[" * 100000, id="deeply-nested"),
        b'{"tags": "\xff"}',
    ],
)
def test_invalid_json(client: FlaskClient, data: bytes) -> None:
    response = client.post("/next-version", data=data, content_type="application/json")
    assert_error(response, 400, "body must be valid JSON")


@pytest.mark.parametrize("body", [[], "x", None, 1])
def test_body_not_object(client: FlaskClient, body: object) -> None:
    response = client.post(
        "/next-version",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert_error(response, 400, "body must be a JSON object")


@pytest.mark.parametrize(
    "body",
    [
        {"bump": "patch"},
        {"tags": None, "bump": "patch"},
        {"tags": "1.2.3", "bump": "patch"},
        {"tags": {"1.2.3": 1}, "bump": "patch"},
        {"tags": [1], "bump": "patch"},
        {"tags": [None], "bump": "patch"},
        {"tags": [[]], "bump": "patch"},
        {"tags": ["1.2.3", 1], "bump": "patch"},
        {"tags": None, "bump": "bad"},
    ],
)
def test_tags_wrong_type(client: FlaskClient, body: dict[str, object]) -> None:
    assert_error(client.post("/next-version", json=body), 400, TAGS_ERROR)


@pytest.mark.parametrize("bump", ["Patch", "", ["patch"], {}, 1, None])
def test_bump_invalid(client: FlaskClient, bump: object) -> None:
    response = client.post("/next-version", json={"tags": ["1.2.3"], "bump": bump})
    assert_error(response, 400, BUMP_ERROR)


def test_bump_missing_checked_before_empty_tags(client: FlaskClient) -> None:
    assert_error(client.post("/next-version", json={"tags": []}), 400, BUMP_ERROR)


def test_empty_tags(client: FlaskClient) -> None:
    response = client.post("/next-version", json={"tags": [], "bump": "patch"})
    assert_error(response, 400, "tags must not be empty")


def test_invalid_tags(client: FlaskClient) -> None:
    response = client.post(
        "/next-version",
        json={"tags": ["1.2", "1.2.3", "V1.2.3", "01.2.3"], "bump": "patch"},
    )
    assert_error(response, 400, "invalid tags: 1.2, V1.2.3, 01.2.3")


@pytest.mark.parametrize("content_type", ["text/plain", None])
def test_not_json_content_type(client: FlaskClient, content_type: str | None) -> None:
    response = client.post("/next-version", data="x", content_type=content_type)
    assert_error(response, 415)


def test_body_too_large(client: FlaskClient) -> None:
    response = client.post(
        "/next-version", json={"tags": ["1.2.3"] * 200000, "bump": "patch"}
    )
    assert_error(response, 413)


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_method_not_allowed(client: FlaskClient, method: str) -> None:
    response = getattr(client, method)("/next-version")
    assert_error(response, 405)
    assert "POST" in response.headers["Allow"]


def test_unknown_route(client: FlaskClient) -> None:
    assert_error(client.get("/nope"), 404)


def test_hello_still_works(client: FlaskClient) -> None:
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.get_json() == {"message": "Hello, the specs server is running"}
