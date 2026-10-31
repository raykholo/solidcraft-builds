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
import re
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
    if cfg.get("guide"):
        parts.append(f'<p><a href="./{esc(name)}/guide/">What&#39;s in this branch, and where the code is</a></p>')
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
    if info.get("failed"):
        parts.append(f'<p class="note">Not in this build (it failed to build): {esc(", ".join(info["failed"]))}. '
                     f'<a href="{esc(info.get("run_url", rel))}">Run log</a>.</p>')
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
.guide h2 {{ margin-top: 28px; }}
.guide h3 {{ margin-top: 18px; }}
pre {{ overflow-x: auto; padding: 14px; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }}
pre code {{ overflow-wrap: normal; }}
.table-scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ text-align: left; vertical-align: top; padding: 8px; border: 1px solid var(--line); }}
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


def inline_markdown(source: str) -> str:
    """Render the inline subset used by the guides, escaping ordinary text."""
    pattern = r"`([^`]+)`|\[([^\]]+)\]\(([^\s)]+)\)"
    parts = []
    end = 0
    for match in re.finditer(pattern, source):
        parts.append(esc(source[end:match.start()]))
        if match[1] is not None:
            parts.append(f"<code>{esc(match[1])}</code>")
        else:
            parts.append(f'<a href="{esc(match[3])}">{esc(match[2])}</a>')
        end = match.end()
    parts.append(esc(source[end:]))
    return "".join(parts)


def minimal_markdown(source: str) -> str:
    """Headings, paragraphs, flat lists, pipe tables, links, and fenced code."""
    lines = source.splitlines()
    parts = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            language = line[3:].strip()
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            if i == len(lines):
                raise ValueError("Unclosed Markdown code fence")
            parts.append(f'<pre><code class="language-{esc(language)}">{esc(chr(10).join(code) + chr(10))}</code></pre>')
            i += 1
            continue
        heading = re.match(r"^(#{1,6}) (.+)$", line)
        if heading:
            level = len(heading[1])
            parts.append(f"<h{level}>{inline_markdown(heading[2])}</h{level}>")
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.fullmatch(r"[| :\-]+", lines[i + 1]):
            cells = lambda row: [inline_markdown(c.strip()) for c in row.strip().strip("|").split("|")]
            parts.append('<div class="table-scroll"><table><thead><tr>' + "".join(f"<th>{c}</th>" for c in cells(line)) + "</tr></thead><tbody>")
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                parts.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells(lines[i])) + "</tr>")
                i += 1
            parts.append("</tbody></table></div>")
            continue
        item = re.match(r"^(- |[0-9]+\. )(.+)$", line)
        if item:
            tag = "ul" if item[1] == "- " else "ol"
            parts.append(f"<{tag}>")
            while i < len(lines):
                item = re.match(r"^(- |[0-9]+\. )(.+)$", lines[i])
                if not item or (item[1] == "- ") != (tag == "ul"):
                    break
                parts.append(f"<li>{inline_markdown(item[2])}</li>")
                i += 1
            parts.append(f"</{tag}>")
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|```|\||- |[0-9]+\. )", lines[i]):
            paragraph.append(lines[i])
            i += 1
        parts.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
    return "\n".join(parts)


def render_markdown(source: str) -> str:
    try:
        import markdown
    except ImportError:
        return minimal_markdown(source)
    return markdown.markdown(source, extensions=["tables", "fenced_code"])


COPY_SCRIPT = """<script>
document.querySelectorAll('[data-copy-prompt]').forEach(button => {
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(button.nextElementSibling.querySelector('code').textContent);
      button.textContent = 'Copied';
    } catch {
      button.textContent = 'Select the prompt and copy';
    }
  });
});
</script>"""


def guide_page(name: str, cfg: dict, repo: str, updated: str) -> str:
    body = render_markdown((ROOT / cfg["guide"]).read_text())
    body = body.replace('<pre><code class="language-prompt">',
                        '<button class="button" type="button" data-copy-prompt aria-live="polite" aria-label="Copy assistant prompt">Copy</button>\n<pre><code class="language-prompt">')
    section = '<p><a href="../../">All preview builds</a></p><article class="card guide">' + body + '</article>'
    page = PAGE.format(sections=section, updated=updated, repo=esc(repo))
    page = page.replace('<title>SolidCraft preview builds</title>', f'<title>{esc(cfg.get("title", name))} guide | SolidCraft preview builds</title>')
    return page.replace('</body>', COPY_SCRIPT + '\n</body>')


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
    for name, cfg in config.items():
        if cfg.get("guide"):
            target = out / name / "guide"
            target.mkdir(parents=True, exist_ok=True)
            (target / "index.html").write_text(guide_page(name, cfg, repo, updated))
    (out / "index.html").write_text(PAGE.format(sections="\n".join(sections), updated=updated, repo=esc(repo)))
    (out / ".nojekyll").write_text("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
