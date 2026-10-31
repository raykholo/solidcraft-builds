# Plugins guide

## What this branch is

The plugins channel builds `raykholo/solidcraft` at `plugins-dutchman`.
It adds a desktop WebAssembly component host for one-shot commands and file importers.
It builds on [crono2250's community runtime PR #8987](https://github.com/tangency-labs/solidcraft/pull/8987).
The branch extends that runtime with installation, approval, ribbon commands, native dialogs, and import reports.
The browser build has no plugin execution host.

## What we did

1. Integrated explicit command execution with content approval, resource limits, rollback on failure, and one Undo step on success ([runtime integration](https://github.com/raykholo/solidcraft/commit/734aff509)).
2. Added importer packages, installation, and Allow/Revoke in Preferences, then connected File > Import, Open, and dropped files to approved importers ([importers](https://github.com/raykholo/solidcraft/commit/5c036dea8), [file routing](https://github.com/raykholo/solidcraft/commit/247e1af64)).
3. Added Dutchman Convert for Fusion, Inventor, SolidWorks, and FreeCAD files, with a larger declared component allowance ([example](https://github.com/raykholo/solidcraft/commit/4aea79ff4)). Unchecked mapped history stays hidden beside the original geometry ([hidden history](https://github.com/raykholo/solidcraft/commit/e56c36371)).
4. Added contributed commands, ribbon placement, host-drawn parameter dialogs, SVG icons, progress, Cancel, import reports, and compiled importer caching ([contributions](https://github.com/raykholo/solidcraft/commit/ad95ad35d)).
5. Made host limits readable as Normal, Large, or Largest, with exact values under Advanced ([limit choices](https://github.com/raykholo/solidcraft/commit/8ee8314ee)).

## Where the code is

Read the two branch docs first, then follow this map. Links track the branch head.

| Area | Path(s) | What it does |
| --- | --- | --- |
| Start here | [docs/plugin-runtime.md](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/docs/plugin-runtime.md), [docs/plugin-architecture-notes.md](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/docs/plugin-architecture-notes.md) | Runtime contract, feature rationale, and remaining gaps. |
| Contract | [wit/solidcraft-plugin.wit](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/wit/solidcraft-plugin.wit) | Command and importer component worlds. |
| Host and sandbox | [crates/engine/src/plugin.rs](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/crates/engine/src/plugin.rs), [crates/engine/src/plugin/runtime.rs](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/crates/engine/src/plugin/runtime.rs) | Inspection, content approval, budgets, scratch transactions, importer execution, and caching. |
| Command contributions | [crates/engine/src/plugin/contrib.rs](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/crates/engine/src/plugin/contrib.rs) | Manifest validation and contributed command registration. |
| File routing | [crates/engine/src/cmd/file.rs](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/crates/engine/src/cmd/file.rs) | Routes imports through the approved importer and adopts the result. |
| Preferences | [crates/ui-egui/src/plugins.rs](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/crates/ui-egui/src/plugins.rs) | Install, allow, revoke, disable, and remove packages; synchronize commands. |
| Dialogs and reports | [crates/ui-egui/src/dialogs_plugin.rs](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/crates/ui-egui/src/dialogs_plugin.rs), [crates/ui-egui/src/plugin_report.rs](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/crates/ui-egui/src/plugin_report.rs) | Host-drawn parameter fields and import reports. |
| Icons | [crates/ui-egui/src/icon_svg.rs](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/crates/ui-egui/src/icon_svg.rs) | Parses plugin SVGs with the built-in whitelist. |
| Examples | [examples/plugins/example-box/README.md](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/examples/plugins/example-box/README.md), [examples/plugins/dutchman-convert/README.md](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/examples/plugins/dutchman-convert/README.md) | Build and try a command component or a CAD importer. |

## Spec

Compared with [issue #1221](https://github.com/tangency-labs/solidcraft/issues/1221), the design remains experimental.

### Within the spec

- Sandboxed desktop components: Wasmtime meters guest work, memory, and deadlines; command plugins get no WASI, and importers get an empty, deterministic WASI environment.
- Explicit grants and approval: the manifest names exact allowed commands, and approval binds to package content; no guest filesystem, network, or process access is granted.
- Existing engine commands: command plugins use the engine command path on a scratch session, so accepted edits are journaled and grouped into one Undo step.
- Failure isolation: traps, refused calls, invalid output, and exhausted budgets discard the transaction; stale desktop results are rejected.
- Language-neutral interface: published WIT accepts compatible components; the supplied examples use Rust.
- First-milestone pieces: Preferences lists and controls packages, and a box example and runtime guide explain authoring and execution.

### Beyond the spec (additions)

- Importer result contract: a component returns a validated design container or STEP, preserving mapped editable history when available without engine grants.
- Native command surfaces: declarations add ribbon buttons, shortcuts, parameter dialogs, and sanitized SVG icons through the existing command registry.
- Import workflow: progress, Cancel, reports, and importing geometry into the current design make importers usable alongside built-in formats.
- Compiled importer caches: memory and disk caches avoid repeated compilation; Allow prepares importers in the background.
- User ceilings: Normal, Large, Largest, and CLI limit files let users bound trusted packages without rebuilding the app.

### Not done yet / outside

- Stable API v1: the implemented API is `solidcraft:plugin@0.1.0`, with no stable compatibility promise; metadata comes from static `plugin.json`, not `manifest()`.
- Arbitrary capabilities: file grants, networking, persistent storage, and unrestricted engine commands are unavailable; the guest surface is deliberately narrow.
- Browser execution and language examples beyond Rust: a browser host and those examples are not supplied.
- Parametric plugin features and arbitrary custom panels: execution emits native results rather than replaying plugin code on rebuild; UI comes from host-owned declarations.
- Curated or signed distribution: a content hash identifies reviewed bytes but does not authenticate a publisher.
- Full native-work interruption: guest budgets do not bound component compilation or forcibly interrupt a running native kernel call.

## How to try it

Use the [latest desktop release](https://github.com/raykholo/solidcraft-builds/releases/tag/plugins-latest).
The [browser build](https://raykholo.github.io/solidcraft-builds/plugins/) runs SolidCraft without plugins.

In Preferences > Plugins, install a package by selecting its `plugin.json`, review its grants and limits, and click Allow.
Dutchman Convert needs about 1 GB and 30 seconds per import; select Large if you trust it.
Then use Insert > Dutchman > Import CAD design. Choose a new design for mapped history; importing into the current design brings geometry only.

From a source checkout of `plugins-dutchman`, the [build guide](https://github.com/raykholo/solidcraft/blob/plugins-dutchman/docs/building.md) runs the desktop app with:

```sh
cargo run --release -p solidcraft -- --sample
```

Build the box example from its directory, with the Rust `wasm32-unknown-unknown` target and `wasm-tools` installed:

```sh
cargo build --release --target wasm32-unknown-unknown
wasm-tools component new target/wasm32-unknown-unknown/release/solidcraft_example_box.wasm -o plugin.wasm
```

Keep `plugin.wasm` beside `plugin.json`. The example README explains inspecting it, reviewing the returned approval, and running entry `make` with dimensions 20, 10, and 3. The expected volume is 600 mm³; Undo removes the result.
For Dutchman Convert, install Rust's `wasm32-wasip2` target and run these commands from its example directory:

```sh
cargo build --release --target wasm32-wasip2
cp target/wasm32-wasip2/release/solidcraft_dutchman_convert.wasm plugin.wasm
```

## For AI assistants

```prompt
Investigate raykholo/solidcraft branch plugins-dutchman, the desktop command and importer plugin preview. It builds on crono2250's upstream PR #8987 and follows issue #1221.
Read docs/plugin-runtime.md and docs/plugin-architecture-notes.md first, then the code map at https://raykholo.github.io/solidcraft-builds/plugins/guide/.
Compare the branch against tangency-labs/solidcraft main. Separate inherited runtime work from branch additions, and cite paths and commits for findings.
Check exact-content approval, command grants, sandbox imports, scratch-session rollback, Undo, stale-result rejection, fuel, memory, deadlines, and native compilation/kernel work outside guest budgets. Distinguish command plugins from importers and host ceilings from package requests.
Check importer output validation, cache trust, and hidden unverified history. Resolve older runtime statements against the later importer and contributions sections and the code. Do not assume API 0.x is stable or that browser builds execute plugins.
```

## Status and caveats

The upstream architecture decision for [PR #8987](https://github.com/tangency-labs/solidcraft/pull/8987) remains pending. The branch additions do not imply upstream acceptance.
These are unofficial preview builds, not SolidCraft releases.

The runtime reference retains older statements about no persistent approvals or icons; its later installation and contributions sections describe the branch additions. Read those with the architecture notes and code.

- First compilation can be slow. Cancel cannot interrupt native compilation, and the disk cache trusts the user's data folder beyond Wasmtime's object checks.
- Dutchman's mapped Fusion history is unverified and hidden; original geometry stays visible. Fillets and chamfers are omitted, and some threads stop history mapping.
- `.iam` and `.sldasm` assemblies are not claimed because their external part files need a consent-based host API. Self-contained `.f3z` assemblies can convert.
- Dialogs have no live preview or conditional rows. Manifest labels have no translation catalog, and plugin tabs have no user-chosen position.
- Progress reports stage starts rather than detailed decoder progress. Replacing a package requires a new Allow, without a display of what changed.
