"""Pure SemVer logic: compute the next version from a list of git tags."""

from typing import Literal

from semver import Version

Bump = Literal["major", "minor", "patch"]
BUMPS: tuple[Bump, ...] = ("major", "minor", "patch")


def next_version(tags: list[str], bump: Bump) -> str:
    """Bump the highest tag; an optional lowercase `v` prefix of the highest is kept."""
    if not tags:
        raise ValueError("tags must not be empty")
    parsed: list[tuple[Version, bool]] = []
    invalid: list[str] = []
    for tag in tags:
        try:
            parsed.append((Version.parse(tag.removeprefix("v")), tag.startswith("v")))
        except ValueError:
            invalid.append(tag)
    if invalid:
        raise ValueError(f"invalid tags: {', '.join(invalid)}")
    version, has_v = max(parsed)
    return ("v" if has_v else "") + str(version.next_version(bump))
