import pytest

from specs import create_app


@pytest.fixture
def client():
    return create_app().test_client()


def post(client, tags, bump="patch"):
    return client.post("/next-version", json={"tags": tags, "bump": bump})


@pytest.mark.parametrize(
    "tags, bump, expected",
    [
        (["1.2.3"], "patch", "1.2.4"),
        (["1.2.3"], "minor", "1.3.0"),
        (["1.2.3"], "major", "2.0.0"),
        (["v1.2.3"], "patch", "v1.2.4"),
        (["1.9.0", "1.10.0"], "patch", "1.10.1"),
        (["1.2.9", "1.3.0-rc.1"], "patch", "1.3.0"),
        (["1.3.0-rc.1", "1.3.0"], "patch", "1.3.1"),
        (["1.3.0-rc.1"], "minor", "1.3.0"),
        (["1.3.1-rc.1"], "minor", "1.4.0"),
        (["2.0.0-rc.1"], "major", "2.0.0"),
        (["1.3.0-rc.1"], "major", "2.0.0"),
        (["1.3.0-rc.1", "1.3.0-rc.2"], "patch", "1.3.0"),
        (["1.2.3", "v1.2.3"], "patch", "v1.2.4"),
        (["v1.2.3", "1.2.3"], "patch", "v1.2.4"),
        (["1.2.3+abc", "v1.2.3+zzz"], "patch", "v1.2.4"),
        (["v1.0.0", "2.0.0"], "patch", "2.0.1"),
        (["0.0.0"], "patch", "0.0.1"),
        (["1.2.3-rc.1+build.5"], "patch", "1.2.3"),
    ],
)
def test_next_version(client, tags, bump, expected):
    res = post(client, tags, bump)
    assert res.status_code == 200
    assert res.get_json() == {"next": expected}


@pytest.mark.parametrize(
    "tag",
    [
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "V1.2.3",
        "vv1.2.3",
        "1.2",
        "1.2.3.4",
        "1.2.3-",
        "1.2.3+",
        "1.2.3-rc..1",
        "1.2.3-rc_1",
        "1.2.3+a+b",
        " 1.2.3",
        "1.2.3\n",
        "",
        "v",
        "a.b.c",
        "1.2.3-é",
    ],
)
def test_invalid_tag(client, tag):
    res = post(client, [tag])
    assert res.status_code == 400
    assert res.get_json() == {"error": f"invalid tags: {tag}"}


def test_invalid_tags_listed_in_input_order(client):
    res = post(client, ["x", "1.0.0", "01.0.0", "y"])
    assert res.status_code == 400
    assert res.get_json() == {"error": "invalid tags: x, 01.0.0, y"}


def test_empty_tags(client):
    res = post(client, [])
    assert res.status_code == 400
    assert res.get_json() == {"error": "tags must not be empty"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"data": "not json", "content_type": "application/json"},
        {"data": '{"tags": ["1.0.0"], "bump": "patch"}', "content_type": "text/plain"},
        {"json": ["1.0.0"]},
        {"json": {"bump": "patch"}},
        {"json": {"tags": "1.0.0", "bump": "patch"}},
        {"json": {"tags": [1, 2], "bump": "patch"}},
        {"json": {"tags": ["1.0.0"]}},
        {"json": {"tags": ["1.0.0"], "bump": "huge"}},
        {"json": {"tags": ["1.0.0"], "bump": None}},
    ],
)
def test_bad_request(client, kwargs):
    res = client.post("/next-version", **kwargs)
    assert res.status_code == 400
    assert res.get_json()["error"]
