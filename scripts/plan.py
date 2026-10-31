#!/usr/bin/env python3
"""Decide which channels need a new build.

For each channel in channels.toml: read the head commit of its base branch and of every branch it
merges (git ls-remote). If that set differs from the one the channel's latest release was built
from, and no earlier run already tried it, merge the branches in a scratch clone to find out which
ones merge cleanly, and write the build spec.

Usage: plan.py [--channel NAME|all] [--force]

Writes to $GITHUB_OUTPUT (or prints): matrix=[{"channel": ..., "spec": "<json>"}], any=true|false.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from merge import build_source  # noqa: E402


def run(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, text=True, capture_output=True, **kw)


def head_sha(repo: str, branch: str) -> str | None:
    out = run(["git", "ls-remote", f"https://github.com/{repo}.git", f"refs/heads/{branch}"])
    if out.returncode != 0:
        print(f"::warning::ls-remote {repo} {branch}: {out.stderr.strip()}", file=sys.stderr)
        return None
    line = out.stdout.strip().splitlines()
    return line[0].split()[0] if line else None


def latest_info(channel: str) -> dict | None:
    out = run(["gh", "release", "download", f"{channel}-latest", "--pattern", "build-info.json", "--output", "-"])
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def attempted(channel: str, key: str) -> bool:
    out = run(["gh", "cache", "list", "--key", f"attempt-{channel}-{key}", "--json", "key"])
    if out.returncode != 0:
        print(f"::warning::cache list: {out.stderr.strip()}", file=sys.stderr)
        return False
    try:
        return any(c.get("key") == f"attempt-{channel}-{key}" for c in json.loads(out.stdout or "[]"))
    except json.JSONDecodeError:
        return False


def pr_details(pr_repo: str, pr: int) -> dict:
    out = run(["gh", "api", f"repos/{pr_repo}/pulls/{pr}", "--jq", "{title, url: .html_url, state, draft, merged}"])
    if out.returncode != 0:
        return {"url": f"https://github.com/{pr_repo}/pull/{pr}"}
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"url": f"https://github.com/{pr_repo}/pull/{pr}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="all")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    config = tomllib.loads((ROOT / "channels.toml").read_text())["channels"]
    names = list(config) if a.channel in ("", "all") else [a.channel]
    for n in names:
        if n not in config:
            print(f"::error::no channel named {n} in channels.toml", file=sys.stderr)
            return 1

    now = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    matrix = []
    for name in names:
        ch = config[name]
        base = dict(ch["base"])
        base["sha"] = head_sha(base["repo"], base["branch"])
        if not base["sha"]:
            print(f"::error::{name}: base {base['repo']} {base['branch']} not found", file=sys.stderr)
            continue
        pr_repo = ch.get("pr_repo", "tangency-labs/solidcraft")
        merges = []
        for m in ch.get("merge", []):
            entry = {"repo": m["repo"], "branch": m["branch"], "sha": head_sha(m["repo"], m["branch"])}
            if "pr" in m:
                entry["pr"] = int(m["pr"])
                entry["pr_repo"] = pr_repo
            merges.append(entry)
        inputs = {"base": base, "merge": [{k: e[k] for k in ("repo", "branch", "sha")} for e in merges]}
        key = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]

        info = latest_info(name)
        if not a.force:
            if info and info.get("key") == key:
                print(f"{name}: unchanged since {info.get('tag')} (key {key})")
                continue
            if attempted(name, key):
                print(f"{name}: key {key} was already tried by an earlier run; skipping (dispatch with force to retry)")
                continue

        for e in merges:
            if "pr" in e:
                e.update({k: v for k, v in pr_details(pr_repo, e["pr"]).items() if v is not None})

        # Trial merge in a scratch clone: which branches merge cleanly.
        with tempfile.TemporaryDirectory() as tmp:
            spec = {"channel": name, "base": base, "merge": merges, "time": int(now.timestamp())}
            result = build_source(spec, Path(tmp) / "src", checkout=False)
        stamp = now.strftime("%Y%m%d-%H%M")
        short = result["head"][:9]
        version = f"{result['version']}-{name}.{now.strftime('%Y%m%d%H%M')}"
        spec = {
            "channel": name,
            "title": ch.get("title", name),
            "summary": ch.get("summary", ""),
            "web_note": ch.get("web_note", ""),
            "key": key,
            "time": int(now.timestamp()),
            "built": now.strftime("%Y-%m-%d %H:%M UTC"),
            "tag": f"{name}-{stamp}-{short}",
            "version": version,
            "head": result["head"],
            "base": base,
            "merge": result["merge"],
        }
        merged = [m["branch"] for m in result["merge"] if m["status"] == "merged"]
        skipped = [m["branch"] for m in result["merge"] if m["status"] != "merged"]
        print(f"{name}: build {spec['tag']} (key {key}); merged {merged}; skipped {skipped}")
        matrix.append({"channel": name, "spec": json.dumps(spec, separators=(",", ":"))})

    out = os.environ.get("GITHUB_OUTPUT")
    lines = [f"matrix={json.dumps(matrix)}", f"any={'true' if matrix else 'false'}"]
    if out:
        with open(out, "a") as f:
            f.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
