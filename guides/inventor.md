# Inventor-familiar options guide

## What this branch is

The inventor channel combines SolidCraft upstream `main` with five separate PR branches from `raykholo/solidcraft`.
It adds optional ribbon, sketch-ownership, browser-saving, and quick-access behavior for familiar CAD workflows.
It uses SolidCraft's own commands, names, and interface conventions.
Existing options already provide per-part history, sketches nested under features, a cube navigator, and part editing with other parts faded.
Assembly constraints are planned work, not part of this channel.

## What we did

1. Added an option to fold the ribbon to its tab row, off by default ([PR #10214](https://github.com/tangency-labs/solidcraft/pull/10214), branch `ribbon-tabs-only`, issue #10112).
2. Added “Sketching on a part's face makes that part active,” off by default, and `sketch.create` parameter `activate_part: true` for scripts and MCP. The part stays active so later features land with the sketch; failure restores the previous active part ([PR #10216](https://github.com/tangency-labs/solidcraft/pull/10216), branch `sketch-face-owner`, issue #10215).
3. Added an explicit action to move existing face-attached sketches to the parts they are drawn on, with one Undo step and reasons for sketches left in place ([PR #10219](https://github.com/tangency-labs/solidcraft/pull/10219), branch `sketches-to-parts`, issue #10218).
4. Added an opt-in browser-saving option to keep unsaved designs in private browser storage and offer them on a later visit. The leave-page warning remains when unsaved changes are not all kept ([PR #10221](https://github.com/tangency-labs/solidcraft/pull/10221), branch `web-keep-unsaved`, issue #10220).
5. Added a quick-access bar after Save, Undo, and Redo, populated from ribbon buttons' right-click menus. It starts empty and hidden ([PR #10224](https://github.com/tangency-labs/solidcraft/pull/10224), branch `quick-access-bar`, issue #10223).

## Where the code is

There is no single inventor source branch. Each link targets the head of the PR branch named above.
Start with its guide documentation, then read the corresponding implementation.

| Area | Path(s) | What it does |
| --- | --- | --- |
| Ribbon docs and layout | [docs/book/src/guide/ui-tour.md](https://github.com/raykholo/solidcraft/blob/ribbon-tabs-only/docs/book/src/guide/ui-tour.md), [crates/ui-egui/src/toolbar.rs](https://github.com/raykholo/solidcraft/blob/ribbon-tabs-only/crates/ui-egui/src/toolbar.rs) | Describes and draws the optional tabs-only ribbon. |
| Face sketch docs and ownership | [docs/book/src/guide/sketching.md](https://github.com/raykholo/solidcraft/blob/sketch-face-owner/docs/book/src/guide/sketching.md), [crates/engine/src/cmd/sketch.rs](https://github.com/raykholo/solidcraft/blob/sketch-face-owner/crates/engine/src/cmd/sketch.rs), [crates/ui-egui/src/dialogs.rs](https://github.com/raykholo/solidcraft/blob/sketch-face-owner/crates/ui-egui/src/dialogs.rs) | Passes activate_part for face picks and creates the sketch in the picked part. |
| Move existing sketches | [docs/book/src/guide/assemblies.md](https://github.com/raykholo/solidcraft/blob/sketches-to-parts/docs/book/src/guide/assemblies.md), [crates/engine/src/cmd/component_sketches_to_parts.rs](https://github.com/raykholo/solidcraft/blob/sketches-to-parts/crates/engine/src/cmd/component_sketches_to_parts.rs) | Moves face-attached sketches to their parts while preserving placement; reports skipped sketches. |
| Unsaved browser work | [docs/book/src/guide/files.md](https://github.com/raykholo/solidcraft/blob/web-keep-unsaved/docs/book/src/guide/files.md), [apps/solidcraft-web/src/keep.rs](https://github.com/raykholo/solidcraft/blob/web-keep-unsaved/apps/solidcraft-web/src/keep.rs), [apps/solidcraft-web/src/files.rs](https://github.com/raykholo/solidcraft/blob/web-keep-unsaved/apps/solidcraft-web/src/files.rs) | Stores and offers unsaved copies, with leave-page warning decisions. |
| Option defaults | [crates/ui-egui/src/prefs.rs](https://github.com/raykholo/solidcraft/blob/web-keep-unsaved/crates/ui-egui/src/prefs.rs) | Declares the browser-saving preference and its default. |
| Quick-access docs and pins | [docs/book/src/guide/ui-tour.md](https://github.com/raykholo/solidcraft/blob/quick-access-bar/docs/book/src/guide/ui-tour.md), [crates/ui-egui/src/toolbar_custom.rs](https://github.com/raykholo/solidcraft/blob/quick-access-bar/crates/ui-egui/src/toolbar_custom.rs), [crates/ui-egui/src/toolbar.rs](https://github.com/raykholo/solidcraft/blob/quick-access-bar/crates/ui-egui/src/toolbar.rs) | Persists pinned command IDs and draws the optional bar. |

## Spec

This channel follows SolidCraft's conventions: options rather than changed defaults, its own names, and one PR per issue.
The [assembly-constraints proposal on issue #6061](https://github.com/tangency-labs/solidcraft/issues/6061) is future work.

### Within the spec

- Options preserve defaults: ribbon folding, face-part activation, and browser saving are opt-in; quick access starts empty and hidden.
- Explicit sketch cleanup: moving sketches is a requested action, so existing designs are not reorganized automatically.
- Own names and commands: the changes extend SolidCraft workflows without a copied product interface or shortcut set.
- One PR per issue: #10214/#10112, #10216/#10215, #10219/#10218, #10221/#10220, and #10224/#10223 keep each change independently reviewable.

### Beyond the spec (additions)

- Scriptable face ownership: `activate_part` exposes the same optional behavior to scripts and MCP, with the activated component and placement returned.
- Placement-preserving cleanup: moving an attached sketch reauthors its face attachment rather than merely relabeling its owner.
- Browser recovery: an optional saving policy offers unsaved copies in SolidCraft's own window instead of relying only on the browser's leave-page box.

### Not done yet / outside

- Assembly constraints: the #6061 proposal recommends tagged joint relations and the existing loop solver, not a shipped independent constraint system.
- Constraint UI and analysis: mate, flush, axis, insert, redundancy reporting, and visible degrees of freedom are proposed stages, pending design agreement.
- Other familiar-workflow gaps: browser search, small ribbon-button stacks, and further view-cube work are separate efforts, not these five PRs.
- Bundled product shortcut sets or copied artwork: SolidCraft's conventions call for neutral names and original assets; personal bindings belong in user profiles.

The #6061 design reuses persistent joint origins, expressions, conflict detection, and the joint graph.
It proposes starting loop-closing joints at current placements, then adding relation kinds, commands, redundancy reporting, a Constrain dialog, browser entries, and a degrees-of-freedom display.
Its proposed UI begins behind an off-by-default option. None of those stages is claimed by this channel.

## How to try it

Use the [latest desktop release](https://github.com/raykholo/solidcraft-builds/releases/tag/inventor-latest) or the [browser build](https://raykholo.github.io/solidcraft-builds/inventor/).
Check the release's Inputs list: a branch that fails to merge can be skipped.
Enable the face-part option in Preferences > Sketch, try browser saving in Preferences > General > Saving, or pin a ribbon command to the application bar from its right-click menu.

For source work, use upstream main plus the five PR branches listed above to reproduce the channel, or use one branch to investigate a change independently.
The [build guide](https://github.com/raykholo/solidcraft/blob/ribbon-tabs-only/docs/building.md) gives these commands from a source checkout:

```sh
cargo run --release -p solidcraft -- --sample
cargo run --release -p solidcraft-cli -- commands
```

For the browser, with Trunk installed:

```sh
cd apps/solidcraft-web
trunk build --release --public-url ./
```

## For AI assistants

```prompt
Investigate the inventor preview channel: tangency-labs/solidcraft main plus raykholo/solidcraft branches ribbon-tabs-only (PR #10214), sketch-face-owner (#10216), sketches-to-parts (#10219), web-keep-unsaved (#10221), and quick-access-bar (#10224).
Start with each branch's docs/book/src/guide documentation: ui-tour.md, sketching.md, assemblies.md, and files.md. Then follow the code map at https://raykholo.github.io/solidcraft-builds/inventor/guide/.
Compare each PR branch against upstream main and distinguish existing upstream options from additions. Check the preview release's actual merged inputs before attributing behavior to a build.
Verify option defaults remain unchanged, quick access starts empty, sketch activation persists after success and restores on failure, moved sketches keep their placement, and browser recovery retains warnings when changes are not safely kept.
Check SolidCraft's own names and command conventions and one PR per issue. Treat issue #6061's tagged-joint assembly-constraints proposal as future work. Compare it with the existing joint relation solver; do not describe proposed commands or UI as implemented.
Cite paths and PRs, and separate confirmed behavior from gaps and proposals.
```

## Status and caveats

PR #10216 is merged into SolidCraft main (2026-10-31), so the channel gets it from main. PRs #10214, #10219, #10221, and #10224 are open drafts.
These are unofficial preview builds, not SolidCraft releases.
The channel's merge inputs can change, and skipped branches are listed in release notes.

Existing per-part history and sketch nesting are options, not new features of these PRs. A sketch made with the design active still belongs to the design unless face-part activation is enabled or the explicit move action is used.
Sketch cleanup leaves unsupported attachments in place and reports why. Local browser copies are not an external backup.
Assembly constraints, a unified component Properties window, and design templates remain outside these five changes.
