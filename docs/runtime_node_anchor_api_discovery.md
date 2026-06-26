# Runtime Node Anchor API Discovery

Date: 2026-06-26

This is PR #8 read-only API discovery. It does not mutate `map_setting`, does not install a `map_setting` override, does not install asset overrides, and does not approve candidate edge `369-370` for mutation.

## Scope

The goal is to find an independent runtime node/world anchor surface that does not depend on pre-rendered background PNG labels. Acceptable surfaces would include public world/entity positions, camera or viewport bounds, world-to-screen transforms, debug drawing, or readable `map_setting.visible_view` / `map_setting.path` data with enough coordinate meaning to distinguish the eight possible `30x30` transforms.

## SDK Audit

Audit command:

```powershell
python .\tools\audit_runtime_node_anchor_api.py `
  --sdk-dir "D:\steam\steamapps\common\Teamfight Manager2\mod-sdk" `
  --include-adjacent-rift-source `
  --output "D:\tfm2_q2a_evidence\runtime_node_anchor_probe\runtime_node_anchor_api_audit.json"
```

Local evidence:

```text
D:\tfm2_q2a_evidence\runtime_node_anchor_probe\runtime_node_anchor_api_audit.json
  size: 7948 bytes
  SHA-256: 1035df9a8f6af3a89ce2e931d51fb66bc0b0c334c96e099e89882c7cdcfe9fba
```

Checked source files:

```text
mod-sdk/base_version.txt
mod-sdk/build_mod.bat
mod-sdk/build_mod_cargo.ps1
mod-sdk/rust-toolchain.toml
mod-sdk/template/Cargo.toml
mod-sdk/template/src/lib.rs
mod-sdk/toolchain_version.txt
TeamFightManger2-Map/rift_manager/src/lib.rs
```

Result:

```json
{
  "runtime_node_anchor_api": "unavailable_in_checked_public_sdk_sources",
  "map_setting_node_world_transform": "unproven",
  "candidate_369_370": "blocked"
}
```

| API surface | Public in checked source | Read-only usable | Anchor data type | Enough for anchor |
| --- | ---: | ---: | --- | ---: |
| `ModExtension::post_update` | yes | yes | callback | no |
| `Scene` | yes | yes | opaque runtime scene parameter | no |
| `GameUI` | yes | yes | opaque UI parameter | no |
| `Assets` | yes | yes | opaque assets parameter | no |
| `ServerModContext` | no | no | server context | no |
| `database.map_setting` | no | no | map setting data | no |
| `map_setting.visible_view` | no | no | rectangle/bounds | no |
| `map_setting.path` | no | no | grid/table | no |
| `camera / viewport` | no | no | view bounds | no |
| `world_to_screen / screen_to_world` | no | no | coordinate transform | no |
| `draw / text / debug overlay` | no | no | screen/world marker output | no |
| `logging` | no | no | diagnostic output | no |
| `tower / nexus / actor position` | no | no | known world entity position | no |

The public SDK template exposes an extension callback with opaque `Scene`, `GameUI`, and `Assets` parameters. The checked public source does not expose a callable draw API, text overlay API, world-to-screen transform, camera/viewport surface, entity-position surface, or readable `map_setting` node table.

## Read-Only Probe Mod

This PR adds an independent DLL-only package:

```text
mods/tfm2_lol_anchor_probe/
  mod.mod_info
  README.md

native/runtime_node_anchor_probe/
  Cargo.toml
  rust-toolchain.toml
  src/lib.rs
```

The package intentionally has no `mod.override_info`, no `map_setting` file, and no background/asset payloads. The committed DLL source writes one repository-external JSON/log pair the first time `post_update` runs:

```text
runtime_node_anchor.json
runtime_node_anchor.log
```

That runtime JSON can prove that the DLL loaded and `post_update` executed, but it still records:

```text
anchor_surface: post_update_only_no_public_anchor_fields
map_setting_node_world_transform: unproven
```

Local compile check:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "D:\steam\steamapps\common\Teamfight Manager2\mod-sdk\build_mod_cargo.ps1" `
  -Project "D:\steam\steamapps\common\Teamfight Manager2\TeamFight-map\native\runtime_node_anchor_probe"
```

The SDK template source shows `declare_mod(init)`, but the compile check confirmed the usable form is the macro `declare_mod!(init)`. The local build produced `runtime_node_anchor_probe.dll` with SHA-256 `33d826f22b13520bf10fa9d5bc691f475d1bde66f721a450176ac52d07875499`; this DLL is ignored and not committed.

## Installer Guardrails

The installer stages only the independent DLL probe:

```powershell
python .\tools\install_runtime_anchor_probe.py `
  --game-root "D:\steam\steamapps\common\Teamfight Manager2" `
  --dll "D:\local-build\runtime_node_anchor_probe.dll" `
  --enable-exclusive
```

It refuses to write audit evidence inside the repository, inside the checked SDK tree, or over checked extra-source files. The runtime installer also refuses repository-internal DLL sources, writes runtime evidence outside the repository, and fails if the source or installed package contains:

```text
mod.override_info
setting/map_setting.map_setting
aseprite_resources/ingame/5v5/background_5v5.png
```

The generated install manifest records:

```text
map_setting_override_installed: false
asset_overrides_installed: false
scene_mutated: false
map_setting_node_world_transform: unproven
```

## Decision

PR #8 does not find a public SDK surface sufficient to prove the node/world transform. The current status remains:

```text
runtime_node_anchor_api: unavailable_in_checked_public_sdk_sources
map_setting_node_world_transform: unproven
candidate_369_370: blocked
may_enter_mutation_pr: false
```

The next acceptable read-only path is offline decoded anchoring against original runtime data or a new public SDK/debug surface from the game, not a background PNG inference.
