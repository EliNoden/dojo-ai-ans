from typing import Literal

import pytest

from versioning import InvalidTagsError, next_version


@pytest.mark.parametrize(
    ("tags", "bump", "expected"),
    [
        (["1.2.3"], "patch", "1.2.4"),
        (["1.2.3"], "minor", "1.3.0"),
        (["1.2.3"], "major", "2.0.0"),
        (["1.9.0", "1.10.0"], "patch", "1.10.1"),
        (["1.10.0", "1.9.0"], "patch", "1.10.1"),
        (["1.2.9", "1.3.0-rc.1"], "patch", "1.3.0"),
        (["1.3.0-rc.1", "1.3.0"], "patch", "1.3.1"),
        (["1.3.0-rc.1"], "minor", "1.3.0"),
        (["1.3.0-rc.1"], "major", "2.0.0"),
        (["2.0.0-rc.1"], "major", "2.0.0"),
        (["1.3.1-rc.1"], "minor", "1.4.0"),
        (["1.3.0-rc.1", "1.3.0-rc.2"], "patch", "1.3.0"),
        (["v1.2.3", "1.2.4"], "patch", "1.2.5"),
        (["v1.2.4", "1.2.3"], "patch", "v1.2.5"),
        (["1.2.3", "v1.2.3"], "patch", "v1.2.4"),
        (["v1.2.3", "1.2.3"], "patch", "v1.2.4"),
        (["1.2.3+abc", "v1.2.3"], "patch", "v1.2.4"),
        (["v1.2.3", "1.2.3+abc"], "patch", "v1.2.4"),
        (["1.2.3+abc"], "minor", "1.3.0"),
        (["v1.2.3+abc"], "patch", "v1.2.4"),
        (["v1.0.0-rc.1"], "patch", "v1.0.0"),
    ],
)
def test_next_version(
    tags: list[str], bump: Literal["major", "minor", "patch"], expected: str
) -> None:
    assert next_version(tags, bump) == expected


@pytest.mark.parametrize(
    "tag",
    [
        "V1.2.3",
        "1.2",
        "01.2.3",
        " 1.2.3",
        "1.2.3\n",
        "1.2.3-",
        "1.2.3+",
        "1.2.3-01",
        "1.2.3+a..b",
        "vv1.2.3",
        "v",
        "",
        "١.2.3",
    ],
)
def test_invalid_tag(tag: str) -> None:
    with pytest.raises(InvalidTagsError, match=r"^invalid tags: "):
        next_version([tag], "patch")


def test_invalid_tags_message_keeps_input_order_and_duplicates() -> None:
    with pytest.raises(InvalidTagsError) as exc:
        next_version(["1.0.0", "V1.0.0", "x", "1.0.0", "x"], "patch")
    assert str(exc.value) == "invalid tags: V1.0.0, x, x"


def test_invalid_tags_error_is_a_value_error() -> None:
    assert issubclass(InvalidTagsError, ValueError)


def test_empty_tags() -> None:
    with pytest.raises(ValueError) as exc:
        next_version([], "patch")
    assert str(exc.value) == "tags must not be empty"
