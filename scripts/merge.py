#!/usr/bin/env python3
"""Make a channel's source tree: the base commit with the listed branches merged on top.

The merges are made with `git merge-tree` and `git commit-tree` under a fixed identity and date
(the spec's `time`), so every job that runs this with the same spec gets the same commit.

As a module: build_source(spec, dir, checkout) -> {"head", "version", "merge": [...with status]}.
  Entries without a "status" are tried; a conflict marks them "conflicts" and moves on.
  Entries with a "status" other than "merged" are left out (a build job repeating the plan).
As a script: merge.py SPEC.json DIR  (a build job): checks out the tree into DIR and prints the head.

Needs git 2.38 or newer (merge-tree --write-tree). Python 3.8+, no third-party modules.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

NAME = "SolidCraft preview builds"
EMAIL = "preview-builds@users.noreply.github.com"


def git(cwd: Path, *args: str, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, env=env)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed ({p.returncode}): {p.stderr.strip()}")
    return p


def workspace_version(cargo_toml: str) -> str:
    section = ""
    for line in cargo_toml.splitlines():
        s = line.strip()
        if s.startswith("["):
            section = s
            continue
        if section == "[workspace.package]":
            m = re.match(r'version\s*=\s*"([^"]+)"', s)
            if m:
                return m.group(1)
    return "0.0.0"


def build_source(spec: dict, dest: Path, checkout: bool) -> dict:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    git(dest, "init", "-q")
    git(dest, "config", "core.longpaths", "true")
    base = spec["base"]
    git(dest, "fetch", "-q", "--filter=blob:none", "--no-tags", f"https://github.com/{base['repo']}.git", base["sha"])
    head = base["sha"]

    when = f"{int(spec['time'])} +0000"
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME=NAME,
        GIT_AUTHOR_EMAIL=EMAIL,
        GIT_AUTHOR_DATE=when,
        GIT_COMMITTER_NAME=NAME,
        GIT_COMMITTER_EMAIL=EMAIL,
        GIT_COMMITTER_DATE=when,
    )

    results = []
    for m in spec.get("merge", []):
        entry = dict(m)
        status = entry.get("status")
        if status not in (None, "merged"):
            results.append(entry)
            continue
        if not entry.get("sha"):
            entry["status"] = "missing"
            entry["reason"] = "branch not found"
            results.append(entry)
            continue
        fetched = git(dest, "fetch", "-q", "--filter=blob:none", "--no-tags",
                      f"https://github.com/{entry['repo']}.git", entry["sha"], check=False)
        if fetched.returncode != 0:
            if status == "merged":
                raise RuntimeError(f"could not fetch {entry['repo']} {entry['sha']}: {fetched.stderr.strip()}")
            entry["status"] = "missing"
            entry["reason"] = "commit could not be fetched"
            results.append(entry)
            continue
        if git(dest, "merge-base", "--is-ancestor", entry["sha"], head, check=False).returncode == 0:
            entry["status"] = "merged"
            entry["note"] = "already contained in the base"
            results.append(entry)
            continue
        mt = git(dest, "merge-tree", "--write-tree", "--name-only", "--no-messages", head, entry["sha"], check=False)
        if mt.returncode != 0:
            if status == "merged":
                raise RuntimeError(f"{entry['branch']} merged in the plan but conflicts now")
            lines = mt.stdout.strip().splitlines()
            entry["status"] = "conflicts"
            entry["reason"] = "conflicts in " + ", ".join(lines[1:6]) + (" and more" if len(lines) > 6 else "")
            results.append(entry)
            continue
        tree = mt.stdout.strip().splitlines()[0]
        msg = f"Merge {entry['repo']} {entry['branch']}"
        head = git(dest, "commit-tree", tree, "-p", head, "-p", entry["sha"], "-m", msg, env=env).stdout.strip()
        entry["status"] = "merged"
        results.append(entry)

    version = workspace_version(git(dest, "show", f"{head}:Cargo.toml").stdout)
    if checkout:
        git(dest, "checkout", "-q", "--detach", head)
    return {"head": head, "version": version, "merge": results}


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    spec = json.loads(Path(sys.argv[1]).read_text())
    result = build_source(spec, Path(sys.argv[2]), checkout=True)
    if spec.get("head") and result["head"] != spec["head"]:
        print(f"error: made {result['head']}, the plan made {spec['head']}", file=sys.stderr)
        return 1
    print(result["head"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
