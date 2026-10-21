import re

import pytest

from versions import PrecedenceKey, next_version, parse_tag, precedence_key


@pytest.mark.parametrize(
    "tag",
    [
        "1.2.3",
        "v1.2.3",
        "0.0.0",
        "1.2.3-rc.1",
        "1.2.3-rc.01",
        "1.2.3+a-b.c",
        "1.2.3-rc.1+x",
        "1.2.3-a-b",
        "999999999999999.0.0",
    ],
)
def test_parse_tag_valid(tag: str) -> None:
    assert parse_tag(tag) is not None


@pytest.mark.parametrize(
    "tag",
    [
        "",
        "V1.2.3",
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "1.2",
        "1.2.3.4",
        "1.2.3-",
        "1.2.3+",
        "1.2.3-a..b",
        "1.2.3-.a",
        "1.2.3-a.",
        "1.2.3+a..b",
        " 1.2.3",
        "1.2.3 ",
        "1.2.3\n",
        "\n1.2.3",
        "١.٢.٣",
        "1.2.٣",
        "1.2.3-é",
        "1.2.3-rc_1",
        "vv1.2.3",
        "-1.2.3",
        "1.2.3-rc.1+",
        "1.2.3+a+b",
        "1234567890123456.0.0",
        "0.1234567890123456.0",
        "0.0.1234567890123456",
        "9" * 5000 + ".0.0",
    ],
)
def test_parse_tag_invalid(tag: str) -> None:
    assert parse_tag(tag) is None


def test_parse_tag_fields() -> None:
    version = parse_tag("v10.20.30-rc.01+build.5")
    assert version is not None
    assert (version.major, version.minor, version.patch) == (10, 20, 30)
    assert version.prerelease == ("rc", "01")
    assert version.has_v is True


def test_parse_tag_fields_without_v_nor_prerelease() -> None:
    version = parse_tag("1.2.3+abc")
    assert version is not None
    assert version.prerelease == ()
    assert version.has_v is False


def _key(tag: str) -> PrecedenceKey:
    version = parse_tag(tag)
    assert version is not None
    return precedence_key(version)


@pytest.mark.parametrize(
    ("lower", "higher"),
    [
        ("1.9.0", "1.10.0"),
        ("1.2.9", "1.3.0"),
        ("1.9.9", "2.0.0"),
        ("1.3.0-rc.1", "1.3.0"),
        ("1.2.9", "1.3.0-rc.1"),
        ("1.3.0-rc.2", "1.3.0-rc.10"),
        ("1.3.0-rc.9", "1.3.0-rc.10"),
        ("1.3.0-rc.1", "1.3.0-rc.01"),
        ("1.3.0-1", "1.3.0-a"),
        ("1.3.0-99999", "1.3.0-0a"),
        ("1.3.0-rc", "1.3.0-rc.1"),
        ("1.3.0-alpha", "1.3.0-beta"),
        ("1.3.0-Z", "1.3.0-a"),
        ("1.3.0-alpha.1", "1.3.0-alpha.beta"),
        ("1.3.0-alpha.beta", "1.3.0-beta"),
        ("1.3.0-beta.2", "1.3.0-beta.11"),
        ("1.3.0-beta.11", "1.3.0-rc.1"),
        ("1.3.0-1", "1.3.0-2"),
        ("1.3.0-9", "1.3.0-10"),
        ("0.0.0", "0.0.1"),
        ("0.0.0", "0.1.0"),
        ("0.0.0", "1.0.0"),
    ],
)
def test_precedence_order(lower: str, higher: str) -> None:
    assert _key(lower) < _key(higher)
    assert _key(higher) > _key(lower)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("v1.2.3", "1.2.3"),
        ("1.2.3+abc", "1.2.3+def"),
        ("1.2.3-rc.1+abc", "1.2.3-rc.1"),
    ],
)
def test_precedence_equal(a: str, b: str) -> None:
    assert _key(a) == _key(b)


@pytest.mark.parametrize(
    ("tags", "bump", "expected"),
    [
        (["1.2.3"], "patch", "1.2.4"),
        (["1.2.3"], "minor", "1.3.0"),
        (["1.2.3"], "major", "2.0.0"),
        (["1.3.0-rc.1"], "patch", "1.3.0"),
        (["1.3.0-rc.1"], "minor", "1.4.0"),
        (["1.3.0-rc.1"], "major", "2.0.0"),
        (["v1.2.3", "v1.2.4"], "patch", "v1.2.5"),
        (["1.9.0", "1.10.0"], "minor", "1.11.0"),
        (["1.2.9", "1.3.0-rc.1"], "patch", "1.3.0"),
        (["1.3.0-rc.1", "1.3.0"], "patch", "1.3.1"),
        (["1.3.0-rc.2", "1.3.0-rc.10"], "minor", "1.4.0"),
        (["1.3.0-rc.10", "1.3.0-rc.2"], "minor", "1.4.0"),
        (["v1.2.3", "1.2.3"], "patch", "v1.2.4"),
        (["1.2.3", "v1.2.3"], "patch", "v1.2.4"),
        (["1.2.3", "v1.2.3+abc"], "patch", "v1.2.4"),
        (["1.2.3+abc", "1.2.3+def"], "patch", "1.2.4"),
        (["v1.2.3-rc.1", "v1.2.3-rc.1+x"], "patch", "v1.2.3"),
        (["v1.0.0", "1.2.3"], "patch", "1.2.4"),
        (["1.0.0", "v1.2.3"], "patch", "v1.2.4"),
        (["v1.3.0-rc.1", "1.3.0-rc.2"], "patch", "1.3.0"),
        (["0.0.0"], "major", "1.0.0"),
        (["0.0.0"], "patch", "0.0.1"),
        (["1.2.3-rc.1+build"], "minor", "1.3.0"),
        (["999999999999999.0.0"], "major", "1000000000000000.0.0"),
    ],
)
def test_next_version(tags: list[str], bump: str, expected: str) -> None:
    assert next_version(tags, bump) == expected


@pytest.mark.parametrize(
    ("tags", "bump", "message"),
    [
        (["1.2.3", "foo", "01.2.3", "bar"], "patch", "invalid tags: foo, 01.2.3, bar"),
        (["foo", "foo"], "patch", "invalid tags: foo, foo"),
        (["V1.2.3"], "patch", "invalid tags: V1.2.3"),
        ([], "patch", "tags must not be empty"),
        ([], "x", "bump must be one of: major, minor, patch"),
        (["foo"], "x", "bump must be one of: major, minor, patch"),
        (["1.2.3"], "MAJOR", "bump must be one of: major, minor, patch"),
        (["1.2.3"], "premajor", "bump must be one of: major, minor, patch"),
        (["1.2.3"], 1, "bump must be one of: major, minor, patch"),
        (["1.2.3"], None, "bump must be one of: major, minor, patch"),
        (["1.2.3"], ["patch"], "bump must be one of: major, minor, patch"),
    ],
)
def test_next_version_errors(tags: list[str], bump: object, message: str) -> None:
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        next_version(tags, bump)
