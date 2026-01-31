# make_repo_links.py
# PyCharm-friendly: edit the CONFIG block, then Run.

from __future__ import annotations

import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# --------------------------- CONFIG ---------------------------

OWNER = "mortlach"
REPO = "RuneDecrypterPrime"
BRANCH = "local_stress"

OUT_JSON = "repo_links.json"
OUT_CSV = "repo_links.csv"

# If you only want code/docs (recommended), keep this True.
TEXT_ONLY = False

# Extension allow-list used when TEXT_ONLY is True.
ALLOW_EXT = {
    ".py", ".pyi",
    ".md", ".txt", ".rst",
    ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".csv", ".tsv",
}

# Optional: skip huge files even if extension matches
MAX_SIZE_BYTES: Optional[int] = 2_000_000  # 2 MB; set to None to disable

# Optional: skip directories by prefix
EXCLUDE_PREFIXES = (
    ".git/",
    "src/rune_decrypter_prime/data/",   # huge LM artefacts live here
)

# Optional: set a token to avoid rate limits (fine to leave blank)
GITHUB_TOKEN = ""  # or paste a token, or leave blank


# --------------------------------------------------------------


@dataclass(frozen=True)
class LinkRow:
    path: str
    size: int
    blob_branch_url: str
    raw_branch_url: str
    blob_commit_url: str
    raw_commit_url: str

def _resolve_branch_commit(owner: str, repo: str, branch: str, token: str = "") -> str:
    ref = _http_json(
        f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}",
        token,
    )
    return ref["object"]["sha"]

def _make_urls(
    owner: str,
    repo: str,
    branch: str,
    commit_sha: str,
    path: str,
) -> tuple[str, str, str, str]:
    quoted_path = "/".join(urllib.parse.quote(p) for p in path.split("/"))

    blob_branch = f"https://github.com/{owner}/{repo}/blob/{branch}/{quoted_path}"
    raw_branch  = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{quoted_path}"

    blob_commit = f"https://github.com/{owner}/{repo}/blob/{commit_sha}/{quoted_path}"
    raw_commit  = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit_sha}/{quoted_path}"

    return blob_branch, raw_branch, blob_commit, raw_commit


def _http_json(url: str, token: str = "") -> Dict[str, Any]:
    headers = {
        "User-Agent": "repo-links-script",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_tree_sha(owner: str, repo: str, branch: str, token: str = "") -> str:
    # 1) Resolve branch -> commit SHA
    ref = _http_json(f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}", token)
    commit_sha = ref["object"]["sha"]

    # 2) Commit SHA -> tree SHA
    commit = _http_json(f"https://api.github.com/repos/{owner}/{repo}/git/commits/{commit_sha}", token)
    return commit["tree"]["sha"]


def _get_repo_tree(owner: str, repo: str, tree_sha: str, token: str = "") -> Dict[str, Any]:
    # recursive=1 returns all blobs/trees in one shot (repo must not exceed API limits)
    return _http_json(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1", token)


def _should_include(path: str, size: int) -> bool:
    if any(path.startswith(pfx) for pfx in EXCLUDE_PREFIXES):
        return False
    if not TEXT_ONLY:
        return True
    _, ext = os.path.splitext(path.lower())
    if ext not in ALLOW_EXT:
        return False
    if MAX_SIZE_BYTES is not None and size > MAX_SIZE_BYTES:
        return False
    return True



def main() -> None:
    token = (GITHUB_TOKEN or "").strip()

    commit_sha = _resolve_branch_commit(OWNER, REPO, BRANCH, token)
    tree_sha = _get_tree_sha(OWNER, REPO, BRANCH, token)
    tree = _get_repo_tree(OWNER, REPO, tree_sha, token)

    if tree.get("truncated"):
        raise RuntimeError("GitHub API returned a truncated tree.")

    rows: list[LinkRow] = []

    for item in tree.get("tree", []):
        if item.get("type") != "blob":
            continue

        path = item.get("path", "")
        size = int(item.get("size", 0) or 0)

        if not path or not _should_include(path, size):
            continue

        bb, rb, bc, rc = _make_urls(
            OWNER, REPO, BRANCH, commit_sha, path
        )

        rows.append(
            LinkRow(
                path=path,
                size=size,
                blob_branch_url=bb,
                raw_branch_url=rb,
                blob_commit_url=bc,
                raw_commit_url=rc,
            )
        )

    rows.sort(key=lambda r: r.path.lower())
    payload = {
        "repo": f"{OWNER}/{REPO}",
        "branch": BRANCH,
        "commit": commit_sha,
        "text_only": TEXT_ONLY,
        "generated_by": "make_repo_links.py",
        "files": [r.__dict__ for r in rows],
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "path",
                "size",
                "blob_branch_url",
                "raw_branch_url",
                "blob_commit_url",
                "raw_commit_url",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r.__dict__)

    print(f"Wrote {len(rows)} rows for commit {commit_sha}")



if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
