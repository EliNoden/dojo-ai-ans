from typing import Literal

from semver import Version


class InvalidTagsError(ValueError):
    pass


def next_version(tags: list[str], bump: Literal["major", "minor", "patch"]) -> str:
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
        raise InvalidTagsError(f"invalid tags: {', '.join(invalid)}")
    version, has_v = max(parsed)
    return f"{'v' if has_v else ''}{version.next_version(bump)}"
