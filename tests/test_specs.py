from specs import REFS, create_app


def test_refs_returns_in_memory_refs():
    res = create_app().test_client().get("/refs")

    assert res.status_code == 200
    assert res.get_json() == REFS
