import pytest

from specs import create_app


def post(json=None, data=None):
    return create_app().test_client().post("/next-version", json=json, data=data)


@pytest.mark.parametrize(
    "tags, bump, expected",
    [
        (["1.2.3"], "patch", "1.2.4"),
        (["v1.2.3"], "minor", "v1.3.0"),
        (["1.2.3"], "major", "2.0.0"),
        (["1.9.0", "1.10.0"], "patch", "1.10.1"),
        (["1.3.0-rc.1", "1.2.9"], "patch", "1.3.0"),
        (["1.3.0-rc.1", "1.3.0"], "patch", "1.3.1"),
        (["v1.3.0-rc.1", "1.3.0-rc.2"], "patch", "1.3.0"),
        (["1.2.3", "v1.2.3"], "patch", "v1.2.4"),
        (["v1.2.3+abc", "1.2.3+zzz"], "patch", "v1.2.4"),
        (["1.0.0-alpha.1", "v1.0.0-alpha.beta"], "minor", "v1.0.0"),
    ],
)
def test_next_version(tags, bump, expected):
    res = post({"tags": tags, "bump": bump})
    assert res.status_code == 200
    assert res.get_json() == {"next": expected}


@pytest.mark.parametrize(
    "json, data, error",
    [
        (
            {
                "tags": [
                    "1.2.3",
                    "V1.2.3",
                    "01.2.3",
                    "1.2",
                    "1.2.3-",
                    "1.2.3+a..b",
                    "1.2.3\n",
                ],
                "bump": "patch",
            },
            None,
            "invalid tags: V1.2.3, 01.2.3, 1.2, 1.2.3-, 1.2.3+a..b, 1.2.3\n",
        ),
        ({"tags": [], "bump": "patch"}, None, "tags must not be empty"),
        (None, "not json", "body must be a JSON object"),
        ([], None, "body must be a JSON object"),
        ({"bump": "patch"}, None, "tags must be a list of strings"),
        (
            {"tags": ["1.2.3", 1], "bump": "patch"},
            None,
            "tags must be a list of strings",
        ),
        ({"tags": ["1.2.3"]}, None, "bump must be one of: major, minor, patch"),
        (
            {"tags": ["1.2.3"], "bump": "huge"},
            None,
            "bump must be one of: major, minor, patch",
        ),
    ],
)
def test_errors(json, data, error):
    res = post(json, data)
    assert res.status_code == 400
    assert res.get_json() == {"error": error}
