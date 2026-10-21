import re

_NUM = r"0|[1-9][0-9]*"
_IDENTS = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
TAG_RE = re.compile(
    rf"(?P<prefix>v)?(?P<major>{_NUM})\.(?P<minor>{_NUM})\.(?P<patch>{_NUM})"
    rf"(?:-(?P<pre>{_IDENTS}))?(?:\+(?P<build>{_IDENTS}))?"
)

BUMPS = ("major", "minor", "patch")


def _sort_key(match):
    """Precedence key: X, Y, Z, then final > pre-release, then 'v' wins ties.

    Build metadata is ignored. Pre-releases with the same X.Y.Z are ordered
    per semver: numeric identifiers numerically and below alphanumeric ones.
    """
    pre = match["pre"]
    pre_key = tuple(
        (0, int(ident)) if ident.isdigit() else (1, ident)
        for ident in (pre.split(".") if pre else ())
    )
    return (
        int(match["major"]),
        int(match["minor"]),
        int(match["patch"]),
        pre is None,
        pre_key,
        match["prefix"] is not None,
    )


def next_version(tags, bump):
    """Return the next version string, or raise ValueError with the error message."""
    if not tags:
        raise ValueError("tags must not be empty")

    matches = [TAG_RE.fullmatch(tag) for tag in tags]
    invalid = [tag for tag, match in zip(tags, matches) if match is None]
    if invalid:
        raise ValueError(f"invalid tags: {', '.join(invalid)}")

    base = max(matches, key=_sort_key)
    major, minor, patch = int(base["major"]), int(base["minor"]), int(base["patch"])

    if base["pre"] is None:
        if bump == "major":
            major, minor, patch = major + 1, 0, 0
        elif bump == "minor":
            minor, patch = minor + 1, 0
        else:
            patch += 1
    # Bumping a pre-release just finalizes it, whatever the bump.

    return f"{base['prefix'] or ''}{major}.{minor}.{patch}"
