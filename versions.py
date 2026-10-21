import re
from dataclasses import dataclass

BUMPS = ("major", "minor", "patch")

_NUM = r"(0|[1-9][0-9]*)"
_IDENTS = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
_TAG = re.compile(rf"(v)?{_NUM}\.{_NUM}\.{_NUM}(?:-({_IDENTS}))?(?:\+({_IDENTS}))?")


@dataclass(frozen=True)
class Version:
    prefix: str
    major: int
    minor: int
    patch: int
    pre: tuple[str, ...]

    def precedence_key(self):
        # A final version sorts above any of its pre-releases.
        pre_key = (1,) if not self.pre else (0, *(_ident_key(i) for i in self.pre))
        return (self.major, self.minor, self.patch, pre_key)


def _ident_key(ident):
    # SemVer: numeric identifiers sort numerically and below alphanumeric ones.
    return (0, int(ident), "") if ident.isdigit() else (1, 0, ident)


def parse_tag(tag):
    m = _TAG.fullmatch(tag)
    if not m:
        return None
    prefix, major, minor, patch, pre, _build = m.groups()
    return Version(
        prefix=prefix or "",
        major=int(major),
        minor=int(minor),
        patch=int(patch),
        pre=tuple(pre.split(".")) if pre else (),
    )


def highest(versions):
    top = max(v.precedence_key() for v in versions)
    tied = [v for v in versions if v.precedence_key() == top]
    # On a tie, the "v" prefix wins.
    return next((v for v in tied if v.prefix), tied[0])


def bump(v, kind):
    x, y, z = v.major, v.minor, v.patch
    if kind == "major":
        # 2.0.0-rc.1 -> 2.0.0, otherwise next major.
        x, y, z = (x, 0, 0) if v.pre and y == 0 and z == 0 else (x + 1, 0, 0)
    elif kind == "minor":
        # 1.3.0-rc.1 -> 1.3.0, otherwise next minor.
        x, y, z = (x, y, 0) if v.pre and z == 0 else (x, y + 1, 0)
    else:
        # 1.3.0-rc.1 -> 1.3.0, otherwise next patch.
        z = z if v.pre else z + 1
    return f"{v.prefix}{x}.{y}.{z}"
