# Runtime Map Loading Spike

Date: 2026-06-25

This spike answers whether the LOL-like map can move from design data into a real Teamfight Manager 2 runtime mod. It intentionally stops before full map art, collision masks, spawn edits, or path export.

## Current Answers

| Question | Current answer | Evidence |
| --- | --- | --- |
| Can map visuals be replaced by asset override? | Yes for `background_5v5`; static visual map-layer overrides are viable. | Manual QA on 2026-06-25 loaded `tfm2_lol_map_spike` in a 5v5 match and showed the diagnostic background while units, minions, towers, jungle monsters, and AI routes stayed stable. Installed Workshop mods and prior local probes also use ordinary `mod.override_info` remaps for visual layers. |
| Can collision, minion paths, and spawn points be replaced by data files? | Not proven. | The loader positively reads a byte-equivalent `asset/base/setting/map_setting` remap when the staged file is named `setting/map_setting.map_setting`; Process Monitor captured `TeamfightManager2.exe` `CreateFile SUCCESS` and `ReadFile SUCCESS` for the installed local file. A structural decode/re-encode round trip is byte-identical, and Q2c has characterized a symmetric read-only edge candidate, but no decoded field mutation has been tested. Visual layer overrides leave native AI/pathing intact. |
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

To reproduce the completed local-only equivalent `map_setting` remap run:

```powershell
python .\tools\install_runtime_spike_mod.py `
  --clean `
  --enable-exclusive `
  --stage-map-setting-equivalent `
  --map-setting-source "D:\path\to\original\map_setting"
```

This mode does not modify the repository's `mods/tfm2_lol_map_spike/mod.override_info`. It copies the binary source unchanged into the installed game mod at `mods/tfm2_lol_map_spike/setting/map_setting.map_setting`, injects the temporary override only into that installed copy, validates byte size, SHA-256, and byte-for-byte equality, and writes a manifest outside the repository under `stage_runtime_spike_evidence/runtime_map_loading_spike/`. The asset remap remains extensionless: `asset/tfm2_lol_map_spike/setting/map_setting`.

The first no-extension staging attempt on 2026-06-25 failed before gameplay validation: the game reported `Only 1/2 asset override(s) were applied`, and `log.log` recorded `Override source 'asset/tfm2_lol_map_spike/setting/map_setting' ... was not found`. Use the `.map_setting` staged filename when reproducing Q2a.

## Manual QA Evidence

| Date | Probe | Evidence | Result |
| --- | --- | --- | --- |
| 2026-06-25 | `tfm2_lol_map_spike` overriding `asset/base/aseprite_resources/ingame/5v5/background_5v5` | Screenshot stored outside the repository at `D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\background_override_verified_20260625-201420.png`; `1919x1079`, `374534` bytes, SHA-256 `17E20C7AFD4A0DDBAC17E69C10EE7D79811C94B9EDA2DAD68672C3446DA8DA8D` | Pass. Diagnostic background appears in match. Units, minion waves, towers, jungle monsters, and AI routes have no observed abnormalities. |
| 2026-06-25 | Q2a byte-equivalent `asset/base/setting/map_setting` remap staged only in the installed game copy | Summary stored outside the repository at `D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\q2a_b1_summary.json`; cold start screenshots `q2a_b1_coldstart1_live_20260625-223645.png` SHA-256 `7582051d44254b05ca19f0eefb7281d04baaa2ab32fe138aa3dc6578cfadfc59` and `q2a_b1_coldstart2_live_20260625-224248.png` SHA-256 `a503b89fdd3afc99a1f25d07fe1dcc50305a6ae6067a0c5a486d3ac648544048`; staged `map_setting.map_setting` SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Earlier registration-only pass. Two cold starts reached live 5v5 with the diagnostic background visible and no `source not found` or partial-override warning in the game log. Units, minions, towers, and AI routes remained visibly normal. The following Process Monitor row completes the positive `CreateFile` / `ReadFile SUCCESS` evidence gate. |
| 2026-06-25 | Q2a positive local file-read evidence for the staged `map_setting.map_setting` | Process Monitor evidence stored outside the repository at `D:\tfm2_q2a_evidence\`: `q2a_file_read_procmon.pml` SHA-256 `cdd8a988e8a982bdf527b68ba619b2ebdebda0d24f773f4afa48829a161de1a7`, filtered `q2a_file_read_procmon.csv` SHA-256 `8eedab38208b6a85954a1ce937b47232abd116f2ba43e41144e9cc7c776262b5`, live screenshot `q2a_file_read_screenshot.png` SHA-256 `e74181647d32966248e12b51e9f2a7f35b80583f424ea32434ece2dce473fa62`, manifest `q2a_file_read_manifest.json` SHA-256 `20744e93e93e9e12387746e2f473e6a80e48ed91fc683c1c4fd596ce117bb694`; staged `map_setting.map_setting` SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Q2a: Loader Takeover Pass. `TeamfightManager2.exe` PID `9952` opened `D:\steam\steamapps\common\Teamfight Manager2\mods\tfm2_lol_map_spike\setting\map_setting.map_setting` with `CreateFile SUCCESS` at `23:18:08.1826610`, then read it with `ReadFile SUCCESS` at `23:18:08.1864235`, `Offset: 0, Length: 1,451,980`. This proves the local staged file was read; it does not prove the binary format can be decoded, re-encoded, or safely mutated. |
| 2026-06-25 | Q2b byte-identical structural `map_setting` round trip | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\map_setting_round_trip\`: manifest `map_setting_round_trip_manifest.json` SHA-256 `842a5f003f9307dbc6ceda2adc7ffa1fe30bc1a18ce2e9034cb52b54f695ed84`, output `map_setting.roundtrip.map_setting` SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0`; input and output size `1,451,980` bytes | Q2b: Byte-Identical Round Trip Pass. The tool decodes only structural framing, preserving gameplay payloads as uninterpreted bytes: one chunked binary layer from offset `0` to `1,033,448`, followed by two packed4 layers ending at `1,438,464` and `1,451,980`. Re-encoding without field edits produced the same SHA-256 and no first-difference offset. This does not prove any gameplay field can be safely changed. |
| 2026-06-26 | Q2c read-only `map_setting` layer characterization | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\map_setting_layer_inspection\`: manifest `layer_inspection_manifest.json` SHA-256 `ef3d1ae47b0a75a8e27eb2c9df89c0f4ea76ac8725c22b4a64dde7504330ef78`, clearance manifest `candidate_clearance_manifest.json` SHA-256 `792a33f2c310b68e05e569e1088b3df81c3c3210b7ab26e1c18a8ebc917c0e3c`, generated diagnostic masks and overlays for `chunked_binary`, `packed4_0`, and `packed4_1` | Q2c read-only symmetric edge characterized. `chunked_binary` is a `900x900` binary layer with `transpose_mismatch_count: 0`, consistent with a symmetric `30x30` source-target relation such as visibility or reachability. Candidate for follow-up review only: edge `369-370`, cells `[370,369]` and `[369,370]`, serialized byte offsets `427536` and `427573`, old values `1`, planned values `0`, `transpose_mismatch_count_after_if_applied: 0`. Risk remains `unverified` because the world/grid transform is not proven and the nearest design feature is `GATE_BLUE_TOP_RIVER`. No mutated file was generated or installed. |

This proves the background visual asset can be overridden through `mod.override_info`, that the loader registers and reads a byte-equivalent `map_setting` override when staged with the `.map_setting` file extension, that the currently observed structural framing can round-trip byte-identically without edits, and that a cautious symmetric edge candidate has been characterized for review. It does not prove collision, lane pathing, spawn points, brush gameplay regions, objective placement, or `map_setting` mutation.

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
| MapSetting data | `asset/base/setting/map_setting` | Binary, local size `1451980` bytes, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Equivalent remap registration, positive local-file read, and byte-identical structural round trip succeed when the installed file is staged as `setting/map_setting.map_setting`. Read-only layer characterization selected one symmetric `chunked_binary` edge candidate at serialized byte offsets `427536` and `427573`, but its risk remains unverified pending world/grid validation. Candidate for path/collision/spawn/placement, but must not be mutated except in a tiny reversible follow-up probe. |
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
6. Done: capture positive `TeamfightManager2.exe` `CreateFile` / `ReadFile SUCCESS` evidence for `mods\tfm2_lol_map_spike\setting\map_setting.map_setting`.
7. Done: decode `map_setting`, re-encode without field edits, and prove the output is byte-identical to the original.
8. Done: characterize the decoded layers read-only, generate repository-external masks/overlays, and characterize one symmetric edge candidate plus rollback constraints.
9. Next: validate or explicitly accept the candidate world/grid risk, then try one tiny reversible mutation in a separate branch or PR with A/B/A runtime proof.

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

If B captures positive read evidence, record only loader takeover success. It still does not prove `map_setting` can be safely modified.

Result on 2026-06-25: Q2a Loader Takeover Pass. B passed override registration, and Process Monitor captured positive local-file access by `TeamfightManager2.exe`: `CreateFile SUCCESS` at `23:18:08.1826610` followed by `ReadFile SUCCESS` at `23:18:08.1864235` for `mods\tfm2_lol_map_spike\setting\map_setting.map_setting`; the `ReadFile` detail was `Offset: 0, Length: 1,451,980`, matching the staged file size. The staged file was `1451980` bytes with SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0`, and live 5v5 reached match with the diagnostic background visible. The first no-extension attempt remains a recorded failure and should not be repeated. This is loader takeover proof only, not decode/re-encode or mutation safety.

## Q2b Byte-Identical Round Trip Gate

Question:

```text
map_setting decode
-> no field edits
-> re-encode
-> output must be byte-identical to input
```

Result on 2026-06-25: Q2b Byte-Identical Round Trip Pass. `tools/map_setting_round_trip.py` decoded the local `map_setting` into structural framing only, preserving the actual layer payloads as uninterpreted bytes. Re-encoding produced `D:\tfm2_q2a_evidence\map_setting_round_trip\map_setting.roundtrip.map_setting`, size `1,451,980`, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0`, with `first_difference: null`.

Decoded structural layout:

| Section | Offset | End | Shape |
| --- | ---: | ---: | --- |
| Chunked binary layer | 0 | 1,033,448 | 30 groups x 30 grids x 30 rows x 30 bytes => 900x900 cells |
| Packed4 layer 0 | 1,033,448 | 1,438,464 | 810,000 4-bit cells / 405,000 bytes |
| Packed4 layer 1 | 1,438,464 | 1,451,980 | 27,000 4-bit cells / 13,500 bytes |

This is still not a gameplay-field decoder. Only a tiny, reversible data mutation should be attempted next, and only in a separate PR with exact offset/context evidence and an install-time rollback path.

## Q2c Read-Only Layer Characterization Gate

Question:

```text
Which decoded layer has the safest, most interpretable symmetric target for the first reversible mutation?
```

Result on 2026-06-26: a symmetric edge candidate is characterized for follow-up review only. `tools/map_setting_inspect.py` unfolds the structural layers into repository-external diagnostic masks, extracts local original visual assets from `bundle.game_data`, creates overlays for comparison, and writes candidate clearance evidence. The tool does not generate a mutated `map_setting` and does not install anything into the game.

Summary:

| Layer | Current interpretation | First-mutation decision |
| --- | --- | --- |
| `chunked_binary` | Symmetric `900x900` binary source-target matrix over a `30x30` logical grid. It most likely represents visibility or reachability, not a direct terrain-category mask. | Selected only as a symmetric edge candidate layer; a single-cell edit is rejected because it would break transpose symmetry. |
| `packed4_0` | `900x900` 4-bit table with values `0-7` and `15`, likely path or next-hop related. | Excluded for the first mutation because path/AI risk is higher. |
| `packed4_1` | `27000` 4-bit values; `30x30x30` slices are an unverified diagnostic view only. | Excluded. |

Selected read-only structural candidate:

```text
layer: chunked_binary
candidate_unit: undirected_edge
edge: 369-370
source_xy_30x30: [9, 12]
target_xy_30x30: [10, 12]
cell_1_logical_coordinate: [370, 369]
cell_1_serialized_byte_offset: 427536
cell_2_logical_coordinate: [369, 370]
cell_2_serialized_byte_offset: 427573
old_value: 1
planned_new_value: 0
changed_cell_count: 2
changed_byte_count: 2
transpose_mismatch_count_before: 0
transpose_mismatch_count_after_if_applied: 0
rollback_source_sha256: 6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0
risk_classification: unverified
prediction_confidence: hypothesis
```

Under the unverified linear `30x30` grid-to-design transform, this edge has lane clearance `16.499` or greater and nearest-feature clearance `7.401` to `GATE_BLUE_TOP_RIVER`. Because the original `map_setting` world/grid transform is not yet proven and the nearest feature is a jungle-to-river gate, this PR records `risk_classification: unverified`, not low risk. The next PR may build a mutation tool around this exact symmetric edge only after validating or explicitly accepting that grid-risk boundary, and it must still run A/B/A and stop on any crash, load error, pathing abnormality, failed rollback, or broader-than-expected diff.

## Stop Conditions

- If the game does not recognize `tfm2_lol_map_spike`, fix metadata or install layout before touching assets.
- If the game recognizes the mod but the background does not change, fix `mod.override_info` or asset path resolution before adding more layers.
- If a visual-only probe affects pathing or AI, stop and record the regression before any map data mutation.
- If `map_setting` equivalent remap fails, do not build a full map exporter. The project needs either a decoded loader-compatible asset pipeline or an SDK/API change.
