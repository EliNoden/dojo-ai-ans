"""Black-box bench for POST /next-version.

Usage: uv run --with requests python bench.py [BASE_URL]   (default http://localhost:8080)
"""

import json
import sys
from collections.abc import Callable
from typing import NamedTuple

import requests

JSON = "application/json"


def as_json(payload: object) -> bytes:
    return json.dumps(payload).encode()


class Case(NamedTuple):
    id: str
    category: str  # core | intent | hardening
    check: Callable[[requests.Response], bool]
    data: bytes | None = None
    content_type: str | None = JSON
    method: str = "POST"
    path: str = "/next-version"


def body(r: requests.Response) -> object:
    try:
        return r.json()
    except ValueError:
        return None


def next_is(id: str, category: str, tags: list[str], bump: str, expected: str) -> Case:
    return Case(
        id,
        category,
        lambda r: r.status_code == 200 and body(r) == {"next": expected},
        as_json({"tags": tags, "bump": bump}),
    )


def error_is(id: str, tags: list[str], bump: str, message: str) -> Case:
    return Case(
        id,
        "intent",
        lambda r: r.status_code == 400 and body(r) == {"error": message},
        as_json({"tags": tags, "bump": bump}),
    )


def is_4xx(r: requests.Response) -> bool:
    # 404/405 would mean the route is missing, not that the input was rejected
    return 400 <= r.status_code < 500 and r.status_code not in (404, 405)


def has_error_body(r: requests.Response) -> bool:
    b = body(r)
    return (
        400 <= r.status_code < 500
        and isinstance(b, dict)
        and isinstance(b.get("error"), str)
    )


def status_and_error(status: int) -> Callable[[requests.Response], bool]:
    return lambda r: r.status_code == status and has_error_body(r)


# Smallest valid request; NOMINAL_NEXT is its expected answer (["v1.0.0"] + patch).
NOMINAL = as_json({"tags": ["v1.0.0"], "bump": "patch"})
NOMINAL_NEXT = {"next": "v1.0.1"}


def same_twice(r: requests.Response) -> bool:
    again = requests.Session().send(r.request, timeout=10)
    return body(r) == body(again) == NOMINAL_NEXT


NINES_1000 = "9" * 1000
NINES_1001 = "9" * 1001

# Valid next-version cases. Sources: tt = tests/test_test.py, tv = tests/test_versions.py,
# api = tests/test_next_version_api.py. "-rewritten": the test_test.py expectation contradicted
# docs/specs/next-version.md, so it was recomputed per the spec.
NEXT = [
    # core: same answer under any reasonable reading of the contract
    ("tt-patch", "core", ["v1.0.0"], "patch", "v1.0.1"),
    ("tt-minor", "core", ["v1.2.3"], "minor", "v1.3.0"),
    ("tt-major", "core", ["v1.2.3"], "major", "v2.0.0"),
    ("tt-ascending-input", "core", ["v1.0.0", "v1.1.0", "v1.2.0"], "patch", "v1.2.1"),
    ("tt-descending-input", "core", ["v1.2.0", "v1.1.0", "v1.0.0"], "minor", "v1.3.0"),
    ("tt-numeric-sort-minor", "core", ["v1.9.0", "v1.10.0"], "patch", "v1.10.1"),
    ("tt-numeric-sort-patch", "core", ["v1.2.9", "v1.2.10"], "patch", "v1.2.11"),
    ("tt-numeric-sort-major", "core", ["v2.0.0", "v10.0.0"], "minor", "v10.1.0"),
    (
        "tt-numeric-sort-unordered",
        "core",
        ["v1.9.0", "v1.10.0", "v1.2.0"],
        "minor",
        "v1.11.0",
    ),
    (
        "tt-prerelease-patch-same",
        "intent",
        ["v1.10.0", "v1.10.1-rc.1"],
        "patch",
        "v1.10.1",
    ),
    (
        "tt-prerelease-minor-same",
        "intent",
        ["v1.10.0", "v1.11.0-beta.2"],
        "minor",
        "v1.11.0",
    ),
    (
        "tt-prerelease-major-same",
        "intent",
        ["v1.0.0", "v2.0.0-rc.1"],
        "major",
        "v2.0.0",
    ),
    (
        "tt-prerelease-below-release",
        "intent",
        ["v1.0.0-rc.1", "v1.0.0"],
        "patch",
        "v1.0.1",
    ),
    ("tt-build-metadata", "core", ["v1.4.0+abc"], "patch", "v1.4.1"),
    ("tt-build-metadata-hyphen", "core", ["v1.0.0+b-1"], "patch", "v1.0.1"),
    ("tt-build-metadata-leading-zero", "core", ["v1.0.0+001"], "patch", "v1.0.1"),
    ("tt-zero-patch", "core", ["v0.0.0"], "patch", "v0.0.1"),
    ("tt-zero-major", "core", ["v0.0.0"], "major", "v1.0.0"),
    ("tt-duplicates", "core", ["v1.0.0", "v1.0.0"], "patch", "v1.0.1"),
    ("tt-build-only-differs", "core", ["v1.0.0+a", "v1.0.0+b"], "patch", "v1.0.1"),
    ("tt-big-minor", "core", ["v1.99999.0"], "minor", "v1.100000.0"),
    (
        "tt-20-digits",
        "core",
        ["v99999999999999999999.0.0"],
        "patch",
        "v99999999999999999999.0.1",
    ),
    (
        "tt-1001-digits",
        "core",
        ["v" + NINES_1001 + ".0.0", "v1.0.0"],
        "patch",
        "v" + NINES_1001 + ".0.1",
    ),
    (
        "tt-1000-digits",
        "core",
        ["v" + NINES_1000 + ".0.0"],
        "patch",
        "v" + NINES_1000 + ".0.1",
    ),
    ("tv-prefixed", "core", ["v1.2.3"], "patch", "v1.2.4"),
    ("api-nominal", "core", ["v1.2.3", "v1.10.0", "v1.9.1"], "minor", "v1.11.0"),
    # intent: product choices of docs/specs/next-version.md. Pre-releases are all here: a naive
    # bump_*() or rejecting pre-releases (both reasonable readings) changes the answer.
    (
        "tt-prerelease-counted-rewritten",
        "intent",
        ["v1.0.0", "v5.0.0-rc.1"],
        "major",
        "v5.0.0",
    ),
    ("tt-prerelease-alone-rewritten", "intent", ["v1.0.0-alpha"], "patch", "v1.0.0"),
    ("tt-prerelease-build-rewritten", "intent", ["v1.0.0-rc+b"], "patch", "v1.0.0"),
    ("tt-unprefixed-rewritten", "intent", ["1.0.0"], "patch", "1.0.1"),
    ("tt-prefix-of-max", "intent", ["1.0.0", "v1.1.0"], "patch", "v1.1.1"),
    (
        "tt-prefix-of-max-unprefixed-rewritten",
        "intent",
        ["v1.0.0", "1.1.0"],
        "patch",
        "1.1.1",
    ),
    (
        "tt-prefix-of-max-major-rewritten",
        "intent",
        ["v1.0.0", "9.0.0"],
        "major",
        "10.0.0",
    ),
    ("tv-patch", "intent", ["1.2.3"], "patch", "1.2.4"),
    ("tv-minor", "intent", ["1.2.3"], "minor", "1.3.0"),
    ("tv-major", "intent", ["1.2.3"], "major", "2.0.0"),
    ("tv-numeric-sort", "intent", ["1.9.0", "1.10.0"], "patch", "1.10.1"),
    ("tv-prefix-of-max", "intent", ["v1.0.0", "2.0.0"], "patch", "2.0.1"),
    ("tv-tie-unprefixed-first", "intent", ["1.2.3", "v1.2.3"], "patch", "v1.2.4"),
    ("tv-tie-prefixed-first", "intent", ["v1.2.3", "1.2.3"], "patch", "v1.2.4"),
    ("tv-prerelease-counted", "intent", ["1.3.0-rc.1", "1.2.9"], "patch", "1.3.0"),
    ("tv-build-metadata", "intent", ["1.2.0+build.5"], "patch", "1.2.1"),
    ("tv-duplicates", "intent", ["1.2.3", "1.2.3"], "patch", "1.2.4"),
    ("tv-build-only-differs", "intent", ["1.2.0+a", "1.2.0+b"], "patch", "1.2.1"),
]

# Deterministic sample for the property "next > every tag" (release-only, v-prefixed), on lists
# a lexical sort gets wrong: (tags, next major, next minor, next patch)
GREATER = [
    (["v3.2.1", "v3.10.0", "v3.9.9"], "v4.0.0", "v3.11.0", "v3.10.1"),
    (["v10.0.0", "v9.99.99"], "v11.0.0", "v10.1.0", "v10.0.1"),
    (["v12.3.4", "v12.3.40", "v12.30.4"], "v13.0.0", "v12.31.0", "v12.30.5"),
]

INVALID_TAG_ERRORS = [
    (
        "tt-invalid-ignored-rewritten",
        ["v1.0.0", "latest", "foo"],
        "patch",
        "invalid tags: latest, foo",
    ),
    (
        "tt-invalid-shapes-rewritten",
        ["v1.0.0", "v1.2", "v1.2.3.4", "v01.3.0"],
        "minor",
        "invalid tags: v1.2, v1.2.3.4, v01.3.0",
    ),
    (
        "tt-invalid-uppercase-v-rewritten",
        ["V9.0.0", "v1.0.0"],
        "patch",
        "invalid tags: V9.0.0",
    ),
    (
        "tt-invalid-build-rewritten",
        ["v1.0.0+a..b", "v1.0.0+.a", "v1.0.0+a.", "v1.0.0+a+b"],
        "patch",
        "invalid tags: v1.0.0+a..b, v1.0.0+.a, v1.0.0+a., v1.0.0+a+b",
    ),
    (
        "tt-invalid-control-chars-rewritten",
        ["v1.0.0\u0000", "ｖ1.0.0", "v1.\t0.0"],
        "patch",
        "invalid tags: v1.0.0\u0000, ｖ1.0.0, v1.\t0.0",
    ),
    (
        "tt-invalid-empty-strings-rewritten",
        ["", "v", "v1.0.0"],
        "patch",
        "invalid tags: , v",
    ),
    (
        "tt-invalid-whitespace-rewritten",
        [" v1.0.0 ", "v1.0.0\n", "vv1.0.0", "v1.0.0-", "v1.0.0+"],
        "patch",
        "invalid tags:  v1.0.0 , v1.0.0\n, vv1.0.0, v1.0.0-, v1.0.0+",
    ),
    (
        "tt-invalid-unicode-digits-rewritten",
        ["v１.0.0", "v١.0.0"],
        "patch",
        "invalid tags: v１.0.0, v١.0.0",
    ),
    (
        "tt-invalid-only-rewritten",
        ["latest", "foo"],
        "major",
        "invalid tags: latest, foo",
    ),
    ("tt-empty-patch-rewritten", [], "patch", "tags must not be empty"),
    ("tt-empty-minor-rewritten", [], "minor", "tags must not be empty"),
    ("tt-empty-major-rewritten", [], "major", "tags must not be empty"),
    (
        "tv-invalid-listed-in-order",
        ["latest", "1.2.3", "V1.2.3", "vv1.2.3", " 1.2.3"],
        "patch",
        "invalid tags: latest, V1.2.3, vv1.2.3,  1.2.3",
    ),
    ("api-invalid-tag", ["1.2.3", "latest"], "patch", "invalid tags: latest"),
]


# Invalid inputs (core): any reasonable implementation answers 4xx, never 5xx.
INVALID_INPUTS = {
    "tt-bump-absent": as_json({"tags": ["v1.0.0"]}),
    "tt-bump-unknown": as_json({"tags": ["v1.0.0"], "bump": "huge"}),
    "tt-bump-uppercase": as_json({"tags": ["v1.0.0"], "bump": "MAJOR"}),
    "tt-bump-space": as_json({"tags": ["v1.0.0"], "bump": " patch"}),
    "tt-bump-null": as_json({"tags": ["v1.0.0"], "bump": None}),
    "tt-bump-list": as_json({"tags": ["v1.0.0"], "bump": ["patch"]}),
    "tt-tags-absent": as_json({"bump": "patch"}),
    "tt-tags-string": as_json({"tags": "v1.0.0", "bump": "patch"}),
    "tt-tags-int-item": as_json({"tags": [1, "v1.0.0"], "bump": "patch"}),
    "tt-tags-null": as_json({"tags": None, "bump": "patch"}),
    "tt-tags-nested-list": as_json({"tags": [["v1.0.0"]], "bump": "patch"}),
    "tt-tags-bool-item": as_json({"tags": [True], "bump": "patch"}),
    "tt-broken-json": b"{not json",
    "tt-empty-body": b"",
    "tt-null-body": b"null",
    "tt-non-utf8-body": b"\xff\xfe",
    "tt-array-body": as_json(["v1.0.0"]),
    "tt-nested-100000": b"[" * 100_000 + b"]" * 100_000,
    "api-bump-capitalized": as_json({"tags": ["1.2.3"], "bump": "Patch"}),
}

# Hardening: a few representative bad inputs must answer a JSON {"error": str}.
ERROR_BODY_INPUTS = {
    "bad-bump": INVALID_INPUTS["tt-bump-unknown"],
    "bad-tags-type": INVALID_INPUTS["tt-tags-string"],
    "broken-json": INVALID_INPUTS["tt-broken-json"],
    "array-body": INVALID_INPUTS["tt-array-body"],
    "invalid-tag": as_json({"tags": ["v1.0.0", "latest"], "bump": "patch"}),
}

CASES: list[Case] = [
    *(next_is(id, cat, tags, bump, expected) for id, cat, tags, bump, expected in NEXT),
    *(
        next_is(f"greater-{i}-{bump}", "core", tags, bump, expected)
        for i, (tags, *nexts) in enumerate(GREATER)
        for bump, expected in zip(("major", "minor", "patch"), nexts)
    ),
    *(
        error_is(id, tags, bump, message)
        for id, tags, bump, message in INVALID_TAG_ERRORS
    ),
    *(Case(f"{id}-4xx", "core", is_4xx, data) for id, data in INVALID_INPUTS.items()),
    *(
        Case(f"{id}-error-body", "hardening", has_error_body, data)
        for id, data in ERROR_BODY_INPUTS.items()
    ),
    Case("identical-calls-same-body", "core", same_twice, NOMINAL),
    Case(
        "response-is-json-with-next",
        "core",
        lambda r: (
            r.headers.get("Content-Type", "").startswith(JSON)
            and isinstance(body(r), dict)
            and "next" in body(r)
        ),
        NOMINAL,
    ),
    Case(
        "charset-utf8-accepted",
        "core",
        lambda r: body(r) == NOMINAL_NEXT,
        NOMINAL,
        "application/json; charset=utf-8",
    ),
    Case(
        "get-405-allow-post",
        "core",
        lambda r: r.status_code == 405 and "POST" in r.headers.get("Allow", ""),
        method="GET",
    ),
    # hardening: rarely asked, about half of the category
    Case("get-405-json", "hardening", status_and_error(405), method="GET"),
    Case("unknown-route-404-json", "hardening", status_and_error(404), path="/nope"),
    Case("old-route-404-json", "hardening", status_and_error(404), path="/refs/next"),
    Case("no-content-type-415", "hardening", status_and_error(415), NOMINAL, None),
    Case("text-plain-415", "hardening", status_and_error(415), NOMINAL, "text/plain"),
    Case(
        "form-415",
        "hardening",
        status_and_error(415),
        NOMINAL,
        "application/x-www-form-urlencoded",
    ),
    Case(
        "body-over-1mb-413",
        "hardening",
        status_and_error(413),
        as_json({"tags": ["x" * 1024 * 1024], "bump": "patch"}),
    ),
]


def run(base_url: str, case: Case) -> tuple[bool, str]:
    headers = {"Content-Type": case.content_type} if case.content_type else {}
    try:
        r = requests.request(
            case.method,
            base_url + case.path,
            data=case.data,
            headers=headers,
            timeout=10,
        )
        return case.check(r), f"{r.status_code} {r.text[:120]!r}"
    except requests.RequestException as e:
        return False, type(e).__name__


def main() -> None:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip(
        "/"
    )
    ids = [c.id for c in CASES]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    try:
        requests.get(base_url, timeout=5)
    except requests.RequestException:
        print(f"server not reachable at {base_url}")
        sys.exit(2)

    score: dict[str, list[int]] = {
        "core": [0, 0],
        "intent": [0, 0],
        "hardening": [0, 0],
    }
    for case in CASES:
        ok, detail = run(base_url, case)
        score[case.category][0] += ok
        score[case.category][1] += 1
        if not ok:
            print(f"FAIL [{case.category}] {case.id}: {detail}")

    print()
    score["total"] = [
        sum(s[0] for s in score.values()),
        sum(s[1] for s in score.values()),
    ]
    for name, (passed, total) in score.items():
        print(f"{name}: {passed}/{total} ({100 * passed / total:.1f} %)")


if __name__ == "__main__":
    main()
