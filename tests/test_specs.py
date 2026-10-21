from specs import create_app


def post(body):
    return create_app().test_client().post("/next-version", json=body)


def test_next_version():
    tags = ["v1.9.0", "1.10.2", "v1.2.3-rc.1", "latest", "2.0"]
    assert post({"tags": tags, "bump": "major"}).json == {"next": "2.0.0"}
    assert post({"tags": tags, "bump": "minor"}).json == {"next": "1.11.0"}
    assert post({"tags": tags, "bump": "patch"}).json == {"next": "1.10.3"}
    assert post({"tags": [], "bump": "minor"}).json == {"next": "0.1.0"}


def test_next_version_rejects_bad_body():
    assert post({"tags": "v1.0.0", "bump": "patch"}).status_code == 400
    assert post({"tags": [], "bump": "huge"}).status_code == 400
    assert post(None).status_code == 400
