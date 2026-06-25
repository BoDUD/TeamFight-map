# Runtime Map Loading Spike

Date: 2026-06-25

This spike answers whether the LOL-like map can move from design data into a real Teamfight Manager 2 runtime mod. It intentionally stops before full map art, collision masks, spawn edits, or path export.

## Current Answers

| Question | Current answer | Evidence |
| --- | --- | --- |
| Can map visuals be replaced by asset override? | Yes for `background_5v5`; static visual map-layer overrides are viable. | Manual QA on 2026-06-25 loaded `tfm2_lol_map_spike` in a 5v5 match and showed the diagnostic background while units, minions, towers, jungle monsters, and AI routes stayed stable. Installed Workshop mods and prior local probes also use ordinary `mod.override_info` remaps for visual layers. |
| Can collision, minion paths, and spawn points be replaced by data files? | Not proven. | The loader accepts a byte-equivalent `asset/base/setting/map_setting` remap when the staged file is named `setting/map_setting.map_setting`, but no decoded field mutation has been tested. Visual layer overrides leave native AI/pathing intact. |
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

For the next local-only equivalent `map_setting` remap gate:

```powershell
python .\tools\install_runtime_spike_mod.py `
  --clean `
  --enable-exclusive `
  --stage-map-setting-equivalent `
  --map-setting-source "D:\path\to\original\map_setting"
```

This mode does not modify the repository's `mods/tfm2_lol_map_spike/mod.override_info`. It copies the binary source unchanged into the installed game mod at `mods/tfm2_lol_map_spike/setting/map_setting.map_setting`, injects the temporary override only into that installed copy, validates byte size, SHA-256, and byte-for-byte equality, and writes a manifest outside the repository under `stage_runtime_spike_evidence/runtime_map_loading_spike/`. The asset remap remains extensionless: `asset/tfm2_lol_map_spike/setting/map_setting`.

The first no-extension staging attempt on 2026-06-25 failed before gameplay validation: the game reported `Only 1/2 asset override(s) were applied`, and `log.log` recorded `Override source 'asset/tfm2_lol_map_spike/setting/map_setting' ... was not found`. Use the `.map_setting` staged filename for the next A/B run.

## Manual QA Evidence

| Date | Probe | Evidence | Result |
| --- | --- | --- | --- |
| 2026-06-25 | `tfm2_lol_map_spike` overriding `asset/base/aseprite_resources/ingame/5v5/background_5v5` | Screenshot stored outside the repository at `D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\background_override_verified_20260625-201420.png`; `1919x1079`, `374534` bytes, SHA-256 `17E20C7AFD4A0DDBAC17E69C10EE7D79811C94B9EDA2DAD68672C3446DA8DA8D` | Pass. Diagnostic background appears in match. Units, minion waves, towers, jungle monsters, and AI routes have no observed abnormalities. |
| 2026-06-25 | Q2a byte-equivalent `asset/base/setting/map_setting` remap staged only in the installed game copy | Summary stored outside the repository at `D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\q2a_b1_summary.json`; cold start screenshots `q2a_b1_coldstart1_live_20260625-223645.png` SHA-256 `7582051d44254b05ca19f0eefb7281d04baaa2ab32fe138aa3dc6578cfadfc59` and `q2a_b1_coldstart2_live_20260625-224248.png` SHA-256 `a503b89fdd3afc99a1f25d07fe1dcc50305a6ae6067a0c5a486d3ac648544048`; staged `map_setting.map_setting` SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Pass for loader takeover only. Two cold starts reached live 5v5 with the diagnostic background visible and no `source not found` or partial-override warning in the game log. Units, minions, towers, and AI routes remained visibly normal. This does not prove `map_setting` can be safely decoded, re-encoded, or mutated. |

This proves the background visual asset can be overridden through `mod.override_info`, and that the loader accepts a byte-equivalent `map_setting` takeover when staged with the `.map_setting` file extension. It does not prove collision, lane pathing, spawn points, brush gameplay regions, objective placement, or `map_setting` mutation.

## Resource Audit

Only paths, formats, and field surfaces are recorded here. No original game resource payloads are committed.

| Runtime area | Candidate path or field | Format | Current status |
| --- | --- | --- | --- |
| Map background / ground texture | `asset/base/aseprite_resources/ingame/5v5/background_5v5` | PNG, native `1280x1280` | Verified in match through `tfm2_lol_map_spike`; diagnostic probe visible and native simulation behavior stable. |
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
| MapSetting data | `asset/base/setting/map_setting` | Binary, local size `1451980` bytes, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Equivalent remap loads when the installed file is staged as `setting/map_setting.map_setting`. Candidate for path/collision/spawn/placement, but must not be mutated until a byte-identical decode/re-encode round trip succeeds. |
| World bounds | likely `map_setting.visible_view` plus binary map tables | SDK field plus binary tables | Public field exists, but full runtime meaning is not proven. |
| Walls / collision data | likely `asset/base/setting/map_setting` binary tables | Binary grid/table | Not proven replaceable. |
| Walkable area | likely `asset/base/setting/map_setting.path` or adjacent binary path tables | SDK field plus binary tables | Public `path` exists, but safe replacement workflow is not proven. |
| Brush gameplay regions | likely `asset/base/setting/map_setting` | Binary or private runtime data | Not proven. Visual brush PNG is separate. |
| Defense tower, base, and jungle spawn points | likely `asset/base/setting/map_setting` or private scene data | Unknown / binary candidate | Not exposed by public SDK probes. |
| Minion paths | likely `asset/base/setting/map_setting.path` | SDK field plus binary path table | Path edit not proven. |
| AI pathing or navigation data | likely `asset/base/setting/map_setting` path tables | Binary grid/table | Native behavior remains after visual-only overrides. |
| Match scene config | static ingame layers plus settings assets | Mixed visual assets and setting data | No direct `add_map` or `replace_map` API found. |

## Test Order

1. Done: load this mod package without any DLL or `map_setting` override.
2. Done: confirm the game recognizes `mod.mod_info`.
3. Done: enter a 5v5 match and confirm the solid-color `background_5v5` probe is visible.
4. Done: confirm units, minions, towers, jungle camps, and AI routes remain native and stable.
5. Done: create a separate local-only `map_setting` equivalent remap with an unmodified copied asset.
6. Next: decode `map_setting`, re-encode without field edits, and prove the output is byte-identical to the original.
7. Later: only after byte-identical round trip passes, try one tiny collision/path/spawn mutation in a separate branch or PR.

## Q2a Equivalent Remap Gate

Question:

```text
Q2a: does the loader accept an unmodified byte-equivalent map_setting remap?
```

Strict A/B:

| Run | Installed override state | Purpose |
| --- | --- | --- |
| A | Background-only `tfm2_lol_map_spike` | Already verified visual baseline. |
| B | Same as A, plus installed-copy-only `asset/base/setting/map_setting` equivalent remap | Tests whether the loader accepts and reads a local `map_setting` replacement without changing gameplay data. |

Required non-visual proof for B:

```text
Process: TeamfightManager2.exe
Path: ...\mods\tfm2_lol_map_spike\setting\map_setting.map_setting...
Operation: CreateFile / ReadFile
Result: SUCCESS
```

This can come from Process Monitor or a game loader log. A successful match alone is not enough because the replacement file is byte-identical to the original and could be ignored by the loader.

B pass criteria:

- Replacement file is actually read by `TeamfightManager2.exe`.
- Mod remains enabled.
- No resource loading errors.
- 5v5 match starts successfully.
- Spawn points, towers, jungle monsters, and objective actors are normal.
- Minion waves and hero AI paths are normal.
- Brush gameplay behavior is unchanged.
- At least two cold starts pass.
- Source and staged target size and SHA-256 match, and byte-for-byte comparison passes.

If B passes, record only loader takeover success. It still does not prove `map_setting` can be safely modified.

Result on 2026-06-25: B passed for loader takeover. The staged file was `mods/tfm2_lol_map_spike/setting/map_setting.map_setting`, both source and staged copy were `1451980` bytes with SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0`, and two cold starts reached live 5v5 without loader warnings. The first no-extension attempt remains a recorded failure and should not be repeated.

The next gate after B is:

```text
map_setting decode
-> no field edits
-> re-encode
-> output must be byte-identical to input
```

Only a byte-identical round trip should open the door to a tiny, reversible data mutation.

## Stop Conditions

- If the game does not recognize `tfm2_lol_map_spike`, fix metadata or install layout before touching assets.
- If the game recognizes the mod but the background does not change, fix `mod.override_info` or asset path resolution before adding more layers.
- If a visual-only probe affects pathing or AI, stop and record the regression before any map data mutation.
- If `map_setting` equivalent remap fails, do not build a full map exporter. The project needs either a decoded loader-compatible asset pipeline or an SDK/API change.
