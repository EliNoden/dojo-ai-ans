import pytest

from versioning import Bump, next_version


@pytest.mark.parametrize(
    ("tags", "bump", "expected"),
    [
        (["1.2.3"], "patch", "1.2.4"),
        (["1.2.3"], "minor", "1.3.0"),
        (["1.2.3"], "major", "2.0.0"),
        (["1.9.0", "1.10.0"], "patch", "1.10.1"),
        (["1.2.9", "1.3.0-rc.1"], "patch", "1.3.0"),
        (["1.3.0-rc.1", "1.3.0"], "patch", "1.3.1"),
        (["1.3.0-rc.1"], "minor", "1.3.0"),
        (["1.3.1-rc.1"], "minor", "1.4.0"),
        (["2.0.0-rc.1"], "major", "2.0.0"),
        (["1.3.0-rc.1"], "major", "2.0.0"),
        (["1.2.3+abc", "1.2.2"], "patch", "1.2.4"),
        (["v1.2.3", "1.0.0"], "patch", "v1.2.4"),
        (["1.2.3", "v1.2.3"], "patch", "v1.2.4"),
        (["v1.2.3", "1.2.3"], "patch", "v1.2.4"),
        (["1.2.3+a", "v1.2.3+b"], "patch", "v1.2.4"),
        (["v1.3.0-rc.1", "1.3.0"], "patch", "1.3.1"),
        (["1.0.0", "v1.2.3"], "major", "v2.0.0"),
    ],
)
def test_next_version(tags: list[str], bump: Bump, expected: str) -> None:
    assert next_version(tags, bump) == expected


def test_empty_tags() -> None:
    with pytest.raises(ValueError, match=r"^tags must not be empty$"):
        next_version([], "patch")


def test_invalid_tags_listed_in_input_order() -> None:
    with pytest.raises(ValueError, match=r"^invalid tags: 1\.2, V1\.2\.3, 01\.2\.3$"):
        next_version(["1.2", "1.2.3", "V1.2.3", "01.2.3"], "patch")


def test_invalid_tags_keep_duplicates() -> None:
    with pytest.raises(ValueError, match=r"^invalid tags: x, x$"):
        next_version(["x", "x"], "patch")


@pytest.mark.parametrize(
    "tag",
    [
        "",
        " 1.2.3",
        "1.2.3 ",
        "1.2.3\n",
        "1.2.3-",
        "1.2.3+",
        "1.2.3-a..b",
        "1.2.3-rc_1",
        "vv1.2.3",
        "1.2.3-rc.01",
        "١.2.3",
        "V1.2.3",
        "v",
    ],
)
def test_invalid_tag(tag: str) -> None:
    with pytest.raises(ValueError) as exc:
        next_version([tag], "patch")
    assert str(exc.value) == f"invalid tags: {tag}"
