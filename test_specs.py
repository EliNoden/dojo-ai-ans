import pytest

from specs import create_app


@pytest.fixture
def client():
    return create_app().test_client()


def post(client, tags, bump):
    return client.post("/next-version", json={"tags": tags, "bump": bump})


@pytest.mark.parametrize(
    "tags, bump, expected",
    [
        (["1.2.3"], "patch", "1.2.4"),
        (["1.2.3"], "minor", "1.3.0"),
        (["1.2.3"], "major", "2.0.0"),
        (["1.9.0", "1.10.0"], "patch", "1.10.1"),
        (["v1.2.3"], "patch", "v1.2.4"),
        (["1.2.3", "v1.2.3"], "patch", "v1.2.4"),
        (["v1.2.3", "1.2.3"], "patch", "v1.2.4"),
        (["1.3.0-rc.1", "1.3.0"], "patch", "1.3.1"),
        (["1.3.0-rc.1", "1.2.9"], "patch", "1.3.0"),
        (["1.3.0-rc.1+abc"], "patch", "1.3.0"),
        (["1.2.3+build", "1.2.3"], "patch", "1.2.4"),
        (["1.2.9", "v1.3.0-rc.1"], "patch", "v1.3.0"),
    ],
)
def test_next_version(client, tags, bump, expected):
    response = post(client, tags, bump)
    assert response.status_code == 200
    assert response.get_json() == {"next": expected}


def test_invalid_tags_keep_input_order(client):
    response = post(client, ["1.2.3", "01.2.3", "V1.0.0", "1.2", "v1.0.0"], "patch")
    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid tags: 01.2.3, V1.0.0, 1.2"}


@pytest.mark.parametrize("tag", ["1.2.3-", "1.2.3+", "1.2.3-a..b", "1.2.3\n", "vv1.2.3", " 1.2.3"])
def test_invalid_tag_forms(client, tag):
    response = post(client, [tag], "patch")
    assert response.status_code == 400


def test_empty_tags(client):
    response = post(client, [], "patch")
    assert response.status_code == 400
    assert response.get_json() == {"error": "tags must not be empty"}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"tags": ["1.0.0"]},
        {"bump": "patch"},
        {"tags": "1.0.0", "bump": "patch"},
        {"tags": [1], "bump": "patch"},
        {"tags": ["1.0.0"], "bump": "huge"},
        {"tags": ["1.0.0"], "bump": 3},
        ["1.0.0"],
    ],
)
def test_bad_body(client, body):
    response = client.post("/next-version", json=body)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_non_json_body(client):
    response = client.post("/next-version", data="not json", content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.get_json()
