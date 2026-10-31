# SolidCraft preview builds

Unofficial preview builds of work-in-progress [SolidCraft](https://github.com/tangency-labs/solidcraft)
branches. **These are not SolidCraft releases.** For the official app, use the
[SolidCraft releases](https://github.com/tangency-labs/solidcraft/releases).

**Index page:** https://raykholo.github.io/solidcraft-builds/

| Channel | What it is | Browser | Latest desktop build |
| --- | --- | --- | --- |
| `inventor` | SolidCraft `main` with the open pull requests for options that make the app feel familiar to Inventor users | [open](https://raykholo.github.io/solidcraft-builds/inventor/) | [inventor-latest](https://github.com/raykholo/solidcraft-builds/releases/tag/inventor-latest) |
| `plugins` | The `plugins-dutchman` branch: SolidCraft with a plugin host | [open](https://raykholo.github.io/solidcraft-builds/plugins/) (without plugins) | [plugins-latest](https://github.com/raykholo/solidcraft-builds/releases/tag/plugins-latest) |

The browser version of `plugins` is SolidCraft without plugins: the plugin host runs only in the
desktop builds.

## Investigating the branches

Read the [Plugins guide](https://raykholo.github.io/solidcraft-builds/plugins/guide/) or the
[Inventor-familiar options guide](https://raykholo.github.io/solidcraft-builds/inventor/guide/)
for changes, specs, code maps, source-build commands, and prompts for your assistant.
The Markdown sources are [plugins.md](guides/plugins.md) and [inventor.md](guides/inventor.md).

## Downloads

Each channel's `<channel>-latest` release always holds its newest build, under fixed names:

- Windows x64: `solidcraft-windows-x64-portable.zip` (extract, run `solidcraft.exe`) or
  `SolidCraft-windows-x64.exe` (the app as one file)
- macOS, Apple silicon: `solidcraft-macos-aarch64.dmg`
- Linux x86_64: `solidcraft-linux-x86_64.AppImage` or `solidcraft-linux-x86_64.tar.gz`
- Browser: `solidcraft-web.zip` (the static site behind the browser link)

For example, `https://github.com/raykholo/solidcraft-builds/releases/download/inventor-latest/solidcraft-linux-x86_64.AppImage`.

Every build is also kept as a dated pre-release, `<channel>-<yyyymmdd-hhmm>-<commit>`, whose notes
list exactly what went in. The last 10 per channel are kept.

Good to know:

- Nothing is signed. Windows SmartScreen: More info, then Run anyway. macOS: right-click the app
  and choose Open the first time, or `xattr -dr com.apple.quarantine SolidCraft.app`.
- The macOS app has the same name as an installed SolidCraft; dragging it into Applications
  replaces it. Keep it somewhere else to have both.
- Preview builds share settings with an installed SolidCraft. Designs saved with a preview build
  may need a newer SolidCraft to open.
- The app's own update check points at official SolidCraft releases.

## How it works

[`channels.toml`](channels.toml) lists the channels. Each starts from a base branch and merges the
listed branches into it, in order. A branch that doesn't merge cleanly is left out and named in the
release notes; it never stops the build.

[`.github/workflows/build.yml`](.github/workflows/build.yml) runs every half hour. A short first
job reads the head commit of every base and merged branch and builds a channel only when that set
changed since its last build. Builds use SolidCraft's own packaging scripts on GitHub's hosted
runners (Linux, Windows, macOS and the browser version in parallel), publish a release, and
refresh the Pages site.

Run it by hand:

```
gh workflow run build.yml -R raykholo/solidcraft-builds                           # check every channel
gh workflow run build.yml -R raykholo/solidcraft-builds -f channel=inventor -f force=true
gh workflow run build.yml -R raykholo/solidcraft-builds -f pages=true             # only refresh the site
```

To add a branch to a channel, add an entry to its `merge` list in `channels.toml`.

## Licence

SolidCraft is licensed under the MIT License or the Apache License, Version 2.0, at your option,
and so are the builds and the files in this repository ([LICENSE-MIT](LICENSE-MIT),
[LICENSE-APACHE](LICENSE-APACHE)). Each build carries SolidCraft's licence files and its
third-party licences.
