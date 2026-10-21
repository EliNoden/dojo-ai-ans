from random import Random

from hypothesis import given
from hypothesis import strategies as st

from versions import next_version, parse_tag, precedence_key

_identifier = st.one_of(
    st.from_regex(r"[0-9]{1,5}", fullmatch=True),
    st.from_regex(r"[0-9A-Za-z-]{1,5}", fullmatch=True),
)
_identifiers = st.lists(_identifier, min_size=1, max_size=3).map(".".join)
_tag = st.builds(
    lambda v, x, y, z, pre, build: (
        f"{v}{x}.{y}.{z}" + (f"-{pre}" if pre else "") + (f"+{build}" if build else "")
    ),
    st.sampled_from(["", "v"]),
    st.integers(0, 50),
    st.integers(0, 50),
    st.integers(0, 50),
    st.one_of(st.none(), _identifiers),
    st.one_of(st.none(), _identifiers),
)
_tags = st.lists(_tag, min_size=1, max_size=8)
_bump = st.sampled_from(["major", "minor", "patch"])


@given(_tags, _bump)
def test_result_is_greater_than_every_tag(tags: list[str], bump: str) -> None:
    result = parse_tag(next_version(tags, bump))
    assert result is not None
    assert result.prerelease == ()
    for tag in tags:
        parsed = parse_tag(tag)
        assert parsed is not None
        assert precedence_key(result) > precedence_key(parsed)


@given(_tags, _bump, st.randoms(use_true_random=False))
def test_result_does_not_depend_on_tag_order(
    tags: list[str], bump: str, random: Random
) -> None:
    shuffled = list(tags)
    random.shuffle(shuffled)
    assert next_version(shuffled, bump) == next_version(tags, bump)
