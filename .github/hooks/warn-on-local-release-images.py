from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath


RELEASE_GLOBS = (
    "docker-compose.yml",
    "docker-compose.release.yml",
    "deploy/local-runtime/**",
    "scripts/docker-up.ps1",
    "scripts/install.ps1",
    "scripts/prepare_runtime_bundle.ps1",
    "README.md",
    "INSTALL_FORK_WINDOWS.md",
)


def run_git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def is_release_surface(path_text: str) -> bool:
    path = PurePosixPath(path_text.replace("\\", "/"))
    return any(path.match(pattern) for pattern in RELEASE_GLOBS)


def added_local_refs_from_diff(diff_text: str) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    current_path: str | None = None

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            candidate = line[6:]
            current_path = candidate if is_release_surface(candidate) else None
            continue

        if not current_path or not line.startswith("+") or line.startswith("+++"):
            continue

        if ":local" not in line:
            continue

        matches.setdefault(current_path, []).append(line[1:].strip())

    return matches


def added_local_refs_from_untracked(repo_root: Path) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    untracked = run_git(repo_root, ["ls-files", "--others", "--exclude-standard"]) 

    for raw_path in untracked.splitlines():
        if not raw_path or not is_release_surface(raw_path):
            continue

        file_path = repo_root / raw_path
        if not file_path.is_file():
            continue

        lines = []
        try:
            for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if ":local" in line:
                    lines.append(line.strip())
        except OSError:
            continue

        if lines:
            matches[raw_path] = lines

    return matches


def merge_matches(*groups: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for group in groups:
        for path, lines in group.items():
            bucket = merged.setdefault(path, [])
            for line in lines:
                if line not in bucket:
                    bucket.append(line)
    return merged


def emit_warning(matches: dict[str, list[str]]) -> None:
    details = "; ".join(f"{path}: {lines[0]}" for path, lines in sorted(matches.items()))
    message = (
        "Release-facing changes added `:local` image references. "
        "If this change is meant for GHCR or client upgrades, prefer `ghcr.io/...` references plus an explicit local-dev fallback. "
        f"Examples: {details}"
    )
    print(json.dumps({"continue": True, "systemMessage": message}))


def main() -> int:
    try:
        if not sys.stdin.isatty():
            json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    repo_root = Path(__file__).resolve().parents[2]
    unstaged = added_local_refs_from_diff(run_git(repo_root, ["diff", "--unified=0", "--", *RELEASE_GLOBS]))
    staged = added_local_refs_from_diff(run_git(repo_root, ["diff", "--cached", "--unified=0", "--", *RELEASE_GLOBS]))
    untracked = added_local_refs_from_untracked(repo_root)

    matches = merge_matches(unstaged, staged, untracked)
    if matches:
        emit_warning(matches)
    else:
        print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())