#!/usr/bin/env python3
"""Assemble the GitHub Pages site: each channel's browser build at /<channel>/ and an index page.

Usage: site.py OUT_DIR

Reads each channel's <channel>-latest release (build-info.json and solidcraft-web.zip), so a run
that rebuilt one channel still publishes the others as they are. Needs gh with GH_TOKEN, GH_REPO.
"""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = [
    ("solidcraft-windows-x64-portable.zip", "Windows x64 (zip)"),
    ("SolidCraft-windows-x64.exe", "Windows x64 (exe)"),
    ("solidcraft-macos-aarch64.dmg", "macOS Apple silicon (dmg)"),
    ("solidcraft-linux-x86_64.AppImage", "Linux x86_64 (AppImage)"),
    ("solidcraft-linux-x86_64.tar.gz", "Linux x86_64 (tar.gz)"),
]


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], text=True, capture_output=True)


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def channel_section(name: str, cfg: dict, info: dict | None, has_web: bool, repo: str) -> str:
    rel = f"https://github.com/{repo}/releases"
    title = esc(cfg.get("title", name))
    parts = [f'<section class="card" id="{esc(name)}">',
             f'<h2>{title} <span class="tag">{esc(name)}</span></h2>',
             f'<p class="summary">{esc(cfg.get("summary", ""))}</p>']
    if not info:
        parts.append("<p>No build yet.</p></section>")
        return "\n".join(parts)
    latest = f"{rel}/download/{name}-latest"
    parts.append('<div class="actions">')
    if has_web:
        parts.append(f'<a class="button primary" href="./{esc(name)}/">Open in browser</a>')
    for file, label in PLATFORMS:
        if file in info.get("assets", []):
            parts.append(f'<a class="button" href="{latest}/{esc(file)}">{esc(label)}</a>')
    parts.append("</div>")
    if cfg.get("web_note"):
        parts.append(f'<p class="note">{esc(cfg["web_note"])}</p>')
    base = info["base"]
    parts.append(f'<p class="meta">Built {esc(info["built"])} &middot; version <code>{esc(info["version"])}</code> &middot; '
                 f'<a href="{rel}/tag/{esc(info["tag"])}">release notes and how to run</a> &middot; '
                 f'<a href="{rel}?q={esc(name)}-&amp;expanded=true">all {esc(name)} builds</a></p>')
    parts.append("<h3>Inputs</h3><ul class=\"inputs\">")
    parts.append(f'<li>Base <code>{esc(base["repo"])}</code> <code>{esc(base["branch"])}</code> at '
                 f'<a href="https://github.com/{esc(base["repo"])}/commit/{esc(base["sha"])}"><code>{esc(base["sha"][:9])}</code></a></li>')
    for m in info.get("merge", []):
        pr = ""
        if m.get("pr"):
            url = m.get("url") or f"https://github.com/{m.get('pr_repo', '')}/pull/{m['pr']}"
            pr = f'<a href="{esc(url)}">#{esc(m["pr"])}</a> {esc(m.get("title", ""))}: '
        sha = (f'<a href="https://github.com/{esc(m["repo"])}/commit/{esc(m["sha"])}"><code>{esc(m["sha"][:9])}</code></a>'
               if m.get("sha") else "(no commit)")
        if m.get("status") == "merged":
            state = '<span class="ok">merged</span>'
        else:
            state = f'<span class="skip">skipped: {esc(m.get("reason", m.get("status", "")))}</span>'
        parts.append(f'<li>{state} {pr}<code>{esc(m["branch"])}</code> at {sha}</li>')
    parts.append("</ul></section>")
    return "\n".join(parts)


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SolidCraft preview builds</title>
<style>
:root {{ --bg: #f6f7f9; --card: #ffffff; --text: #1d2330; --muted: #5d6677; --line: #dde1e8;
  --accent: #2a62d4; --accent-text: #ffffff; --ok: #1e7b3c; --skip: #a3561a; color-scheme: light dark; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #14171c; --card: #1d2128; --text: #e4e7ec; --muted: #9aa3b2;
  --line: #2e343e; --accent: #5b8dff; --accent-text: #0b0f17; --ok: #5cc581; --skip: #e3a064; }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--text); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 900px; margin: 0 auto; padding: 24px 16px 48px; }}
h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
.lede {{ color: var(--muted); margin: 0 0 24px; }}
.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px; margin: 0 0 18px; }}
h2 {{ margin: 0 0 4px; font-size: 1.25rem; }}
h3 {{ font-size: .95rem; margin: 14px 0 4px; }}
.tag {{ font: 12px ui-monospace, monospace; color: var(--muted); border: 1px solid var(--line); border-radius: 4px; padding: 1px 6px; vertical-align: middle; }}
.summary, .meta, .note {{ color: var(--muted); margin: 6px 0; }}
.note {{ color: var(--skip); }}
.actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
.button {{ display: inline-block; padding: 7px 12px; border: 1px solid var(--line); border-radius: 6px; color: var(--text); text-decoration: none; }}
.button:hover {{ border-color: var(--accent); }}
.button.primary {{ background: var(--accent); border-color: var(--accent); color: var(--accent-text); font-weight: 600; }}
a {{ color: var(--accent); }}
code {{ font: 13px ui-monospace, monospace; overflow-wrap: anywhere; }}
.inputs {{ padding-left: 18px; margin: 0; }}
.inputs li {{ margin: 3px 0; }}
.ok {{ color: var(--ok); font-weight: 600; }}
.skip {{ color: var(--skip); font-weight: 600; }}
footer {{ color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<main>
<h1>SolidCraft preview builds</h1>
<p class="lede">Unofficial builds of work-in-progress SolidCraft branches, rebuilt when they change.
These are not SolidCraft releases. The official app is at
<a href="https://github.com/tangency-labs/solidcraft">tangency-labs/solidcraft</a>.</p>
{sections}
<footer>Page updated {updated}. <a href="https://github.com/{repo}">Source and channel list</a>.
Desktop builds are unsigned; each release's notes say how to open them.</footer>
</main>
</body>
</html>
"""


def main() -> int:
    out = Path(sys.argv[1])
    repo = os.environ["GH_REPO"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    config = tomllib.loads((ROOT / "channels.toml").read_text())["channels"]
    sections = []
    for name, cfg in config.items():
        info = None
        has_web = False
        with tempfile.TemporaryDirectory() as tmp:
            got = gh("release", "download", f"{name}-latest", "--dir", tmp,
                     "--pattern", "build-info.json", "--pattern", "solidcraft-web.zip")
            if got.returncode == 0 and (Path(tmp) / "build-info.json").exists():
                info = json.loads((Path(tmp) / "build-info.json").read_text())
            web = Path(tmp) / "solidcraft-web.zip"
            if web.exists():
                with zipfile.ZipFile(web) as z:
                    z.extractall(Path(tmp) / "web")
                inner = [p for p in (Path(tmp) / "web").iterdir() if p.is_dir()]
                src = inner[0] if len(inner) == 1 else Path(tmp) / "web"
                if (src / "index.html").exists():
                    shutil.copytree(src, out / name)
                    has_web = True
        print(f"{name}: info={'yes' if info else 'no'} web={'yes' if has_web else 'no'}")
        sections.append(channel_section(name, cfg, info, has_web, repo))
    from datetime import datetime, timezone
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (out / "index.html").write_text(PAGE.format(sections="\n".join(sections), updated=updated, repo=esc(repo)))
    (out / ".nojekyll").write_text("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
