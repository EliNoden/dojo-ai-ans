import re
from dataclasses import dataclass

BUMPS = ("major", "minor", "patch")
_NUMBER = r"(0|[1-9][0-9]{0,14})"
_IDENTIFIERS = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
_TAG = re.compile(
    rf"(v)?{_NUMBER}\.{_NUMBER}\.{_NUMBER}(?:-({_IDENTIFIERS}))?(?:\+{_IDENTIFIERS})?"
)


type IdentifierKey = tuple[bool, int, str] | tuple[bool, str]
type PrecedenceKey = tuple[int, int, int, bool, tuple[IdentifierKey, ...]]


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...]
    has_v: bool


def _identifier_key(identifier: str) -> IdentifierKey:
    # Numeric ids sort before alphanumeric ones (False < True); numeric ids are
    # compared by (length, string) so that no int() conversion is needed.
    if identifier.isdecimal():
        return (False, len(identifier), identifier)
    return (True, identifier)


def precedence_key(version: Version) -> PrecedenceKey:
    return (
        version.major,
        version.minor,
        version.patch,
        not version.prerelease,
        tuple(_identifier_key(i) for i in version.prerelease),
    )


def parse_tag(tag: str) -> Version | None:
    match = _TAG.fullmatch(tag)
    if match is None:
        return None
    v, major, minor, patch, prerelease = match.groups()
    return Version(
        int(major),
        int(minor),
        int(patch),
        tuple(prerelease.split(".")) if prerelease else (),
        v is not None,
    )


def next_version(tags: list[str], bump: object) -> str:
    """Return the next version; raise ValueError(message) on invalid input."""
    if bump not in BUMPS:
        raise ValueError(f"bump must be one of: {', '.join(BUMPS)}")
    if not tags:
        raise ValueError("tags must not be empty")
    parsed = [parse_tag(tag) for tag in tags]
    invalid = [tag for tag, version in zip(tags, parsed) if version is None]
    if invalid:
        raise ValueError(f"invalid tags: {', '.join(invalid)}")
    versions = [version for version in parsed if version is not None]
    highest = max(precedence_key(version) for version in versions)
    top = [version for version in versions if precedence_key(version) == highest]
    base = top[0]
    prefix = "v" if any(version.has_v for version in top) else ""
    major, minor, patch = base.major, base.minor, base.patch
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    elif not base.prerelease:
        patch += 1
    return f"{prefix}{major}.{minor}.{patch}"
