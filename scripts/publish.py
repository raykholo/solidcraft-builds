#!/usr/bin/env python3
"""Publish one channel build: a dated pre-release, the moving <channel>-latest release, and prune.

Usage: publish.py SPEC.json ASSET_DIR

ASSET_DIR holds the packages as the SolidCraft packaging scripts name them
(solidcraft-<version>-linux-x86_64.AppImage, ...). They are renamed without the version so the
same names work in every release, and so <channel>-latest has fixed download links.
Needs gh with GH_TOKEN and GH_REPO.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

KEEP = 10

# (file name, platform, how to run) in the order the notes list them.
DOWNLOADS = [
    ("solidcraft-linux-x86_64.AppImage", "Linux x86_64",
     "`chmod +x solidcraft-linux-x86_64.AppImage` and run it. Needs glibc 2.35 or newer."),
    ("solidcraft-linux-x86_64.tar.gz", "Linux x86_64",
     "Extract it and run `bin/solidcraft` in the folder it makes."),
    ("solidcraft-windows-x64-portable.zip", "Windows x64",
     "Extract it and run `solidcraft.exe`. Unsigned: in the SmartScreen box choose More info, then Run anyway."),
    ("SolidCraft-windows-x64.exe", "Windows x64",
     "The app as a single file. Unsigned: in the SmartScreen box choose More info, then Run anyway."),
    ("solidcraft-macos-aarch64.dmg", "macOS, Apple silicon",
     "Open it and drag SolidCraft somewhere (dragging it into Applications replaces an installed SolidCraft). "
     "It is not notarized: the first time, right-click the app and choose Open, or run "
     "`xattr -dr com.apple.quarantine SolidCraft.app`."),
    ("solidcraft-cli-macos-aarch64.zip", "macOS, Apple silicon",
     "The command-line tool `solidcraft-cli`. Not notarized: `xattr -d com.apple.quarantine solidcraft-cli` before running it."),
    ("solidcraft-web.zip", "Browser",
     "The browser version as a static site. Serve the folder over HTTPS or from localhost, or use the link above."),
]


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(["gh", *args], text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {p.stderr.strip()}")
    return p


def short(sha: str) -> str:
    return sha[:9]


def commit_link(repo: str, sha: str) -> str:
    return f"[`{short(sha)}`](https://github.com/{repo}/commit/{sha})"


def pages_url() -> str:
    repo = os.environ["GH_REPO"]
    owner, name = repo.split("/", 1)
    return f"https://{owner.lower()}.github.io/{name}/"


def notes(spec: dict, files: list[str], tag: str) -> str:
    repo = os.environ["GH_REPO"]
    ch = spec["channel"]
    base = spec["base"]
    web = f"{pages_url()}{ch}/"
    out = [
        f"Preview build of the **{ch}** channel: {spec['title']}. {spec.get('summary', '')}".rstrip(),
        "",
        "This is an unofficial build of work-in-progress branches, not a SolidCraft release. "
        "Designs saved with it may need a newer SolidCraft to open.",
        "",
        f"Built {spec['built']}, version `{spec['version']}`, source commit `{short(spec['head'])}`.",
        "",
        "### Inputs",
        "",
        f"- Base: `{base['repo']}` `{base['branch']}` at {commit_link(base['repo'], base['sha'])}",
    ]
    merged = [m for m in spec["merge"] if m.get("status") == "merged"]
    skipped = [m for m in spec["merge"] if m.get("status") != "merged"]

    def describe(m: dict) -> str:
        pr = ""
        if m.get("pr"):
            title = f" {m['title']}" if m.get("title") else ""
            pr = f"[#{m['pr']}]({m.get('url') or 'https://github.com/' + m['pr_repo'] + '/pull/' + str(m['pr'])}){title}: "
        sha = commit_link(m["repo"], m["sha"]) if m.get("sha") else "(no commit)"
        return f"{pr}`{m['repo']}` `{m['branch']}` at {sha}"

    if merged:
        out += ["", "Merged, in this order:", ""]
        out += [f"- {describe(m)}" + (f" ({m['note']})" if m.get("note") else "") for m in merged]
    if skipped:
        out += ["", "Skipped (left out of this build):", ""]
        out += [f"- {describe(m)}: {m.get('reason', m.get('status'))}" for m in skipped]

    if spec.get("failed"):
        out += ["", "**Not in this build** (the build failed; see the "
                f"[run log]({spec.get('run_url', '')})): " + ", ".join(spec["failed"]) + "."]

    out += ["", "### Downloads", ""]
    if "solidcraft-web.zip" not in files:
        pass
    elif spec.get("web_note"):
        out += [f"Open in the browser: {web} ({spec['web_note']})", ""]
    else:
        out += [f"Open in the browser: {web}", ""]
    out += ["| File | For | How to run |", "| --- | --- | --- |"]
    for name, platform, how in DOWNLOADS:
        if name in files:
            link = f"https://github.com/{repo}/releases/download/{tag}/{name}"
            out.append(f"| [{name}]({link}) | {platform} | {how} |")
    out += [
        "",
        "Every build here is unsigned. Preview builds share settings with an installed SolidCraft, "
        "and the app's own update check points at official SolidCraft releases.",
        "",
        f"Latest build of this channel: https://github.com/{repo}/releases/tag/{ch}-latest. "
        f"All channels: {pages_url()}",
        "",
        f"<!-- build-key: {spec['key']} -->",
    ]
    return "\n".join(out) + "\n"


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text())
    assets = Path(sys.argv[2])
    version = spec["version"]
    ch = spec["channel"]
    tag = spec["tag"]
    labels = {"linux": "Linux", "windows": "Windows", "macos": "macOS", "web": "Browser"}
    needs = json.loads(os.environ.get("NEEDS") or "{}")
    spec["failed"] = [labels.get(k, k) for k, v in needs.items() if v.get("result") != "success"]
    if os.environ.get("GITHUB_RUN_ID"):
        spec["run_url"] = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                           f"{os.environ['GH_REPO']}/actions/runs/{os.environ['GITHUB_RUN_ID']}")
    latest = f"{ch}-latest"

    for f in sorted(assets.iterdir()):
        new = f.name.replace(f"-{version}", "")
        if new != f.name:
            f.rename(assets / new)
    files = sorted(p.name for p in assets.iterdir() if p.is_file())
    if not files:
        raise RuntimeError("no assets")

    sums = []
    for name in files:
        sums.append(f"{hashlib.sha256((assets / name).read_bytes()).hexdigest()}  {name}")
    (assets / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")
    info = dict(spec)
    info["assets"] = files
    (assets / "build-info.json").write_text(json.dumps(info, indent=2) + "\n")
    upload = [str(assets / n) for n in files + ["SHA256SUMS.txt", "build-info.json"]]

    work = Path(os.environ.get("RUNNER_TEMP", "."))
    dated_notes = work / "notes-dated.md"
    dated_notes.write_text(notes(spec, files, tag))
    latest_notes = work / "notes-latest.md"
    latest_notes.write_text(notes(spec, files, latest))

    # Tags point at this repository's main branch head: GITHUB_TOKEN may not tag an older commit
    # that changed a workflow file.
    title = f"{spec['title']} preview {spec['built']}"
    gh("release", "create", tag, "--prerelease", "--latest=false", "--target", "main",
       "--title", title, "--notes-file", str(dated_notes), *upload)
    print(f"published {tag}")

    if gh("release", "view", latest, "--json", "tagName", check=False).returncode == 0:
        gh("release", "upload", latest, "--clobber", *upload)
        names = set(files + ["SHA256SUMS.txt", "build-info.json"])
        old = gh("release", "view", latest, "--json", "assets", "--jq", ".assets[].name").stdout.split()
        for name in old:
            if name not in names:
                gh("release", "delete-asset", latest, name, "--yes")
        gh("release", "edit", latest, "--prerelease", "--latest=false", "--title", f"{spec['title']}: latest preview",
           "--notes-file", str(latest_notes))
    else:
        gh("release", "create", latest, "--prerelease", "--latest=false", "--target", "main",
           "--title", f"{spec['title']}: latest preview", "--notes-file", str(latest_notes), *upload)
    print(f"updated {latest}")

    listing = json.loads(gh("release", "list", "--limit", "500", "--json", "tagName,createdAt").stdout)
    dated = sorted(
        (r for r in listing if re.match(rf"^{re.escape(ch)}-\d{{8}}-\d{{4}}-[0-9a-f]+$", r["tagName"])),
        key=lambda r: r["createdAt"], reverse=True,
    )
    for r in dated[KEEP:]:
        gh("release", "delete", r["tagName"], "--cleanup-tag", "--yes")
        print(f"pruned {r['tagName']}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(notes(spec, files, tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
