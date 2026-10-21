import json

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from specs import create_app


@pytest.fixture
def client() -> FlaskClient:
    app: Flask = create_app()
    return app.test_client()


def _post(client: FlaskClient, payload: object) -> TestResponse:
    return client.post("/next-version", json=payload)


def _assert_error(
    response: TestResponse, status: int, message: str | None = None
) -> None:
    assert response.status_code == status
    assert response.content_type == "application/json"
    body = response.get_json()
    assert set(body) == {"error"}
    assert isinstance(body["error"], str)
    if message is not None:
        assert body["error"] == message


def test_hello_still_works(client: FlaskClient) -> None:
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.get_json() == {"message": "Hello, the specs server is running"}


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
def test_nominal(
    client: FlaskClient, tags: list[str], bump: str, expected: str
) -> None:
    response = _post(client, {"tags": tags, "bump": bump})
    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.get_json() == {"next": expected}


@pytest.mark.parametrize(
    "raw",
    [b"[]", b'"x"', b"42", b"null", b"true", b"1.5", b'[{"tags": [], "bump": "x"}]'],
)
def test_body_must_be_object(client: FlaskClient, raw: bytes) -> None:
    response = client.post("/next-version", data=raw, content_type="application/json")
    _assert_error(response, 400, "body must be a JSON object")


@pytest.mark.parametrize(
    "raw",
    [
        b"{",
        b"",
        b"not json",
        b'{"tags": ["1.2.3"], "bump": "patch"',
        b'{"tags": ["\xff"], "bump": "patch"}',
        b"\xff\xfe\xfd",
        b'{"a": ' + b"1" * 5000 + b"}",
    ],
)
def test_malformed_body(client: FlaskClient, raw: bytes) -> None:
    response = client.post("/next-version", data=raw, content_type="application/json")
    _assert_error(response, 400, "body must be a JSON object")


@pytest.mark.parametrize(
    ("depth", "message"),
    [
        (1000, "tags must be a list of strings"),
        (100_000, "tags must be a list of strings"),
        (500_000, "body must be a JSON object"),  # RecursionError in json
    ],
)
def test_deeply_nested_array_body(
    client: FlaskClient, depth: int, message: str
) -> None:
    raw = b'{"tags": ' + b"[" * depth + b"]" * depth + b', "bump": "patch"}'
    response = client.post("/next-version", data=raw, content_type="application/json")
    _assert_error(response, 400, message)


def test_deeply_nested_object_body(client: FlaskClient) -> None:
    raw = b'{"":' * 200_000 + b"1" + b"}" * 200_000
    response = client.post("/next-version", data=raw, content_type="application/json")
    _assert_error(response, 400, "body must be a JSON object")


@pytest.mark.parametrize(
    "tags",
    [
        None,
        "1.2.3",
        1,
        {"a": "1.2.3"},
        [1, 2],
        ["1.2.3", 2],
        ["1.2.3", None],
        [["1.2.3"]],
        [{"a": 1}],
    ],
)
def test_tags_must_be_list_of_strings(client: FlaskClient, tags: object) -> None:
    _assert_error(
        _post(client, {"tags": tags, "bump": "patch"}),
        400,
        "tags must be a list of strings",
    )


def test_tags_absent(client: FlaskClient) -> None:
    _assert_error(
        _post(client, {"bump": "patch"}), 400, "tags must be a list of strings"
    )


@pytest.mark.parametrize("bump", ["MAJOR", "premajor", "", 1, None, ["patch"], {}])
def test_bump_invalid(client: FlaskClient, bump: object) -> None:
    _assert_error(
        _post(client, {"tags": ["1.2.3"], "bump": bump}),
        400,
        "bump must be one of: major, minor, patch",
    )


def test_bump_absent(client: FlaskClient) -> None:
    _assert_error(
        _post(client, {"tags": ["1.2.3"]}),
        400,
        "bump must be one of: major, minor, patch",
    )


def test_tags_empty(client: FlaskClient) -> None:
    _assert_error(
        _post(client, {"tags": [], "bump": "patch"}), 400, "tags must not be empty"
    )


def test_validation_order_structure_first(client: FlaskClient) -> None:
    _assert_error(
        _post(client, {"tags": [], "bump": "x"}),
        400,
        "bump must be one of: major, minor, patch",
    )
    _assert_error(
        _post(client, {"tags": [1], "bump": "x"}),
        400,
        "tags must be a list of strings",
    )
    _assert_error(
        _post(client, {"tags": ["foo"], "bump": "x"}),
        400,
        "bump must be one of: major, minor, patch",
    )


def test_invalid_tags_listed_in_order_with_duplicates(client: FlaskClient) -> None:
    _assert_error(
        _post(
            client, {"tags": ["1.2.3", "foo", "01.2.3", "bar", "foo"], "bump": "patch"}
        ),
        400,
        "invalid tags: foo, 01.2.3, bar, foo",
    )


@pytest.mark.parametrize(
    "tag",
    [
        "V1.2.3",
        " 1.2.3",
        "1.2.3\n",
        "1.2",
        "١.٢.٣",
        pytest.param("9" * 5000 + ".0.0", id="5000-digits"),
        "\ud800",
    ],
)
def test_invalid_tag_is_400_not_5xx(client: FlaskClient, tag: str) -> None:
    response = _post(client, {"tags": [tag], "bump": "patch"})
    assert response.status_code == 400
    assert response.content_type == "application/json"
    assert response.get_json() == {"error": f"invalid tags: {tag}"}


@pytest.mark.parametrize(
    "content_type", ["text/plain", "application/x-www-form-urlencoded", None]
)
def test_unsupported_media_type(client: FlaskClient, content_type: str | None) -> None:
    response = client.post(
        "/next-version",
        data=json.dumps({"tags": ["1.2.3"], "bump": "patch"}),
        content_type=content_type,
    )
    _assert_error(response, 415)


def test_body_too_large(client: FlaskClient) -> None:
    raw = b'{"tags": ["' + b"a" * (1024 * 1024) + b'"], "bump": "patch"}'
    response = client.post("/next-version", data=raw, content_type="application/json")
    _assert_error(response, 413)


def test_body_just_under_limit_is_accepted(client: FlaskClient) -> None:
    padding = b" " * (1024 * 1024 - 40)
    raw = b'{"tags": ["1.2.3"], "bump": "patch"}' + padding
    assert len(raw) <= 1024 * 1024
    response = client.post("/next-version", data=raw, content_type="application/json")
    assert response.status_code == 200
    assert response.get_json() == {"next": "1.2.4"}


def test_unknown_route_is_json_404(client: FlaskClient) -> None:
    _assert_error(client.get("/nope"), 404)


def test_get_is_json_405_with_allow(client: FlaskClient) -> None:
    response = client.get("/next-version")
    _assert_error(response, 405)
    assert "POST" in response.headers["Allow"].split(", ")


def test_other_route_405_keeps_allow(client: FlaskClient) -> None:
    response = client.post("/hello")
    _assert_error(response, 405)
    assert "GET" in response.headers["Allow"]
