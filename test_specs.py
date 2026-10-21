import pytest

from specs import create_app


@pytest.fixture
def client():
    return create_app().test_client()


def post(client, body):
    return client.post("/next-version", json=body)


@pytest.mark.parametrize(
    ("bump", "expected"),
    [("major", "2.0.0"), ("minor", "1.3.0"), ("patch", "1.2.4")],
)
def test_bumps_highest_tag(client, bump, expected):
    res = post(client, {"tags": ["1.0.0", "1.2.3", "0.9.9"], "bump": bump})
    assert res.status_code == 200
    assert res.get_json() == {"next": expected}


def test_compares_numerically_not_alphabetically(client):
    res = post(client, {"tags": ["1.9.0", "1.10.0"], "bump": "patch"})
    assert res.get_json() == {"next": "1.10.1"}


def test_keeps_v_prefix_of_highest_tag(client):
    res = post(client, {"tags": ["1.0.0", "v1.1.0"], "bump": "minor"})
    assert res.get_json() == {"next": "v1.2.0"}


def test_ignores_invalid_and_prerelease_tags(client):
    res = post(
        client, {"tags": ["latest", "2.0.0-rc.1", "1.0.0", "01.2.3"], "bump": "patch"}
    )
    assert res.get_json() == {"next": "1.0.1"}


def test_starts_from_zero_without_valid_tags(client):
    res = post(client, {"tags": [], "bump": "minor"})
    assert res.get_json() == {"next": "0.1.0"}


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        {"bump": "patch"},
        {"tags": "1.0.0", "bump": "patch"},
        {"tags": [1], "bump": "patch"},
        {"tags": []},
        {"tags": [], "bump": "huge"},
    ],
)
def test_rejects_invalid_body(client, body):
    res = post(client, body)
    assert res.status_code == 400
    assert "error" in res.get_json()
