# Runtime Map Loading Spike

Date: 2026-06-25

This spike answers whether the LOL-like map can move from design data into a real Teamfight Manager 2 runtime mod. It intentionally stops before full map art, collision masks, spawn edits, or path export.

## Current Answers

| Question | Current answer | Evidence |
| --- | --- | --- |
| Can map visuals be replaced by asset override? | Yes for `background_5v5`; static visual map-layer overrides are viable. | Manual QA on 2026-06-25 loaded `tfm2_lol_map_spike` in a 5v5 match and showed the diagnostic background while units, minions, towers, jungle monsters, and AI routes stayed stable. Installed Workshop mods and prior local probes also use ordinary `mod.override_info` remaps for visual layers. |
| Can collision, minion paths, and spawn points be replaced by data files? | Not proven. | The loader positively reads a byte-equivalent `asset/base/setting/map_setting` remap when the staged file is named `setting/map_setting.map_setting`; Process Monitor captured `TeamfightManager2.exe` `CreateFile SUCCESS` and `ReadFile SUCCESS` for the installed local file. A structural decode/re-encode round trip is byte-identical, Q2c has characterized a symmetric read-only edge candidate, and Q2c-1 shows that `chunked_binary` is not a transitive closure. Q2d audited original bundle/setting data offline but found no sufficient independent anchor; `packed4_0` path-graph transform scoring remains ambiguous. Q2e risk acceptance planning defines a possible two-byte probe but does not run it. No decoded field mutation has been tested. Visual layer overrides leave native AI/pathing intact. |
| If data replacement fails, does ModExtension/DLL expose enough map API? | Not currently proven. | PR #8 source-level audit found only `ModExtension::post_update` plus opaque `Scene`, `GameUI`, and `Assets` parameters in the checked public SDK/source surface. No public `visible_view`, `path`, world-to-screen transform, debug draw/text overlay, camera/viewport, or entity-position anchor surface was found. |

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
| 2026-06-26 | Q2c-1 read-only relation semantics and `30x30` transform validation | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\map_setting_transform_validation\`: manifest `semantic_validation_manifest.json` SHA-256 `ab61692d680d287ba92793ae134a9fd1b880d57d8b19a63048d577bbb206d3a8`, contingency `chunked_packed4_contingency.json` SHA-256 `c491d8ffbacbd92b6ad2ce41a9720d6d81c9fea76fbe3ff49455b988ed163150`, 180 check `candidate_rotation180.json` SHA-256 `c14912012eae02c53491beadbd1728df23a3e39e5104a514d14b81d9a8749ad1`, direction mapping `direction_code_mapping.json` SHA-256 `d3ae47d8c0c5012443b54855a011a64fdb3a3f43b82919129d43d9c810e1a74a`, transform scores `transform_scores.json` SHA-256 `458ce3e11ea874fbbff1d26444a41d1e979128a45b5c8ab1de33d6bc6d0d333a`, grid probe `runtime_grid_probe.png` SHA-256 `b32cd9669b2f9d1147e7612ab91996ac0152a6156592858e2f622ea73757ddc8` | Q2c-1 pending, not mutation-approved. `chunked_binary` is symmetric but not closure-like (`connected_pair_row_signature_mismatch_ratio: 0.999888`, `closure_like: false`). It is not globally 180-degree rotation symmetric (`rotation180_relation_mismatch_count: 44116`). The `packed4_0` cross-table does not create a strong sentinel conflict for edge `369-370`, but direction code `15` is unresolved and transform scoring is ambiguous: `rotate180` score `0.013291`, `identity` score `0.013200`, margin `0.000091`. Candidate status is still not mutation-approved. |
| 2026-06-26 | Q2c-1 runtime background UV captures | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\map_setting_transform_validation\`: `runtime_grid_probe_screenshot_blue_candidate.png` SHA-256 `7f8f4b1907f56e2077ffba7924850fa7fc0e19a53d1abb8c165e5b2ca8eca2c6`, `runtime_grid_probe_screenshot_red_base.png` SHA-256 `97c996833a5559fbd4c07bfb883b22f5d47413ee6c48b627b826e20b8ef6ee7c`, `runtime_anchor_measurements.json` SHA-256 `91c3b7211fa3f8179f0d39623efd231dbc09f6676130a2206772b50fe3131056` | Runtime background UV calibration pass for observed views. The grid probe renders in match with near-square pitch and no extra mirror/rotation detected in the captured views. This is background texture evidence only; node labels are pre-rendered in the PNG, so `map_setting_node_world_transform` remains unproven and candidate mutation remains disallowed. |
| 2026-06-26 | PR #8 read-only runtime node-anchor API discovery | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\runtime_node_anchor_probe\runtime_node_anchor_api_audit.json`; size `7948` bytes, SHA-256 `1035df9a8f6af3a89ce2e931d51fb66bc0b0c334c96e099e89882c7cdcfe9fba`. Local DLL compile check produced ignored build artifact `runtime_node_anchor_probe.dll` SHA-256 `33d826f22b13520bf10fa9d5bc691f475d1bde66f721a450176ac52d07875499`. | `runtime_node_anchor_api: unavailable_in_checked_public_sdk_sources`. The checked public source exposes a read-only callback shape but no independent node/world anchor surface. The new `tfm2_lol_anchor_probe` package is DLL-only and has no `mod.override_info`, `map_setting`, or background asset. Candidate `369-370` remains blocked. |
| 2026-06-26 | Q2d offline runtime map anchor discovery | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\offline_runtime_map_anchor_discovery\`: asset index `bundle_asset_index.json` SHA-256 `7641a29a8626df715e82f499380845d4b9759ab4f4bc5f9b08efd0fef159328d`, map-related assets `bundle_map_related_assets.json` SHA-256 `df0a15db39b791d9a6787e6419bef3fa8735138a83c61760b63ec5e1f4e2d6e8`, setting scan report `anchor_candidate_report.json` SHA-256 `0344ee6d66a8d2f8b23dd719f2b46aa86e864e76640f4544a043990291213acf`, path graph scores `transform_scores_path_graph.json` SHA-256 `7678ec7330de54370f22333daa58c2065fd4f31a7a90d9ed2259ab86cf91e1f6` | Q2d: no sufficient offline anchor found. The bundle audit found 143 map-related metadata candidates and the blob scan found 68 unverified coordinate-like tables, but none are semantically tied to three non-collinear runtime anchors. `packed4_0` path-follow is weak/unresolved and transform scoring is still ambiguous: `rotate180` vs `identity` margin `0.000198`. `map_setting_node_world_transform` remains unproven and candidate `369-370` remains blocked. |
| 2026-06-26 | Q2e risk acceptance planning for a minimal mutation probe | No runtime evidence yet; this is a document and tool gate only. See `docs/minimal_mutation_risk_acceptance.md` and `tools/map_setting_mutate_symmetric_edge.py`. | Pending review. The proposed probe is risk-accepted only, not proven safe: mutate exactly offsets `427536` and `427573` from `1` to `0`, preserve transpose symmetry, write only repository-external output, and do not auto-install. No mutated file has been generated, staged, or tested in game by this PR. |

This proves the background visual asset can be overridden through `mod.override_info`, that the loader registers and reads a byte-equivalent `map_setting` override when staged with the `.map_setting` file extension, that the currently observed structural framing can round-trip byte-identically without edits, and that a cautious symmetric edge candidate has been characterized and partially checked. It does not prove collision, lane pathing, spawn points, brush gameplay regions, objective placement, world/grid transform, or `map_setting` mutation.

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
| MapSetting data | `asset/base/setting/map_setting` | Binary, local size `1451980` bytes, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Equivalent remap registration, positive local-file read, and byte-identical structural round trip succeed when the installed file is staged as `setting/map_setting.map_setting`. Read-only layer characterization selected one symmetric `chunked_binary` edge candidate at serialized byte offsets `427536` and `427573`; Q2c-1 shows it does not violate a transitive-closure invariant or the current packed4 sentinel heuristic. Q2d still found no sufficient offline runtime anchor, and `packed4_0` path-graph transform scoring remains ambiguous. Candidate for path/collision/spawn/placement investigation only; must not be mutated until a node/world anchor is proven or explicit risk acceptance is documented. |
| World bounds | likely `map_setting.visible_view` plus binary map tables | Unknown / binary candidate | Not found in checked public SDK/source surfaces; full runtime meaning is not proven. |
| Walls / collision data | likely `asset/base/setting/map_setting` binary tables | Binary grid/table | Not proven replaceable. |
| Walkable area | likely `asset/base/setting/map_setting.path` or adjacent binary path tables | Unknown / binary candidate | `path` was not found in checked public SDK/source surfaces; safe replacement workflow is not proven. |
| Brush gameplay regions | likely `asset/base/setting/map_setting` | Binary or private runtime data | Not proven. Visual brush PNG is separate. |
| Defense tower, base, and jungle spawn points | likely `asset/base/setting/map_setting` or private scene data | Unknown / binary candidate | Not exposed by public SDK probes. |
| Minion paths | likely `asset/base/setting/map_setting.path` | Unknown / binary candidate | Path edit not proven and no public path API was found in the checked SDK/source surface. |
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
9. Done: run read-only relation semantics and offline transform validation for candidate edge `369-370`.
10. Done: stage the pure visual coordinate grid background probe and capture background UV evidence.
11. Done: audit the checked public SDK/source surface and add an independent read-only DLL probe skeleton; no sufficient node/world anchor API was found.
12. Done: run offline original bundle/setting anchor discovery. No sufficient independent anchor was found; path-graph transform scoring remains ambiguous.
13. In progress: review whether to accept one explicitly risky, two-byte, reversible A/B/A probe despite the unproven node/world transform.
14. Next if risk acceptance is approved: generate one repository-external mutated file with `tools/map_setting_mutate_symmetric_edge.py`; do not install it automatically.
15. Later only in a separate PR: run the A/B/A runtime proof and stop on any loader error, gameplay abnormality, or rollback failure.

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

## Q2c-1 Relation Semantics And Transform Gate

Question:

```text
Can edge 369-370 be promoted from a structural candidate to a runtime mutation target?
```

Result on 2026-06-26: not yet. `tools/map_setting_validate_semantics.py` keeps this phase read-only, extracts local original wall/minimap resources, compares `chunked_binary` against `packed4_0`, infers adjacent direction-code distributions, scores all eight `30x30` square transforms, and writes a pure visual coordinate-grid background probe.

Key findings:

| Check | Result |
| --- | --- |
| `chunked_binary` transpose symmetry | Pass: `transpose_mismatch_count: 0`. |
| Closure/transitivity risk | Not a closure: `connected_pair_row_signature_mismatch_ratio: 0.999888`, `closure_like: false`. |
| 180-degree node rotation risk | Not a global invariant: `rotation180_relation_mismatch_count: 44116`, `rotation180_relation_symmetric: false`. |
| `chunked_binary` x `packed4_0` sentinel rule | No strong rule: `P(packed4_0 == 15 | chunked_binary == 0) = 0.196971`, `P(chunked_binary == 0 | packed4_0 == 15) = 0.895068`. |
| Candidate cross-layer conflict | No conflict detected for the current heuristic: chunked forward/reverse are `1`, packed4 forward/reverse are both `15`. |
| Direction code mapping | Ambiguous overall because code `15` has purity `0.136223`; codes `0-7` look direction-like but are not enough to approve mutation. |
| Offline transform scoring | Ambiguous: `rotate180` score `0.013291`, `identity` score `0.013200`, margin `0.000091`. |
| Runtime grid screenshot | Captured as background UV evidence only; it does not prove node/world transform. |

Current candidate decision:

```text
candidate_status: pending_independent_node_anchor
may_enter_mutation_pr: false
```

To stage the generated grid probe as background-only evidence, use:

```powershell
python .\tools\install_runtime_spike_mod.py `
  --clean `
  --enable-exclusive `
  --stage-background-source "D:\tfm2_q2a_evidence\map_setting_transform_validation\runtime_grid_probe.png"
```

The checked public SDK/source surface does not currently provide that anchor. The next evidence item should come from offline decoded original runtime data or a new SDK/debug surface, not a mutated `map_setting`.

## Q2d Offline Runtime Anchor Discovery Gate

Question:

```text
Do original bundle.game_data / setting resources contain an independent anchor that proves the map_setting node/world transform?
```

Result on 2026-06-26: no sufficient offline anchor found. `tools/audit_bundle_map_assets.py` indexed `bundle.game_data` and found 143 map-related metadata candidates. `tools/scan_setting_anchor_candidates.py` scanned 29 binary candidates and reported 68 coordinate-like tables, but none are semantically tied to known entities, world bounds, or three non-collinear runtime anchors. `tools/derive_map_setting_path_graph.py` derived a local path graph from `chunked_binary` and `packed4_0`, but `packed4_0` path following is only `weak_or_unresolved` and transform scoring is still ambiguous.

Key findings:

| Check | Result |
| --- | --- |
| Bundle map-related metadata | 143 candidates; metadata only, no payload committed. |
| Possible binary anchor sources | 27 from metadata filtering. |
| Binary assets scanned | 29. |
| Coordinate-like tables | 68, all `unverified_coordinate_table`; no semantic entity labels. |
| `packed4_0` path-follow validation | 20,000 connected pairs tested; 17,986 reached, 2,014 unresolved code. |
| Path graph transform scoring | `rotate180` best, `identity` second, margin `0.000198`; conclusion `ambiguous`. |

Current Q2d decision:

```text
offline_anchor_result: no_sufficient_anchor_found
map_setting_node_world_transform: unproven
candidate_369_370: blocked
may_enter_mutation_pr: false
```

Do not open a mutation PR from this state. The next valid paths are a stronger decoder for original runtime data, a newly exposed SDK/debug anchor surface, or an explicit risk-acceptance document before a tiny controlled probe.

## Q2e Minimal Mutation Risk Acceptance Gate

Question:

```text
Without a proven node/world anchor, does the project accept one tightly bounded two-byte mutation probe?
```

Current PR status: planning only. `docs/minimal_mutation_risk_acceptance.md` records the known evidence and unknowns, then defines a single risk-accepted candidate:

```text
layer: chunked_binary
offsets: 427536, 427573
old values: 1, 1
new values: 0, 0
changed_cell_count: 2
changed_byte_count: 2
map_setting_node_world_transform: unproven
risk label: risk-accepted candidate, not proven safe
```

`tools/map_setting_mutate_symmetric_edge.py` implements the file generator for that exact candidate only. It requires `--confirm-risk-accepted`, rejects repository-internal paths, rejects path/hardlink aliases, verifies the known input SHA-256, verifies both old byte values, requires the diff to be exactly two bytes, decodes the output, and verifies transpose symmetry remains intact.

This PR does not generate, install, or runtime-test a mutated `map_setting`. If the risk gate is approved, the next PR may generate the repository-external B file and run the A/B/A protocol. The result must be named `Q2e Loader Mutation Probe Pass` unless a clear, local, reversible, explainable gameplay effect is observed.

## Stop Conditions

- If the game does not recognize `tfm2_lol_map_spike`, fix metadata or install layout before touching assets.
- If the game recognizes the mod but the background does not change, fix `mod.override_info` or asset path resolution before adding more layers.
- If a visual-only probe affects pathing or AI, stop and record the regression before any map data mutation.
- If `map_setting` equivalent remap fails, do not build a full map exporter. The project needs either a decoded loader-compatible asset pipeline or an SDK/API change.
