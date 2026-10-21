"""Bench several iterations side by side.

Usage: uv run --with requests python compare.py [REF ...]   (default: every origin/feat/prompt-*)

Each REF is looked up as origin/REF first, then as any git ref (local branch, commit).
For each one: temporary detached worktree, `uv sync`, gunicorn "specs:create_app()" on a
free port, bench.run, then the server is killed and the worktree removed.
"""

import contextlib
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time

import bench

COLUMNS = ["core", "intent", "hardening", "total"]
STARTUP_TIMEOUT = 20  # seconds


def git(root: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", root, *args], check=False, capture_output=True, text=True
    )


def resolve(root: str, name: str) -> str | None:
    for ref in (f"origin/{name}", name):
        found = git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if found.returncode == 0:
            return found.stdout.strip()
    return None


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


def wait_until_listening(port: int, server: subprocess.Popen[bytes]) -> None:
    # TCP connect rather than an HTTP route: an iteration may have no /hello
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError("server exited at startup (no specs:create_app?)")
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"server not listening after {STARTUP_TIMEOUT} s")


def bench_commit(root: str, commit: str) -> dict[str, tuple[int, int]]:
    with tempfile.TemporaryDirectory(prefix="bench-") as tmp:
        wt = os.path.join(tmp, "wt")
        server = None
        try:
            added = git(root, "worktree", "add", "--detach", wt, commit)
            if added.returncode:
                raise RuntimeError(f"worktree add failed: {added.stderr.strip()}")
            sync = subprocess.run(
                ["uv", "sync"], cwd=wt, check=False, capture_output=True, text=True
            )
            if sync.returncode:
                last = (sync.stderr or sync.stdout).strip().splitlines()[-1:]
                raise RuntimeError(f"uv sync failed: {' '.join(last).strip()}")
            port = free_port()
            # --preload: a broken app fails before the port is bound, not after
            server = subprocess.Popen(
                ["uv", "run", "--project", wt, "gunicorn", "-w", "2", "--preload"]
                + ["-b", f"127.0.0.1:{port}", "specs:create_app()"],
                cwd=wt,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # own process group: uv, gunicorn and workers
            )
            wait_until_listening(port, server)
            return bench.run(f"http://127.0.0.1:{port}", quiet=True)
        finally:
            if server:
                # the group may already be gone (server died at startup):
                # ESRCH on Linux, EPERM on macOS
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(server.pid, signal.SIGKILL)
                server.wait()
            git(root, "worktree", "remove", "--force", wt)


def cell(passed: int, total: int) -> str:
    return f"{passed}/{total} {round(100 * passed / total):2d}%"


def main() -> None:
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if top.returncode:
        print("compare.py must run inside the git repository")
        sys.exit(1)
    root = top.stdout.strip()

    git(root, "worktree", "prune")
    if git(root, "fetch", "origin").returncode:
        print("warning: git fetch origin failed, using local refs", file=sys.stderr)
    names = sys.argv[1:] or [
        ref.removeprefix("origin/")
        for ref in git(
            root,
            "for-each-ref",
            "--format=%(refname:short)",
            "refs/remotes/origin/feat/prompt-*",
        ).stdout.split()
    ]
    if not names:
        print("no origin/feat/prompt-* branches found")
        sys.exit(1)

    width = max(len(n) for n in ["branch", *names]) + 3
    print(("branch".ljust(width) + "".join(c.ljust(14) for c in COLUMNS)).rstrip())
    for name in names:
        commit = resolve(root, name)
        if commit is None:
            row = "ERROR: unknown branch"
        else:
            try:
                score = bench_commit(root, commit)
                row = "".join(cell(*score[c]).ljust(14) for c in COLUMNS)
            except RuntimeError as e:
                row = f"ERROR: {e}"
        print(name.ljust(width) + row.rstrip(), flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
