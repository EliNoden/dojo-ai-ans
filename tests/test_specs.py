from specs import create_app


def test_hello():
    res = create_app().test_client().get("/hello")

    assert res.status_code == 200
    assert res.get_json() == {"message": "Hello, the specs server is running"}
