"""Compute the next version to tag from existing SemVer tags."""

from typing import Literal

from semver import Version

type Bump = Literal["major", "minor", "patch"]


class InvalidTagsError(ValueError):
    pass


class EmptyTagsError(ValueError):
    pass


def _parse(tag: str) -> tuple[Version, bool] | None:
    """Return (version, has "v" prefix), or None if the tag is invalid."""
    has_v = tag.startswith("v")
    raw = tag.removeprefix("v")
    if not Version.is_valid(raw):
        return None
    return Version.parse(raw), has_v


def next_version(tags: list[str], bump: Bump) -> str:
    if not tags:
        raise EmptyTagsError("tags must not be empty")
    parsed = [_parse(tag) for tag in tags]
    invalid = [tag for tag, p in zip(tags, parsed) if p is None]
    if invalid:
        raise InvalidTagsError("invalid tags: " + ", ".join(invalid))
    # Version order ignores build metadata; on a tie, the "v" prefix wins.
    base, has_v = max(p for p in parsed if p is not None)
    if base.prerelease is None:
        base = base.next_version(bump)
    return ("v" if has_v else "") + f"{base.major}.{base.minor}.{base.patch}"
