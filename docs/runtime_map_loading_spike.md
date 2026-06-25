# Runtime Map Loading Spike

Date: 2026-06-25

This spike answers whether the LOL-like map can move from design data into a real Teamfight Manager 2 runtime mod. It intentionally stops before full map art, collision masks, spawn edits, or path export.

## Current Answers

| Question | Current answer | Evidence |
| --- | --- | --- |
| Can map visuals be replaced by asset override? | Yes for static visual layers. Keep the next PR focused on a single `background_5v5` probe. | Installed Workshop mods and prior local probes use ordinary `mod.override_info` remaps for `background_5v5`, `wall_5v5`, tower/nexus sheets, shadows, and minimap background. |
| Can collision, minion paths, and spawn points be replaced by data files? | Not proven. | Visual layer overrides leave native AI/pathing intact. `asset/base/setting/map_setting` is the main candidate, but it is a binary asset and must be proven through an unmodified equivalent remap before mutation. |
| If data replacement fails, does ModExtension/DLL expose enough map API? | Not currently proven. | Public SDK probes found `ServerModContext.database.map_setting` exposes only `visible_view` and `path`; obvious `objectives`, `objective_spawns`, `jungle_camps`, `spawn`, and neutral objective fields were not exposed. |

## Minimal Mod Package

This PR adds:

```text
mods/tfm2_lol_map_spike/
  mod.mod_info
  mod.override_info
  README.md
  aseprite_resources/ingame/5v5/background_5v5.png
```

The override table follows the installed Workshop schema:

```json
{
  "asset/base/aseprite_resources/ingame/5v5/background_5v5": {
    "remapping": "asset/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/background_5v5",
    "type": "override"
  }
}
```

The PNG is a generated solid-color diagnostic asset. It is not image-gen map art and is not intended to ship as a map texture.

Install the spike into the local game folder with:

```powershell
python .\tools\install_runtime_spike_mod.py --clean --enable-exclusive
```

The script copies the repository package to the game-scanned `mods/tfm2_lol_map_spike/` folder and, when `--enable-exclusive` is used, writes `config/game/mods.json` with only this spike enabled for isolated QA.

## Resource Audit

Only paths, formats, and field surfaces are recorded here. No original game resource payloads are committed.

| Runtime area | Candidate path or field | Format | Current status |
| --- | --- | --- | --- |
| Map background / ground texture | `asset/base/aseprite_resources/ingame/5v5/background_5v5` | PNG, native `1280x1280` | Visual override route verified by references; this PR includes a one-asset probe. |
| Primary wall visual layer | `asset/base/aseprite_resources/ingame/5v5/wall_5v5` | PNG, native `1280x1280` | Override route verified by references; not included in this minimal spike package. |
| Foreground wall visual layer | `asset/base/aseprite_resources/ingame/5v5/wall_5v5_front` | PNG, native `1280x1280` | Candidate visual layer; test separately after background. |
| Wall shadow visual layer | `asset/base/aseprite_resources/ingame/5v5/wall_shadow_5v5` | PNG, native `1280x1280` | Candidate visual layer; not pathing. |
| Brush visual layer | `asset/base/aseprite_resources/ingame/5v5/bush_5v5` | PNG, native `1280x1280` | Candidate visual layer; does not prove brush gameplay state. |
| Brush shadow visual layer | `asset/base/aseprite_resources/ingame/5v5/bush_shadow_5v5` | PNG, native `1280x1280` | Candidate visual layer; not pathing. |
| Tower and base shadows | `asset/base/aseprite_resources/ingame/5v5/tower_shadow`, `asset/base/aseprite_resources/ingame/5v5/nexus_shadow` | PNG | Visual polish candidates. |
| Tower and base actor sprites | `asset/base/aseprite_resources/ingame/blue_tower#sheet`, `#anim`, red tower, blue/red nexus | PNG sheet plus animation data | Reference mods prove asset remaps work when sheet and anim contracts are preserved. |
| Jungle monster sprites | `asset/base/aseprite_resources/ingame/rhino#sheet`, `epic#sheet`, `serpen#sheet`, matching `#anim` | PNG sheet plus animation data | Reference mods prove visual actor remaps work; camp placement is separate. |
| Minion visual sprites | `asset/base/aseprite_resources/UI_aseprite/minion#sheet`, `#anim` | PNG sheet plus animation data | Reference mods prove visual actor remaps work; lane paths are separate. |
| Minimap resource | `asset/base/aseprite_resources/ingame/5v5/minimap_5v5_bg` | PNG, native `320x320` in prior probe | HUD minimap background can be tested after map background. |
| MapSetting data | `asset/base/setting/map_setting` | Binary, prior local size `1451980` bytes | Candidate for path/collision/spawn/placement. Must not be mutated until equivalent remap loads. |
| World bounds | likely `map_setting.visible_view` plus binary map tables | SDK field plus binary tables | Public field exists, but full runtime meaning is not proven. |
| Walls / collision data | likely `asset/base/setting/map_setting` binary tables | Binary grid/table | Not proven replaceable. |
| Walkable area | likely `asset/base/setting/map_setting.path` or adjacent binary path tables | SDK field plus binary tables | Public `path` exists, but safe replacement workflow is not proven. |
| Brush gameplay regions | likely `asset/base/setting/map_setting` | Binary or private runtime data | Not proven. Visual brush PNG is separate. |
| Defense tower, base, and jungle spawn points | likely `asset/base/setting/map_setting` or private scene data | Unknown / binary candidate | Not exposed by public SDK probes. |
| Minion paths | likely `asset/base/setting/map_setting.path` | SDK field plus binary path table | Path edit not proven. |
| AI pathing or navigation data | likely `asset/base/setting/map_setting` path tables | Binary grid/table | Native behavior remains after visual-only overrides. |
| Match scene config | static ingame layers plus settings assets | Mixed visual assets and setting data | No direct `add_map` or `replace_map` API found. |

## Test Order

1. Load this mod package without any DLL or `map_setting` override.
2. Confirm the game recognizes `mod.mod_info`.
3. Enter a 5v5 match and confirm the solid-color `background_5v5` probe is visible.
4. Confirm units, minions, towers, jungle camps, and AI routes remain native and stable.
5. Only after the visual probe passes, create a separate local-only `map_setting` equivalent remap with an unmodified copied asset.
6. Only after equivalent remap passes, try one tiny collision/path/spawn mutation in a separate branch or PR.

## Stop Conditions

- If the game does not recognize `tfm2_lol_map_spike`, fix metadata or install layout before touching assets.
- If the game recognizes the mod but the background does not change, fix `mod.override_info` or asset path resolution before adding more layers.
- If a visual-only probe affects pathing or AI, stop and record the regression before any map data mutation.
- If `map_setting` equivalent remap fails, do not build a full map exporter. The project needs either a decoded loader-compatible asset pipeline or an SDK/API change.
