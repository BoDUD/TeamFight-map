# Runtime Map Loading Spike

Date: 2026-06-25

This spike answers whether the LOL-like map can move from design data into a real Teamfight Manager 2 runtime mod. It intentionally stops before full map art, collision masks, spawn edits, or path export.

## Current Answers

| Question | Current answer | Evidence |
| --- | --- | --- |
| Can map visuals be replaced by asset override? | Yes for `background_5v5`; static visual map-layer overrides are viable. | Manual QA on 2026-06-25 loaded `tfm2_lol_map_spike` in a 5v5 match and showed the diagnostic background while units, minions, towers, jungle monsters, and AI routes stayed stable. PR #28 replaces the diagnostic solid color with a generated visual-only LOL-like background skin while keeping the active override background-only. Installed Workshop mods and prior local probes also use ordinary `mod.override_info` remaps for visual layers. |
| Can collision, minion paths, and spawn points be replaced by data files? | Not proven. | The loader positively reads a byte-equivalent `asset/base/setting/map_setting` remap when the staged file is named `setting/map_setting.map_setting`; Process Monitor captured `TeamfightManager2.exe` `CreateFile SUCCESS` and `ReadFile SUCCESS` for the installed local file. A structural decode/re-encode round trip is byte-identical, Q2c has characterized a symmetric read-only edge candidate, and Q2c-1 shows that `chunked_binary` is not a transitive closure. Q2d audited original bundle/setting data offline but found no sufficient independent anchor; `packed4_0` path-graph transform scoring remains ambiguous. Q2e then ran one explicitly risk-accepted two-byte `map_setting` A/B/A loader mutation probe, Q2f repeated the same B file with longer live observation past 3:00, and Q2g ran a second risk-accepted two-byte candidate through A/B/A. Q2h synthesizes those probes and recommends static decoding before any third runtime candidate because neither probe produced a semantic signal. Q2i refines `packed4_0`: codes `0-7` are strong direction-like candidates, but code `15` remains unresolved and the overall next-hop interpretation is still ambiguous. Q2j classifies code `15` contexts more deeply and keeps the result `ambiguous`: it is not a clean blocked sentinel, and connected non-self code15 contexts are not recoverable through the current no-15 graphs. Q2k shows all connected non-self code15 relations cross no15 components, making code `15` a static cross-component bridge candidate. Q2l classifies the 90 no15 singleton components as a structured special-node-set candidate, and Q2m shows those singleton nodes share a distinct node-major `packed4_1` profile absent from the 810-node large component. Q2n correlates those structural masks with original visual resources, but the transform result remains ambiguous. Q2o drills into the 30 node-major `packed4_1` slots and finds the complete singleton profile is exclusive while individual slot values are not. Q2p classifies exact `packed4_1` profile families, keeps Hamming clusters diagnostic-only, and finds asymmetric exact-family masks for a later read-only visual-correlation pass. Q2q scores those asymmetric exact-family masks against original visuals, but aggregate and resource-subset results remain ambiguous. Q2r inventories unclassified/residual `map_setting` sections and finds the known three structural layers consume the full baseline file, leaving no residual anchor candidates. Q2s closes the current spike route: gameplay `map_setting` editing remains blocked pending runtime anchor and semantic proof; the next route must be either visual-only deliverable or a separate runtime-anchor spike. This proves only that bounded two-byte `chunked_binary` mutations can be read and run through 5v5 observation; decoded field semantics, node/world transform, collision/path/spawn editing, and broader map safety remain unproven. |
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

The PNG is now an image-gen sourced visual-only LOL-like background skin normalized by the build script. It is not a gameplay map edit and not proof of collision/path/spawn editing.

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
| 2026-06-26 | Q2e risk-accepted two-byte `map_setting` loader mutation probe | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\minimal_mutation_probe\`: summary `q2e_loader_mutation_probe_summary.json` size `12,278`, SHA-256 `c84d0bb71deaa3e44997c633cb17cdb8787b3b02ddd5210b1ee6b352eaba9e41`; B mutation file `map_setting.q2e.mutated.map_setting` size `1,451,980`, SHA-256 `dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072`; mutation manifest SHA-256 `9129d2c4dcf1b86b602bfd4928f096f4e1e21dc3053a6999c08888d39595d380`; B filtered ProcMon CSV SHA-256 `2f8ec3aa0cc913b6f5420993c3ce7e229af94594a88724bf362523cc0feeab67`; A2 filtered ProcMon CSV SHA-256 `dd1eeaaef28dcd85cfa80d2f864927225a61325d1ff25c092d471fa873a32d1f`; screenshots for A1/B/A2 are recorded in `docs/q2e_loader_mutation_probe.md` by path, size, and SHA-256. | Q2e Loader Mutation Probe Pass. A1 original baseline reached 5v5 and 01:31. B staged only offsets `427536` and `427573` changed from `1` to `0`, reached 5v5 and 01:32, and Process Monitor captured `CreateFile SUCCESS` plus `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`, for the mutated installed file. A2 restored the original SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0`, reached 5v5 and 01:31, and Process Monitor captured the restored file read. This is loader mutation proof only; semantic safety and broader map edits remain unproven. |
| 2026-06-27 | Q2f semantic probe plan and read-only candidate catalog | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2f_semantic_probe_plan\`: candidates JSON size `24,231`, SHA-256 `3ef16f633a42993a98a55b46aa9b7c6b9826e169d47896ce6c27fae459c78254`; decision JSON size `899`, SHA-256 `6d1b847e64b98edba064e7aba588496e7b4a8bfffca60272cb273cb808db78f5`. | Q2f plan only. `tools/select_q2f_semantic_probe_candidates.py` catalogs higher-signal `chunked_binary` symmetric pairs without generating a mutated binary or installing runtime files. The recommended next runtime option remains repeating the same Q2e `369-370` mutation with longer observation. The top second candidate is cataloged only and has `may_enter_runtime_probe: false`. |
| 2026-06-27 | Q2f extended observation of the same Q2e `369-370` two-byte mutation | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2f_extended_observation_369_370\`: summary `q2f_extended_observation_summary.json` size `14,035`, SHA-256 `5d144efd6e24af63c1545442e1596243f122a5b6f9c60acf0a35259ea61d823e`; B filtered ProcMon CSV SHA-256 `3e582c795154421e49724970572aacd31dcb3b9ad500462a4eebe7b51592f5b3`; A2 filtered ProcMon CSV SHA-256 `9923f3c58b431dfed4e40573de4cb5fb8508b23f9cd7110516b0d0b118610299`; screenshots for A1/B/A2 are recorded in `docs/q2f_extended_observation_probe.md` by path, size, and SHA-256. | Q2f Extended Observation Probe Pass. A1 original baseline reached about 02:59. B reused the exact Q2e mutated file SHA-256 `dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072`, reached about 03:59, and Process Monitor captured `CreateFile SUCCESS` plus `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`, for the mutated installed file. A2 restored the original SHA-256 and reached about 03:23 with restored-file read proof. No obvious global AI, lane, tower, UI, minimap, or runtime abnormality was observed. This is extended observation only; semantic safety and broader map edits remain unproven. |
| 2026-06-27 | Q2g second-candidate risk acceptance and dedicated mutation-tool gate | No runtime evidence is produced by this PR. `docs/q2g_second_candidate_risk_acceptance.md` records the risk gate, and `tools/map_setting_mutate_q2g_second_candidate.py` is covered by synthetic unit tests only. | Q2g risk acceptance accepted for one controlled second-candidate probe only. Candidate `59-837` is higher signal than `369-370` but not proven safe: offsets `66605` and `932331`, old values `1, 1`, planned values `0, 0`, packed4 codes `1` and `3`, row/column hamming distance `873`. No real mutated binary is generated, no runtime staging occurs, and any A/B/A test must be a later PR. |
| 2026-06-28 | Q2g second-candidate `59-837` loader probe | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2g_second_candidate_probe\`: summary `q2g_second_candidate_probe_summary.json` size `14,621`, SHA-256 `ecb0ae7b7d9c631a126409eaaf5bc191dc8864d54f1d82aff5f37fb65dc9faab`; B mutation file `map_setting.q2g.59_837.mutated.map_setting` size `1,451,980`, SHA-256 `d633092b25abf6bee3527f51249650ebe91d3912f25040dcff0728164819156a`; mutation manifest SHA-256 `a78437844fc6387c5422e456b7e9757e37426c06fabe9c69ff1f5f15d14d97f2`; B filtered ProcMon CSV SHA-256 `deb1e8fa41588f3658beb38af5d1de635d95f71b201703796709e6f036e0572d`; A2 filtered ProcMon CSV SHA-256 `b0ccfadc60a014e6cfa880d3722be8403a008aa0d1d0234ec7406b60af3fbd35`; screenshots for A1/B/A2 are recorded in `docs/q2g_second_candidate_loader_probe.md` by path, size, and SHA-256. | Q2g Second Candidate Loader Probe Pass. A1 original baseline reached about 03:54. B staged only offsets `66605` and `932331` changed from `1` to `0`, reached about 03:52, and Process Monitor captured `CreateFile SUCCESS` plus `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`, for the mutated installed file. A2 restored the original SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0`, reached about 03:59, and Process Monitor captured the restored file read. No obvious global AI, lane, tower, UI, minimap, loader, or runtime abnormality was observed, and no clear local reversible gameplay effect was identified. This is loader probe proof only; semantic safety and broader map edits remain unproven. |
| 2026-06-28 | Q2h `chunked_binary` probe synthesis | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2h_chunked_binary_probe_synthesis\`: row/column classes JSON size `12,955`, SHA-256 `3c9589223712c6cad52b667f4283d0a3f83d086b1076c57178888b95f85a637b`; prior probe analysis JSON size `5,417`, SHA-256 `7b4d9df953fea56df24f32d14180164504e397b9852448cbeefb6f185a2905c7`; next strategy JSON size `2,105`, SHA-256 `f5a339aa46c3d467dc5923055d8c1b305d60e47ea6d6f7e995a79c14cd2c326f`. | Q2h synthesis only. `tools/analyze_chunked_binary_probe_targets.py` writes read-only JSON diagnostics outside the repository. Q2h found one universal-like `row_sum == 900` and `column_sum == 900` node: node `837`, which was one endpoint of Q2g `59-837`. This may explain why Q2g looked high-signal by row/column contrast but still produced no visible semantic effect. The next action is `continue_static_decoding`; do not run a third runtime probe now. |
| 2026-06-28 | Q2i `packed4_0` next-hop static decode | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2i_packed4_next_hop_static_decode\`: value histogram JSON size `1,416`, SHA-256 `ebf8110b6314a43637fc377974db95e32dfc77f1f550acb82dacd1ea7337912e`; direction candidates JSON size `2,371`, SHA-256 `aaf6fdf3b832b0586b6b2a94163994fa6faf2e0e791b4065add4b2f52d1288a7`; path-follow samples JSON size `36,504`, SHA-256 `6101fc77ce23768ec3a3b2e3452e2a9a618a7a632d7ada6a8ea4aea742c3ea92`; code 15 analysis JSON size `1,375`, SHA-256 `6b7610ba2fcd6bd3e3cbea15a43b88330865fea3a177c1b4f5162df2517ca015`; interpretation JSON size `3,890`, SHA-256 `53128ceaf217c23f41ad9cc3cd3fb7fe9017fcceb621e53e050779d152ffb1cc`. | Q2i static decode only. `packed4_0` values `0-7` show strong adjacent-direction behavior, with candidate directions `0:E`, `1:S`, `2:W`, `3:N`, `4:SE`, `5:SW`, `6:NE`, `7:NW`. Non-adjacent path-follow reached `42,803 / 50,000` sampled connected pairs (`0.856060`), and every sampled failure was unresolved code `15`. Code `15` remains `ambiguous_special_case`, so the overall interpretation is `packed4_0_interpretation: ambiguous`; runtime mutation remains disallowed. |
| 2026-06-28 | Q2j `packed4_0` code15 context analysis | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2j_packed4_code15_context_analysis\`: contexts JSON size `1,697`, SHA-256 `c8bcfce986a7c2732ed0150948b84fc8c26f9504ccf496b571a9eaf3f0bd7551`; distance buckets JSON size `11,328`, SHA-256 `32c3dab66b2e4651230d3df0a553f32acd06f2ddfe6bd34b4b7096d7254d801e`; endpoint classes JSON size `14,723`, SHA-256 `e3d7a1a35cd5dbf72a2ab9f0999f94a9a3bc23821d3af32defa60f9144643d05`; path recovery JSON size `21,879`, SHA-256 `c4f516085b07ee61e3a7b9e8339a4a70ddac8e0739e0ace6f1b2012c03f7c23d`; interpretation JSON size `3,555`, SHA-256 `a89ccbdf7ef88ca53190582db92af43aa9d0e2008b18202ceb31898e47be6cf3`. | Q2j static analysis only. Code `15` remains `ambiguous`: it appears with `chunked_binary == 0` in `138,476` cells and with `chunked_binary == 1` in `16,234` cells, so it is not a clean blocked sentinel. Among connected non-self code15 contexts, no pair was recoverable through either the inferred 0-7 direction graph without 15 or the chunked non15 graph. Runtime mutation, packed4 mutation, third chunked runtime probe, and broader map edits remain disallowed. |
| 2026-06-28 | Q2k code15/no15 component graph | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2k_code15_component_graph\`: no15 component summary JSON size `21,881`, SHA-256 `3733aadc1746281bd3908c78a44588bdfbd718215923a79f0485e9456121548a`; cross-component edges JSON size `25,002`, SHA-256 `f3a097735f23bc050dd1900912759bfb0b5720b5c23d98b9685912d58f6db213`; component pair matrix JSON size `36,276`, SHA-256 `bd8aea72cfe245ddb5c6f4bc574dcc33abb1a9abe922253734d1cd59504d1de0`; prior probe component context JSON size `3,934`, SHA-256 `afac523ddf3f51e078f73e4bf9001c6fbf4bb46756a580a7d57558c0955d5ff3`; packed4_1 correlation JSON size `50,482`, SHA-256 `ba80633b6d01dfb232d56ec388348fd6ff959e5c79bf24f5c19e4f3eb553ff78`; interpretation JSON size `1,953`, SHA-256 `daaa5f23116ee350bd9804fd730a3883bbfb305aef00d42d971e5078681c5f1d`. | Q2k static analysis only. The no15 graph has `91` weak components: one `810`-node component and ninety single-node components. All `15,930` connected non-self code15 relations cross components, so `code15_component_role` is `cross_component_bridge_candidate`. `packed4_1` does not show a clear component-id-like pattern under tested reshapes. Runtime mutation, packed4 mutation, third chunked runtime probe, and broader map edits remain disallowed. |
| 2026-06-28 | Q2l no15 singleton component classification | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2l_no15_singleton_components\`: singleton nodes JSON size `28,505`, SHA-256 `74f7c439bdab16f7618e9e29ba6d9bb1803c0396832aa1b50118497aa0347328`; spatial pattern JSON size `7,846`, SHA-256 `d09a031fab0bd3e368c78004b0644783cc195ca60d331d0d88ddd71995422d53`; bridge edges JSON size `33,163`, SHA-256 `fa77819df77455eefc81e0c4d83b0004337543d536cbafdbcf15aadfa38051ea`; singleton packed4_1 profiles JSON size `61,886`, SHA-256 `c5ca0a701478edc00822c0de54e357237f0a54e124377d34e71a93a387b7758f`; interpretation JSON size `2,992`, SHA-256 `f8649e6db505e758f36fd1fbd011ca5e8770077c62950b8e3ebd7c59646a2f1f`. | Q2l static analysis only. The 90 no15 singleton nodes are all interior, form a table-coordinate `band_candidate`, have symmetric code15 bridge degrees, and share one node-major packed4_1 profile that does not appear in the large no15 component. `no15_singleton_role` is `structured_special_node_set_candidate`; runtime mutation, packed4 mutation, third chunked runtime probe, and broader map edits remain disallowed. |
| 2026-06-28 | Q2m `packed4_1` node-major profile analysis | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2m_packed4_1_node_profiles\`: profile catalog JSON size `510,584`, SHA-256 `f38e9946012918cc1e86ca7b0aeed10a696fa43628f05c451d31157480ca49fe`; spatial patterns JSON size `45,774`, SHA-256 `a6141fd338381e50fd195a8f7e1ced938548d77a3e8d35e96342f0036eb39a3a`; component correlation JSON size `379,599`, SHA-256 `4b3babdc65c35c49ae94382e247e94ce3dc443e3738b9f1cd1e86131fb0b3284`; bridge correlation JSON size `904,423`, SHA-256 `bfb01cf453f51152dcac8d39efe6cd7c70b5096c66c621e70789f48b08078201`; tracked nodes JSON size `11,151`, SHA-256 `5dfe141bfe776d39d081da80b5a37364ec358cd30e8c8e858485a30b7f8e013c`; interpretation JSON size `2,934`, SHA-256 `c55b685a83e40ed3c886187c90ba357d71e8a15549f42f390f83c92a3f3a457d`. | Q2m static analysis only. Under the `900x30 node-major` hypothesis, `packed4_1` has `507` unique profiles. All 90 no15 singleton nodes share `profile_0001`, the alternating `[8, 0]` profile, and that profile is absent from the 810-node large component. The singleton profile has varied code15 bridge degrees (`90` to `400`), so it is a `node_class_descriptor_candidate`, not a bridge-strength proof. Runtime mutation, packed4 mutation, third chunked runtime probe, and broader map edits remain disallowed. |
| 2026-06-28 | Q2n map_setting structural mask visual correlation | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2n_map_setting_mask_visual_correlation\`: structural manifest JSON size `1,664`, SHA-256 `5b71711e6067348e75c124c6a0ce71c73e10b9f8e9c8253cfa8a71e6624a2b4f`; profile mask PNG size `2,266`, SHA-256 `4d5d9bdb3e9c40391b7eded01c5ad15a21b8c7d28881ebddcd871f334c331ad3`; large component mask PNG size `2,266`, SHA-256 `6a1b2554ba97288895714979d31639ea74692093629a5f1be17e7fc6313c3298`; bridge heatmap PNG size `3,601`, SHA-256 `2e9e823f4edce22e3516fe0ff32b31b524435135939b6443fdcc736c4ed7ca4d`; visual resource manifest JSON size `2,817`, SHA-256 `e84f1d119d7242c8ac45c7be67c7eb262ce6fb6aab35160f76230992f3591794`; transform summary JSON size `5,520`, SHA-256 `c0583fdaf068e7e0dbc2cd09ff29501f352a5ee907e5ad36112f9680b02a6c3d`; interpretation JSON size `1,561`, SHA-256 `986daf69a616ec33c6d561c055e4e28c52a89114026ad0e8cbdfd5662e922247`; plus 24 repository-external overlay PNGs. | Q2n static visual correlation only. Structural masks were compared with original `background_5v5`, `minimap_5v5_bg`, `wall_5v5`, `wall_5v5_front`, and `bush_5v5` resources across 8 transforms. The top transform was `transpose` with score `0.681203`, but `identity` scored `0.681138`; margin `0.000065`, so `visual_correlation_result` is `ambiguous` and `node_world_transform` remains `unproven`. Runtime mutation, packed4 mutation, third chunked runtime probe, and broader map edits remain disallowed. |
| 2026-06-29 | Q2o `packed4_1` slot-plane analysis | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2o_packed4_1_slot_planes\`: slot histograms JSON size `153,541`, SHA-256 `ddbfb1c71890f57117f5963a20e4fee13af57327fd86e59fcc800b17789c44fc`; spatial patterns JSON size `927,705`, SHA-256 `ba81eff1785209fc592340e69c2e9e3b787f645d6c54808547b7424039dbd8f6`; component correlation JSON size `232,454`, SHA-256 `08d9750cf9945231b70be23b228ca1eb853670b8758ad2ed72dc41feb37583a9`; pair correlation JSON size `29,374`, SHA-256 `080c38ad463f28c3f5f1ec0eb6f7e7933e97f69c36cd54af5db7e6d0dd9c923d`; profile signature JSON size `8,975`, SHA-256 `dcf3c76ddbd9908a6f1cbb9e6f3903e2f347e82531626eb31e7cf8fbdd0b57a0`; tracked nodes JSON size `10,422`, SHA-256 `b5b2926a77c7f356ba8cc59b85a9112000e27de6bf04b2e3e53d082e79e45a1f`; interpretation JSON size `2,109`, SHA-256 `a68459b16c751856ba639f9130b4659002f65a4a985cb08f81f5ba6b8fc44040`; plus 208 repository-external slot/value mask PNGs and one contact sheet. | Q2o static analysis only. The full singleton `packed4_1[node * 30 : node * 30 + 30]` profile remains exclusive to all 90 no15 singleton nodes and follows the alternating `[8, 0]` signature, but individual slot/value pairs are not singleton-exclusive (`singleton_only_slot_value_count: 0`). `packed4_1_slot_role` is `slot_level_node_class_descriptor_candidate`; runtime mutation, packed4 mutation, third chunked runtime probe, and broader map edits remain disallowed. |
| 2026-06-29 | Q2p `packed4_1` profile-family analysis | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2p_packed4_1_profile_families\`: profile family catalog JSON size `2,254,100`, SHA-256 `ffb0c6a3d2a1b24d5ffd73fc61c116fa1f41b448daf197d611d2bdfef76509a0`; Hamming clusters JSON size `33,718`, SHA-256 `5ca8360edce6cc001f32d9ddf1604a28d11b715f48fc6a358a00da515d9125ab`; spatial patterns JSON size `706,370`, SHA-256 `4b7c1c48459b1eee756f21760fc23343f0ff1214ea20d72a10984d03cdfb6a0c`; component correlation JSON size `417,308`, SHA-256 `e8e564df6765178be81bbb0d97adfdad2c55dc0f8c86a98d538d3ff082be9627`; anchor candidates JSON size `44,550`, SHA-256 `0c64a66751e9c07f7074e814c7c7608e64366aca454a89418dde85575baea7fc`; tracked nodes JSON size `16,642`, SHA-256 `6a938414a1a6341d22bc92ebe9497af8dadc7f43b5326f5c0389da951af12002`; interpretation JSON size `1,901`, SHA-256 `127b19d1ecbe530500ed43129f88d143c32771e199d3e2386e94e4373301e176`; plus 40 repository-external family mask PNGs and one contact sheet SHA-256 `95d7a902faa4dfe120802643a05d335c33f53e62af86d03285ae9bcf7d43cd82`. | Q2p static analysis only. Exact node-major profile families remain the primary interpretation surface: `507` exact families, with `family_0001` containing all 90 no15 singleton nodes and the alternating `[8, 0]` profile. Hamming threshold `2` yields `73` diagnostic clusters and `1,337` Hamming-neighbor edges, but clusters do not override exact-family conclusions. The tool found `134` asymmetric exact-family masks that may be useful only for a later read-only visual-correlation pass. Runtime mutation, packed4 mutation, third chunked runtime probe, and broader map edits remain disallowed. |
| 2026-06-29 | Q2q asymmetric profile-family visual correlation | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2q_profile_family_mask_visual_correlation\`: visual resource manifest JSON size `2,835`, SHA-256 `d05a80aaf990c5354d4d751511015c1988d5a83f2a2160fb4d021ec7d8b0a047`; anchor candidate manifest JSON size `155,942`, SHA-256 `fd0643366335700377d05e205d5ea16ba8ba92d11bc806e2f634cad58e42a473`; transform score summary JSON size `186,797`, SHA-256 `1fc7f19d51dd5fa89c7b392f2ababbbdd13e1b0041517a34fb09e0cfdb57ef0e`; per-family rankings JSON size `397,222`, SHA-256 `54a2b05f36d4ea974332af7cbd419fc2acf9020dbae515c52a5751713f68fa6f`; aggregate vote summary JSON size `184,830`, SHA-256 `8626e8eb26f7c6825c565174dc5e8f8d7009eee20574d3652939b7d8a95c9e0f`; interpretation JSON size `2,139`, SHA-256 `13bca932166394c1a6d6894e169e3876384397a435b353e979e83ef089e6f289`; plus 80 repository-external overlay PNGs for the top 10 candidate families. | Q2q static visual correlation only. The tool re-derived `134` Q2P asymmetric exact-family masks and ranked each against original visuals across 8 transforms. Aggregate best was `rotate90`, second was `anti_transpose`, but margin was only `0.015180` and best vote share only `0.256246`. Wall, bush, minimap, and background subsets stayed ambiguous and did not converge. `q2q_result` is `ambiguous`; `node_world_transform` remains `unproven`; runtime mutation, packed4 mutation, third chunked runtime probe, and broader map edits remain disallowed. |
| 2026-07-01 | Q2r unclassified `map_setting` section inventory | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2r_map_setting_unclassified_sections\`: section inventory JSON size `2,310`, SHA-256 `e756a696357c9e566a20a01d4ea2c8fb6814e3305e7e80cf4dd242ad1de19506`; residual entropy JSON size `837`, SHA-256 `b918ba6968fc3c110a9cf5abd71848baf644c46bbadde983a7fcda263e1becec`; dimensioned array candidates JSON size `836`, SHA-256 `cd0e145b91d6ca239d09384bf6d3d1cabb077a56ccab10d3a49609b0bffd9546`; coordinate-like candidates JSON size `840`, SHA-256 `f349bc0646cd4d403deed1b19cb3c2661a4230d99be7fb02f1ca054ea7d9b41c`; cross-layer reference candidates JSON size `846`, SHA-256 `72594ed38a887086ddced32b07dd9eb102154646bd21296f30252b265f285f7a`; tracked context JSON size `7,303`, SHA-256 `ed249a984b3a67b89606cff2a49cb18edfe76136f1f24db8ad124d5206edde5c`; interpretation JSON size `1,758`, SHA-256 `aa83c3a786126837ba1dfb1dc18cbafa513067fd8327722bab017443927bdffc`. | Q2r static section inventory only. The known `chunked_binary`, `packed4_0`, and `packed4_1` layers consume the full `1,451,980` byte baseline file. `residual_span_count: 0`, `dimensioned_array_candidate_count: 0`, `coordinate_like_candidate_count: 0`, and `cross_layer_reference_candidate_count: 0`. `unclassified_anchor_candidates_found: false`; `node_world_transform` remains `unproven`; runtime mutation, packed4 mutation, third chunked runtime probe, and broader map edits remain disallowed. |
| 2026-07-01 | Q2s map_setting route decision | Evidence stored outside the repository at `D:\tfm2_q2a_evidence\q2s_map_setting_route_decision\q2s_status_matrix.json`; size `4,082`, SHA-256 `4648a69269e8ead3339c7e5ea81c83b46ab59d24965e9e29c3b50d2c5bc79c93`. | Q2s route decision only. `q2_map_setting_route_status: blocked_pending_runtime_anchor`, `node_world_transform: unproven`, `semantic_safety: not_proven`, `runtime_mutation_allowed: false`, `packed4_mutation_allowed: false`, `third_chunked_binary_runtime_probe_allowed: false`, and `map_editing_allowed: false`. The next route must be explicitly chosen as either visual-only deliverable or a separate runtime-anchor/instrumentation spike; gameplay map editing remains blocked. |

This proves the background visual asset can be overridden through `mod.override_info`, that the loader registers and reads a byte-equivalent `map_setting` override when staged with the `.map_setting` file extension, that the currently observed structural framing can round-trip byte-identically without edits, and that two risk-accepted two-byte `chunked_binary` mutations can run through live 5v5 observation. Q2h then shows those probes did not produce semantic signal and recommends static decoding before any third runtime probe. Q2i narrows `packed4_0` toward direction-like codes `0-7`; Q2j keeps code `15` unresolved after deeper context analysis; Q2k classifies code15 as a static cross-component bridge candidate; Q2l classifies the singleton components as a structured special-node-set candidate; Q2m classifies the singleton-only node-major `packed4_1` profile as a static node-class descriptor candidate; Q2n shows current structural masks do not produce a unique visual transform against original resources; Q2o shows that the complete singleton profile is more informative than any individual slot/value; Q2p separates exact profile families from diagnostic Hamming clusters and finds asymmetric family masks for later read-only visual correlation; Q2q applies those sharper masks to original visuals but still gets an ambiguous transform result; Q2r finds no residual or unclassified `map_setting` spans outside the known three layers; Q2s records that this route is blocked pending runtime anchor and semantic proof. It does not prove collision, lane pathing, spawn points, brush gameplay regions, objective placement, world/grid transform, or broader `map_setting` mutation safety.

## Resource Audit

Only paths, formats, and field surfaces are recorded here. No original game resource payloads are committed.

| Runtime area | Candidate path or field | Format | Current status |
| --- | --- | --- | --- |
| Map background / ground texture | `asset/base/aseprite_resources/ingame/5v5/background_5v5` | PNG, native `1280x1280` | Override route verified in match through `tfm2_lol_map_spike`; PR #28 replaces the earlier diagnostic probe with a generated visual-only LOL-like skin. Runtime QA for the new skin is a follow-up PR. |
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
| MapSetting data | `asset/base/setting/map_setting` | Binary, local size `1451980` bytes, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Equivalent remap registration, positive local-file read, and byte-identical structural round trip succeed when the installed file is staged as `setting/map_setting.map_setting`. Read-only layer characterization selected one symmetric `chunked_binary` edge candidate at serialized byte offsets `427536` and `427573`; Q2c-1 shows it does not violate a transitive-closure invariant or the current packed4 sentinel heuristic. Q2d still found no sufficient offline runtime anchor, and `packed4_0` path-graph transform scoring remains ambiguous. Q2e/Q2f loaded and observed `369-370`, and Q2g loaded and observed `59-837`; neither produced semantic signal. Q2h identifies Q2g endpoint `837` as the only universal-like row/column and recommends static decoding before a third runtime probe. Q2i shows `packed4_0` codes `0-7` are direction-like. Q2j shows code `15` is not a clean blocked sentinel and is not recoverable through current no-15 graphs. Q2k shows all connected non-self code15 edges cross no15 components. Q2l shows the 90 singleton components are an interior band-like special set with symmetric code15 bridges. Q2m shows those singleton nodes share one node-major `packed4_1` profile absent from the large component, making `packed4_1_node_major_role` a static `node_class_descriptor_candidate`. Q2n compares current structural masks against original visual resources, but the transform score margin is only `0.000065`, so visual correlation remains ambiguous. Q2o shows the full 30-slot singleton profile is exclusive, while individual slot/value pairs are not singleton-exclusive. Q2p keeps exact `packed4_1` profile families as the primary interpretation surface, records Hamming clusters as diagnostic-only, and finds asymmetric exact-family masks for a later read-only visual correlation pass. Q2q applies those asymmetric masks against original visuals, but aggregate and resource-subset transform results remain ambiguous. Q2r inventories unclassified/residual sections and finds no remaining spans outside `chunked_binary`, `packed4_0`, and `packed4_1`. Q2s records `q2_map_setting_route_status: blocked_pending_runtime_anchor` and requires either visual-only deliverable or separate runtime-anchor spike next. This is not gameplay semantic proof and does not approve packed4/path/collision/spawn/placement edits. |
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
3. Done: enter a 5v5 match and confirm the `background_5v5` override route is visible.
4. Done: confirm units, minions, towers, jungle camps, and AI routes remain native and stable.
5. Done: create a separate local-only `map_setting` equivalent remap with an unmodified copied asset.
6. Done: capture positive `TeamfightManager2.exe` `CreateFile` / `ReadFile SUCCESS` evidence for `mods\tfm2_lol_map_spike\setting\map_setting.map_setting`.
7. Done: decode `map_setting`, re-encode without field edits, and prove the output is byte-identical to the original.
8. Done: characterize the decoded layers read-only, generate repository-external masks/overlays, and characterize one symmetric edge candidate plus rollback constraints.
9. Done: run read-only relation semantics and offline transform validation for candidate edge `369-370`.
10. Done: stage the pure visual coordinate grid background probe and capture background UV evidence.
11. Done: audit the checked public SDK/source surface and add an independent read-only DLL probe skeleton; no sufficient node/world anchor API was found.
12. Done: run offline original bundle/setting anchor discovery. No sufficient independent anchor was found; path-graph transform scoring remains ambiguous.
13. Done: document explicit risk acceptance for one two-byte reversible probe despite the unproven node/world transform.
14. Done: generate one repository-external B file with `tools/map_setting_mutate_symmetric_edge.py`; do not commit the binary payload.
15. Done: stage and run the A1/B/A2 runtime proof with `tools/install_runtime_mutation_probe.py`, including B-stage positive file-read evidence and A2 rollback to the original SHA-256.
16. Done: define Q2f semantic-probe guardrails and catalog read-only second-candidate options without generating mutation files.
17. Done: repeat the same Q2e `369-370` mutation with longer observation to about 03:59 for B and A2 rollback to about 03:23.
18. Done: define the Q2g second-candidate `59-837` risk-acceptance gate and dedicated hardcoded mutation tool without generating a real B file.
19. Done: stage and run the Q2g second-candidate A1/B/A2 runtime proof with B-stage positive file-read evidence and A2 rollback to the original SHA-256.
20. Done: synthesize Q2e/Q2f and Q2g probe targets by row/column class and identify Q2g node `837` as the only universal-like row/column.
21. Done: refine `packed4_0` next-hop interpretation read-only. Codes `0-7` are direction-like; code `15` remains unresolved and overall interpretation is ambiguous.
22. Done: analyze `packed4_0` code15 contexts. Code `15` is not a clean blocked sentinel and remains ambiguous.
23. Done: analyze code15/no15 component graph structure. Code15 is a static cross-component bridge candidate.
24. Done: classify the 90 no15 singleton components as a structured special-node set candidate.
25. Done: classify node-major `packed4_1` profiles. The singleton profile is a static node-class descriptor candidate.
26. Done: correlate current structural masks with original visual resources. The result remains ambiguous and does not prove node/world transform.
27. Done: analyze the 30 node-major `packed4_1` slot planes. The complete profile is informative, but no individual slot/value isolates the singleton set.
28. Done: classify exact `packed4_1` profile families and separate diagnostic Hamming clusters. Asymmetric exact-family masks are available only for a later read-only visual-correlation pass.
29. Done: correlate Q2P asymmetric exact-family masks against original visuals. Aggregate and resource-subset transform results remain ambiguous.
30. Done: inventory unclassified/residual `map_setting` sections after the known three structural layers. No residual spans or direct anchor candidates were found.
31. Done: synthesize Q2 map_setting spike results and record route decision: gameplay map editing is blocked pending runtime anchor and semantic proof.
32. Done: choose Route A and add a background-only visual LOL-like skin package without enabling minimap or gameplay data overrides.
33. Next: run visual-only runtime QA for the new background skin. Do not broaden mutations from Q2g, mutate packed4, or start gameplay map editing.

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

Result on 2026-06-26: accepted for one controlled probe only. `docs/minimal_mutation_risk_acceptance.md` records the known evidence and unknowns, then defines a single risk-accepted candidate:

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

The risk acceptance does not prove safety. It only permits one repository-external B file and one A/B/A runtime probe.

## Q2e Loader Mutation Probe Gate

Question:

```text
Can the game load and run one risk-accepted two-byte map_setting mutation through 5v5 startup, then roll back to the original SHA-256?
```

Result on 2026-06-26: Q2e Loader Mutation Probe Pass. `docs/q2e_loader_mutation_probe.md` records the external evidence paths, file sizes, SHA-256 values, screenshots, and filtered ProcMon proof.

The B file was generated outside the repository and changed only:

```text
offset 427536: 1 -> 0
offset 427573: 1 -> 0
changed_byte_count: 2
changed_cell_count: 2
```

A/B/A runtime result:

| Run | map_setting | Runtime result |
| --- | --- | --- |
| A1 | Original byte-equivalent baseline, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | 5v5 entered and reached 01:31; visible heroes, minions, towers, jungle/objective actors, UI, and minimap appeared normal. |
| B | Two-byte risk-accepted mutation, SHA-256 `dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072` | 5v5 entered and reached 01:32. Process Monitor captured `TeamfightManager2.exe` `CreateFile SUCCESS` and `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`, for `mods\tfm2_lol_map_spike\setting\map_setting.map_setting`. No obvious global gameplay abnormality was observed. |
| A2 | Original byte-equivalent rollback, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | 5v5 entered and reached 01:31. Process Monitor captured the restored installed file with `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`. |

This proves the loader can read and run one risk-accepted two-byte `map_setting` mutation through 5v5 startup, and that the staged file can be rolled back to the original SHA-256. It does not prove the semantic meaning of `chunked_binary`, the true node/world transform, or the safety of broader map edits.

## Q2f Semantic Probe Plan Gate

Question:

```text
After Q2e loader pass, what is the next semantic probe without broadening into region edits?
```

Result on 2026-06-27: plan only. `docs/q2f_semantic_probe_plan.md` records two possible routes and selects the lower-risk route for the next runtime PR:

```text
recommended next runtime option: repeat the same Q2e 369-370 mutation with longer B observation
second candidate status: cataloged_not_selected
second candidate may_enter_runtime_probe: false
```

`tools/select_q2f_semantic_probe_candidates.py` reads the original `map_setting`, evaluates symmetric `chunked_binary` source-target pairs, and writes only JSON diagnostics outside the repository. It favors packed4 contrast plus row/column signature differences as semantic signal, but that score is not a gameplay-safety score.

Local read-only candidate run:

```text
candidate_count_considered: 53335
top cataloged second candidate: 59-837
top candidate offsets if ever separately reviewed: 66605, 932331
top candidate may_enter_runtime_probe: false
```

This PR does not generate, stage, or runtime-test a new mutated `map_setting`. A future PR may run `Q2f Extended Observation Probe` only against the same Q2e two-byte mutation unless a separate risk-acceptance review approves a second candidate.

## Q2f Extended Observation Probe Gate

Question:

```text
Does the same Q2e 369-370 two-byte mutation remain visibly stable when observed longer in live 5v5?
```

Result on 2026-06-27: Q2f Extended Observation Probe Pass. `docs/q2f_extended_observation_probe.md` records the external evidence paths, file sizes, SHA-256 values, screenshots, and filtered ProcMon proof.

The B file was not regenerated or changed. It reused the Q2e external mutation file:

```text
SHA-256: dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072
offset 427536: 1 -> 0
offset 427573: 1 -> 0
changed_byte_count: 2
changed_cell_count: 2
```

A/B/A runtime result:

| Run | map_setting | Runtime result |
| --- | --- | --- |
| A1 | Original byte-equivalent baseline, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | 5v5 entered and reached about 02:59; visible heroes, minions, towers, UI, and minimap appeared normal. |
| B | Same Q2e two-byte mutation, SHA-256 `dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072` | 5v5 entered and reached about 03:59. Process Monitor captured `TeamfightManager2.exe` `CreateFile SUCCESS` and `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`, for `mods\tfm2_lol_map_spike\setting\map_setting.map_setting`. No obvious global AI standstill, wall-sticking, path jitter, lane, tower, UI, minimap, loader, or runtime abnormality was observed. |
| A2 | Original byte-equivalent rollback, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Rollback restored the original staged SHA-256, 5v5 entered, and observation reached about 03:23. Process Monitor captured the restored installed file with `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`. |

After the run, the installed local spike was reset to background-only: `mod.override_info` contains only `background_5v5`, and `mods\tfm2_lol_map_spike\setting\map_setting.map_setting` does not exist.

Conclusion:

```text
Q2f Extended Observation Probe Pass
semantic safety: not proven
node/world transform: unproven
second candidate 59-837: blocked
broader map edits: not approved
```

This extends Q2e's loader mutation startup proof to a longer observation of the same B file. It still does not prove `chunked_binary` semantics, the true node/world transform, or the safety of broader edits.

## Q2g Second Candidate Risk Acceptance Gate

Question:

```text
Should candidate 59-837 be allowed to enter one independent A/B/A runtime probe?
```

Result on 2026-06-27: accepted for one controlled second-candidate probe only. `docs/q2g_second_candidate_risk_acceptance.md` records the risk boundary. This PR does not generate a mutated `map_setting`, does not stage a runtime override, and does not run the game.

Candidate:

```text
layer: chunked_binary
edge: 59-837
cell 1 logical_coordinate: [837, 59]
cell 1 serialized_byte_offset: 66605
cell 2 logical_coordinate: [59, 837]
cell 2 serialized_byte_offset: 932331
old values: 1, 1
planned new values: 0, 0
changed_cell_count: 2
changed_byte_count: 2
risk label: risk-accepted second candidate, not proven safe
```

Why it is higher signal:

```text
row_sum_source: 27
row_sum_target: 900
row_signature_hamming_distance: 873
column_signature_hamming_distance: 873
packed4_0_forward: 1
packed4_0_reverse: 3
```

Why it is still risky:

```text
map_setting_node_world_transform: unproven
chunked_binary semantics: unproven
world position of source/target: unknown
AI / vision / pathing effect: unknown
```

`tools/map_setting_mutate_q2g_second_candidate.py` is a dedicated, non-generic tool. It only allows the above two offsets, requires `--confirm-risk-accepted`, rejects repository-internal paths, rejects output under any `mods` tree, rejects path/hardlink aliases, checks the original SHA-256, checks both old values, requires exactly two changed bytes, decodes the output, and verifies transpose symmetry remains `0`.

Current Q2g status:

```text
risk acceptance: accepted for one controlled second-candidate probe
mutated binary generated: false
runtime staged: false
semantic safety: not proven
broader map edits: not approved
```

The follow-up runtime probe has now been run; see the next section. The risk acceptance did not prove semantic safety.

## Q2g Second Candidate Loader Probe Gate

Question:

```text
Can the game load and run the risk-accepted second candidate 59-837 two-byte map_setting mutation through live 5v5, then roll back to the original SHA-256?
```

Result on 2026-06-28: Q2g Second Candidate Loader Probe Pass. `docs/q2g_second_candidate_loader_probe.md` records the external evidence paths, file sizes, SHA-256 values, screenshots, and filtered ProcMon proof.

The B file was generated outside the repository and changed only:

```text
offset 66605: 1 -> 0
offset 932331: 1 -> 0
changed_byte_count: 2
changed_cell_count: 2
```

A/B/A runtime result:

| Run | map_setting | Runtime result |
| --- | --- | --- |
| A1 | Original byte-equivalent baseline, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | 5v5 entered and reached about 03:54; visible heroes, minions, towers, UI, and minimap appeared normal. |
| B | Q2g second-candidate two-byte mutation, SHA-256 `d633092b25abf6bee3527f51249650ebe91d3912f25040dcff0728164819156a` | 5v5 entered and reached about 03:52. Process Monitor captured `TeamfightManager2.exe` `CreateFile SUCCESS` and `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`, for `mods\tfm2_lol_map_spike\setting\map_setting.map_setting`. No obvious global AI standstill, wall-sticking, path jitter, lane, loader, or runtime abnormality was observed. No clear local reversible gameplay effect was identified. |
| A2 | Original byte-equivalent rollback, SHA-256 `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Rollback restored the original staged SHA-256, 5v5 entered, and observation reached about 03:59. Process Monitor captured the restored installed file with `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`. |

After the run, the installed local spike was reset to background-only: `mod.override_info` contains only `background_5v5`, and `mods\tfm2_lol_map_spike\setting\map_setting.map_setting` does not exist.

Conclusion:

```text
Q2g Second Candidate Loader Probe Pass
semantic safety: not proven
node/world transform: unproven
broader map edits: not approved
```

This proves the loader can read and run the risk-accepted second candidate through live 5v5 observation and rollback. It still does not prove `chunked_binary` semantics, the true node/world transform, or the safety of broader edits.

## Q2h Chunked Binary Probe Synthesis Gate

Question:

```text
Why did Q2e/Q2f 369-370 and Q2g 59-837 both load successfully but produce no clear semantic signal?
```

Result on 2026-06-28: Q2h synthesis only. `docs/q2h_chunked_binary_probe_synthesis.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2h_chunked_binary_probe_synthesis\
```

Key row/column findings:

```text
matrix: 900 x 900
chunked value 0 count: 703,026
chunked value 1 count: 106,974
middle rows/columns: 782
sparse rows/columns: 112
near_universal rows/columns: 5
universal_like rows/columns: 1
universal_like node: 837
```

Prior probe interpretation:

| Probe | Row/column class | Runtime result | Semantic signal |
| --- | --- | --- | --- |
| Q2e/Q2f `369-370` | `369` middle, `370` middle; packed4 values `15 / 15` | Loader and extended observation pass | None observed |
| Q2g `59-837` | `59` sparse, `837` universal_like; packed4 values `1 / 3` | Loader pass | None observed |

Q2g's high row/column hamming distance remains real, but it touches the only `row_sum == 900` and `column_sum == 900` node. This may indicate a default, sentinel-like, redundant, or otherwise low-observability relation.

Decision:

```text
next_action: continue_static_decoding
do_not_run_third_runtime_probe_now: true
```

If a future PR proposes a third candidate, it needs a separate risk review and should avoid `row_sum_900` or `column_sum_900` universal-like nodes unless that is the explicit hypothesis. It must still avoid already tested edges, keep `changed_cell_count == 2`, keep `changed_byte_count == 2`, avoid `packed4`, avoid visual synchronization, and avoid broader region edits.

## Q2i Packed4 Next-Hop Static Decode Gate

Question:

```text
Is packed4_0 likely to be a next-hop / direction / path-query table?
```

Result on 2026-06-28: ambiguous. `docs/q2i_packed4_next_hop_static_decode.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2i_packed4_next_hop_static_decode\
```

Direction-code evidence:

```text
0 -> E   purity 0.908976
1 -> S   purity 0.908976
2 -> W   purity 0.908976
3 -> N   purity 0.908976
4 -> SE  purity 1.0
5 -> SW  purity 1.0
6 -> NE  purity 1.0
7 -> NW  purity 1.0
15 -> unresolved, purity 0.136223
```

Path-follow evidence:

```text
tested non-adjacent connected pairs: 50,000
reached: 42,803
unresolved_code: 7,197
reached_ratio: 0.856060
all sampled failures: code 15
```

Code `15` evidence:

```text
with chunked_binary == 0: 138,476
with chunked_binary == 1:  16,234
P(chunked_binary == 0 | packed4_0 == 15): 0.8950681921
P(packed4_0 == 15 | chunked_binary == 0): 0.1969713780
P(packed4_0 == 15 | chunked_binary == 1): 0.1517565016
interpretation: ambiguous_special_case
```

Conclusion:

```text
packed4_0_interpretation: ambiguous
runtime_mutation_allowed: false
packed4_mutation_allowed: false
next_recommended_step: continue_static_decoding
```

This narrows `packed4_0` substantially: codes `0-7` behave like direction/next-hop candidates, but code `15` is not a clean blocked sentinel and blocks a meaningful fraction of path-follow samples. No `packed4` mutation, third `chunked_binary` runtime probe, multi-edge edit, region edit, or visual sync is approved.

## Q2j Packed4 Code15 Context Analysis Gate

Question:

```text
What is packed4_0 code 15 most likely to mean?
```

Result on 2026-06-28: ambiguous. `docs/q2j_packed4_code15_context_analysis.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2j_packed4_code15_context_analysis\
```

Code15 x `chunked_binary` evidence:

```text
packed4_0 == 15 and chunked_binary == 0: 138,476
packed4_0 == 15 and chunked_binary == 1:  16,234
P(chunked_binary == 0 | packed4_0 == 15): 0.8950681921
P(chunked_binary == 1 | packed4_0 == 15): 0.1049318079
```

Connected code15 distance buckets in unproven table coordinates:

```text
distance 0:      304
distance 1:      336
distance 2-3:    654
distance 4-8:  2,364
distance 9+:  12,576
```

Recovery evidence:

```text
connected code15 total:          16,234
connected non-self code15 total: 15,930
self pairs:                         304
not recoverable without 15:      15,930
direction recovery ratio:             0
chunked non15 recovery ratio:         0
any recovery ratio:                   0
```

Conclusion:

```text
code15_interpretation: ambiguous
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
next_recommended_step: continue_static_decoding
```

This rules out two easy readings: code `15` is not a clean blocked sentinel, and connected non-self code15 contexts are not recoverable through the current no-15 graphs. It still does not prove whether code `15` is no-op, special, overflow, uncached, or part of another semantic layer. No `packed4` mutation, third `chunked_binary` runtime probe, multi-edge edit, region edit, or visual sync is approved.

## Q2k Code15 Component Graph Gate

Question:

```text
Does packed4_0 code 15 connect no-15 subgraph components?
```

Result on 2026-06-28: cross-component bridge candidate, static only. `docs/q2k_code15_component_graph.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2k_code15_component_graph\
```

No15 component definition:

```text
chunked_binary == 1
packed4_0 != 15
source != target
weak connected components
```

No15 component result:

```text
component_count: 91
component_size_histogram:
  size 810: 1
  size 1: 90
directed_no15_edge_count: 90,740
undirected_no15_edge_count: 45,370
```

Connected code15 cross-component result:

```text
code15 connected non-self edge count: 15,930
same_component_count: 0
cross_component_count: 15,930
cross_component_ratio: 1.0
```

Prior probe component context:

| Probe | Component context | packed4_0 values | Runtime signal |
| --- | --- | --- | --- |
| Q2e/Q2f `369-370` | `369` in singleton component `36`, `370` in large component `0`; cross-component | `15 / 15` | Loader + extended observation pass, no semantic effect |
| Q2g `59-837` | both nodes in large component `0`; same no15 component | `1 / 3` | Loader pass, no semantic effect |

Packed4_1 static correlation:

```text
tested reshapes: 900x30, 30x900, 30x30x30
component-id-like pattern: not_detected for all tested assumptions
packed4_1 mutation allowed: false
```

Conclusion:

```text
code15_component_role: cross_component_bridge_candidate
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

This strengthens the static hypothesis that code `15` marks component-bridging or special inter-component relations. It still does not prove gameplay semantics, node/world transform, or a safe edit path. No `packed4` mutation, third `chunked_binary` runtime probe, multi-edge edit, region edit, or visual sync is approved.

## Q2l No15 Singleton Component Classification Gate

Question:

```text
Are the 90 no15 singleton components structured special nodes, or scattered graph leftovers?
```

Result on 2026-06-28: structured special-node-set candidate, static only. `docs/q2l_no15_singleton_component_classification.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2l_no15_singleton_components\
```

Singleton node class result:

```text
singleton_count: 90
large_component_id: 0
large_component_size: 810
row/column class pairs:
  middle|middle: 88
  sparse|sparse: 2
edge positions:
  interior: 90
```

Spatial result:

```text
spatial_pattern: band_candidate
complete_rows: []
complete_columns: []
bounding_box:
  min_x: 3
  max_x: 26
  min_y: 3
  max_y: 26
```

Bridge result:

```text
large_component_to_singleton: 7,609
singleton_to_large_component: 7,609
singleton_to_singleton: 712
all_singletons_have_code15_bridge: true
all_singleton_bridge_degrees_symmetric: true
```

Packed4_1 profile result:

```text
node-major singleton unique profiles: 1
node-major large component unique profiles: 506
node-major shared profiles: 0
node-major signal: strong_unverified
```

Conclusion:

```text
no15_singleton_role: structured_special_node_set_candidate
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

This makes the singleton set look intentional in the static table graph, especially because all singleton `packed4_0` source rows are code15-only and all singleton nodes share a node-major `packed4_1` profile absent from the large component. It still does not prove gameplay semantics, node/world transform, or a safe edit path. No `packed4` mutation, third `chunked_binary` runtime probe, multi-edge edit, region edit, or visual sync is approved.

## Q2m Packed4_1 Node Profile Analysis Gate

Question:

```text
Does packed4_1 node-major profile data distinguish the 90 no15 singleton components from the large component?
```

Result on 2026-06-28: node-class descriptor candidate, static only. `docs/q2m_packed4_1_node_profile_analysis.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2m_packed4_1_node_profiles\
```

Profile catalog result:

```text
node-major profile definition: packed4_1[node * 30 : node * 30 + 30]
node_count: 900
unique_profile_count: 507
profile_frequency_histogram:
  1: 372
  2: 77
  3: 15
  4: 19
  5: 7
  6: 8
  7: 3
  9: 1
  10: 1
  12: 1
  14: 2
  90: 1
```

Singleton profile result:

```text
profile_id: profile_0001
singleton_node_count: 90
singleton_unique_profile_count: 1
shared_profile_count_with_large_component: 0
singleton_profiles_disjoint_from_large: true
profile:
  [8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
   8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
   8, 0, 8, 0, 8, 0, 8, 0, 8, 0]
```

Large component result:

```text
large_component_id: 0
large_component_node_count: 810
large_component_unique_profile_count: 506
```

Spatial result:

```text
profile_0001 spatial_pattern: matches_no15_singleton_band
singleton_overlap_count: 90
bounding_box:
  min_x: 3
  max_x: 26
  min_y: 3
  max_y: 26
```

Bridge-correlation result:

```text
profile_0001 total_code15_endpoint_count: 16,642
degree_min: 90
degree_max: 400
degree_average: 184.9111111111111
```

Because the same singleton profile has varied bridge degrees, Q2m treats it as a static class marker candidate, not a bridge-strength descriptor.

Conclusion:

```text
packed4_1_node_major_role: node_class_descriptor_candidate
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

This strengthens the static hypothesis that `packed4_1` has node-class information tied to the no15 singleton set. It still does not prove gameplay semantics, node/world transform, or a safe edit path. No `packed4` mutation, third `chunked_binary` runtime probe, multi-edge edit, region edit, or visual sync is approved.

## Q2n MapSetting Mask Visual Correlation Gate

Question:

```text
Do the current map_setting structural masks align with original map visual resources under one reliable transform?
```

Result on 2026-06-28: ambiguous visual correlation, static only. `docs/q2n_map_setting_mask_visual_correlation.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2n_map_setting_mask_visual_correlation\
```

Structural masks:

```text
profile_0001 node count: 90
large_component node count: 810
code15 bridge heatmap nonzero node count: 819
packed4_0 direction confidence nonzero node count: 810
node837 universal-like node count: 1
```

Original visual resources checked:

```text
background_5v5
minimap_5v5_bg
wall_5v5
wall_5v5_front
bush_5v5
```

Transform score result:

```text
best_transform: transpose
best_score: 0.681203
second_transform: identity
second_score: 0.681138
margin: 0.000065
visual_correlation_result: ambiguous
```

Conclusion:

```text
node_world_transform: unproven
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

This visual correlation pass does not produce a reliable transform candidate. The `transpose` score is effectively tied with `identity`, so it is not a node/world transform proof. No `packed4` mutation, third `chunked_binary` runtime probe, multi-edge edit, region edit, collision/path/spawn work, or visual sync is approved.

## Q2o Packed4_1 Slot Plane Analysis Gate

Question:

```text
Does packed4_1 node-major slot-plane data isolate the no15 singleton set at the slot/value level?
```

Result on 2026-06-29: slot-level node-class descriptor candidate, static only. `docs/q2o_packed4_1_slot_plane_analysis.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2o_packed4_1_slot_planes\
```

Core evidence:

```text
profile definition: packed4_1[node * 30 : node * 30 + 30]
singleton_profile_node_count: 90
full_profile_singleton_exclusive: true
alternating_even_8_odd_0: true
slot_value_all_singleton_exclusive: false
singleton_only_slot_value_count: 0
slot/value mask PNG count: 208
```

Singleton profile:

```text
[8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
 8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
 8, 0, 8, 0, 8, 0, 8, 0, 8, 0]
```

The complete 30-slot profile identifies all 90 no15 singleton nodes and remains absent from the large no15 component. However, individual slot values do not isolate the singleton set. For example:

```text
slot 0 value 8: 754 nodes total, 90 singleton nodes, 664 large-component nodes
slot 1 value 0: 813 nodes total, 90 singleton nodes, 723 large-component nodes
slot 27 value 0: 900 nodes total
slot 28 value 8: 900 nodes total
slot 29 value 0: 900 nodes total
```

Tracked-node context:

```text
node 369: singleton_component, full singleton slot profile, code15 endpoint degree 262
node 370: large_component, related but non-singleton profile
node 59: large_component, sparse row/column class, code15 endpoint degree 0
node 837: large_component, universal_like row/column class, code15 endpoint degree 180
```

Conclusion:

```text
packed4_1_slot_role: slot_level_node_class_descriptor_candidate
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

This strengthens the static hypothesis that the full node-major `packed4_1` profile encodes or describes membership in the no15 singleton node class. It does not prove that any individual slot is an editable class bit, does not prove gameplay semantics, does not prove node/world transform, and does not approve mutation of `packed4_1`, `packed4_0`, `chunked_binary`, regions, collision, pathing, spawns, or visual sync.

## Q2p Packed4_1 Profile Family Analysis Gate

Question:

```text
Can exact packed4_1 node-major profile families provide sharper static masks than slot/value planes?
```

Result on 2026-06-29: profile-level node-class descriptor candidate, static only. `docs/q2p_packed4_1_profile_family_analysis.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2p_packed4_1_profile_families\
```

Q2p separates two concepts:

```text
exact profile family:
  nodes with the exact same packed4_1[node * 30 : node * 30 + 30] profile

Hamming cluster:
  diagnostic connected components between exact profiles with Hamming distance <= 2
```

Exact profile families remain the primary interpretation surface. Hamming clusters are diagnostic only and do not override exact-family conclusions.

Core evidence:

```text
unique_profile_count: 507
exact_family_count: 507
top_family: family_0001
top_family_node_count: 90
top_family_dominant_role: singleton_component
hamming_threshold: 2
hamming_cluster_count: 73
hamming_edge_count: 1,337
asymmetric_anchor_candidates_found: true
anchor_candidate_count: 134
```

`family_0001` is the same complete singleton profile isolated in Q2m/Q2o:

```text
[8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
 8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
 8, 0, 8, 0, 8, 0, 8, 0, 8, 0]
```

Q2p also found small asymmetric exact-profile families that may be useful for a later read-only visual-correlation pass:

```text
family_0120: 2 nodes, large_component, asymmetry 1.0, avg code15 endpoint degree 160.0
family_0112: 2 nodes, large_component, asymmetry 1.0, avg code15 endpoint degree 75.0
family_0023: 5 nodes, large_component, asymmetry 1.0, avg code15 endpoint degree 66.4
family_0042: 4 nodes, large_component, asymmetry 1.0, avg code15 endpoint degree 57.0
family_0049: 3 nodes, large_component, asymmetry 1.0, avg code15 endpoint degree 52.666666666666664
```

These are not runtime anchors and are not approved mutation targets. They are candidate masks for future read-only visual correlation only.

Tracked-node context:

```text
node 369: profile_0001, family_0001, singleton_component, Q2e/Q2f endpoint
node 370: profile_0287, family_0287, large_component, Q2e/Q2f endpoint
node 59: profile_0156, family_0156, large_component, sparse, Q2g endpoint
node 837: profile_0002, family_0002, large_component, universal_like row/column, Q2g endpoint
```

Conclusion:

```text
packed4_1_profile_family_role: profile_level_node_class_descriptor_candidate
asymmetric_anchor_candidates_found: true
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

This strengthens the static hypothesis that exact node-major `packed4_1` profiles describe node classes and gives sharper asymmetric masks for a later read-only transform/correlation attempt. It does not prove gameplay semantics, does not prove node/world transform, does not approve a third runtime probe, and does not approve mutation of `packed4_1`, `packed4_0`, `chunked_binary`, regions, collision, pathing, spawns, or visual sync.

## Q2q Profile Family Visual Correlation Gate

Question:

```text
Do Q2P asymmetric exact-family masks produce a reliable visual transform candidate?
```

Result on 2026-06-29: ambiguous, static only. `docs/q2q_profile_family_visual_correlation.md` records the read-only analysis.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2q_profile_family_mask_visual_correlation\
```

Q2q re-derives Q2P exact-family candidates from the original `map_setting` and scores each asymmetric candidate mask across:

```text
identity
rotate90
rotate180
rotate270
flip_x
flip_y
transpose
anti_transpose
```

Candidate input:

```text
candidate_count: 134
overlay_png_count: 80
```

Aggregate result:

```text
best_transform: rotate90
second_transform: anti_transpose
aggregate_margin: 0.015180
best_vote_share: 0.256246
```

This fails the single-transform threshold:

```text
required aggregate_margin >= 0.03
required best_vote_share >= 0.60
```

Robustness subsets also remain ambiguous:

```text
all_resources: rotate90 over anti_transpose, margin 0.015180
wall_only: anti_transpose over rotate180, margin 0.012206
bush_only: rotate90 over rotate180, margin 0.001959
minimap_only: rotate270 over flip_y, margin 0.000153
background_only: rotate270 over rotate180, margin 0.002249
without_top_5_high_degree_families: rotate90 over flip_x, margin 0.008188
without_singleton_family: rotate90 over anti_transpose, margin 0.015180
```

Conclusion:

```text
q2q_result: ambiguous
candidate_transform: none
node_world_transform: unproven
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

This shows the Q2P asymmetric exact-family masks are sharper than Q2N's coarse structural masks, but they still do not produce a robust node/world transform candidate. It does not prove gameplay semantics, does not approve a third runtime probe, and does not approve mutation of `packed4_1`, `packed4_0`, `chunked_binary`, regions, collision, pathing, spawns, or visual sync.

## Q2r Unclassified Section Inventory Gate

Question:

```text
Does the original map_setting contain residual or unclassified spans outside the known structural layers that might provide a more direct anchor surface?
```

Result on 2026-07-01: no residual anchor candidates found, static only. `docs/q2r_map_setting_unclassified_section_inventory.md` records the read-only inventory.

The analysis output is repository-external:

```text
D:\tfm2_q2a_evidence\q2r_map_setting_unclassified_sections\
```

Q2r inventories the original baseline after parsing the currently known structural layers:

| Section | Offset | End | Shape |
| --- | ---: | ---: | --- |
| `chunked_binary` | 0 | 1,033,448 | `900x900` |
| `packed4_0` | 1,033,448 | 1,438,464 | `900x900` |
| `packed4_1` | 1,438,464 | 1,451,980 | `900x30` or `30x30x30` |

The known layers consume the full `1,451,980` byte input:

```text
section_count: 3
known_section_count: 3
residual_span_count: 0
dimensioned_array_candidate_count: 0
coordinate_like_candidate_count: 0
cross_layer_reference_candidate_count: 0
```

Conclusion:

```text
unclassified_anchor_candidates_found: false
node_world_transform: unproven
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

This closes the current "unclassified residual span" route for the observed structural framing. It does not prove gameplay semantics, does not prove node/world transform, does not approve a third runtime probe, and does not approve mutation of `packed4_1`, `packed4_0`, `chunked_binary`, regions, collision, pathing, spawns, or visual sync.

## Q2s MapSetting Route Decision Gate

Question:

```text
Can the project proceed to gameplay map editing now, or must it choose a different route?
```

Result on 2026-07-01: gameplay map editing remains blocked. `docs/q2s_map_setting_route_decision.md` records the route decision and the allowed next routes.

The generated status matrix is repository-external:

```text
D:\tfm2_q2a_evidence\q2s_map_setting_route_decision\q2s_status_matrix.json
```

Status:

```text
q2_map_setting_route_status: blocked_pending_runtime_anchor
node_world_transform: unproven
semantic_safety: not_proven
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
recommended_next_route: choose_visual_only_deliverable_or_runtime_anchor_spike
```

Route A:

```text
visual-only LOL-like map skin / concept mod
allowed: background_5v5, minimap_5v5_bg, visual-only layers after separate QA, concept docs
forbidden: map_setting, collision/path/spawn, brush gameplay, objective placement, AI route edits
```

Route B:

```text
runtime anchor / instrumentation spike
must prove: node_world_transform, field semantic proof, one small local reversible effect
must not mix with: visual-only deliverable, map_setting mutation, collision/path/spawn edits
```

Conclusion:

```text
Q2 map_setting gameplay editing is blocked pending runtime anchor and semantic field proof.
The next PR should choose either Route A visual-only deliverable or Route B runtime-anchor spike.
```

This is a route-decision gate only. It does not generate any runtime asset, does not approve a third runtime probe, and does not approve mutation of `packed4_1`, `packed4_0`, `chunked_binary`, regions, collision, pathing, spawns, or visual sync.

## Route A Visual-Only Background Skin Gate

Question:

```text
Can Route A produce a user-visible package without touching gameplay data?
```

Result: package prepared and reduced-obstacle runtime QA passed. `docs/visual_only_lol_map_skin.md` records the visual-only scope, and `docs/visual_only_runtime_qa.md` records the live 5v5 QA evidence.

Active override remains exactly:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
```

The image-gen source and generated runtime background skin are:

```text
assets/visual/lol_skin/background_5v5_imagegen_source.png
size: 1254x1254
sha256: a5dc8dd8e50b007559c3571266481ddbaefb6655b4c95c433796500d2a496436
```

```text
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/background_5v5.png
size: 1280x1280
sha256: 7c0c6dfca623436c8f0d267161ed4f135987e1bcdff39dfcb694ab3bb2b80c81
```

Still not enabled:

```text
map_setting
collision/path/spawn
brush gameplay
objective placement
AI route edits
```

Optional minimap candidate:

```text
minimap_5v5_bg candidate: prepared, not enabled by default
optional runtime QA: pass when temporarily staged in installed copy
default override: false
```

Conclusion:

```text
Route A background-only visual skin package: prepared
runtime QA: pass for reduced-obstacle background version
gameplay map editing: still not allowed
```

This gate prepares and QA-checks a cosmetic background package only. It does not prove gameplay semantics, does not approve minimap override, does not approve a third runtime probe, and does not approve mutation of `map_setting`, regions, collision, pathing, spawns, or visual sync.

## Route A Visual-Only Runtime QA

Question:

```text
Can the reduced-obstacle background-only skin display correctly in live 5v5 without staging gameplay data?
```

Result on 2026-07-02: pass for visual-only background runtime display. `docs/visual_only_runtime_qa.md` records the QA evidence.

Installed package checks:

```text
installed background_5v5 sha256: 7c0c6dfca623436c8f0d267161ed4f135987e1bcdff39dfcb694ab3bb2b80c81
map_setting override installed: false
mods\tfm2_lol_map_spike\setting\map_setting.map_setting exists: false
minimap override installed: false
forbidden override matches for minimap|map_setting|setting: 0
```

Runtime evidence summary:

```text
entered live 5v5: true
background displayed correctly: true
heroes, minions, towers, UI readable: true
original minimap remained active: true
loader log: not available / not captured
```

Repository-external evidence:

```text
D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_runtime_summary.json
size: 4,851
sha256: fb077c667ad56cbfbf196bad1bc4f9e64559bafbd18906245b151304ffeb7edd
```

Conclusion:

```text
Visual-only LOL-like Background Runtime QA Pass
gameplay data modified: false
map_setting override installed: false
minimap override installed: false
gameplay map editing: still blocked
```

This QA pass does not prove gameplay map editing, does not approve minimap override, and does not approve collision, pathing, spawn, brush gameplay, objective, AI-route, or `map_setting` edits.

## Route A Optional Minimap Runtime QA

Question:

```text
Can the optional minimap_5v5_bg candidate display correctly in live 5v5 when temporarily staged in the installed copy?
```

Result on 2026-07-02: pass for optional visual minimap runtime display. `docs/visual_only_minimap_runtime_qa.md` records the QA evidence.

Temporary installed-copy overrides during QA:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
asset/base/aseprite_resources/ingame/5v5/minimap_5v5_bg
```

Installed asset checks during QA:

```text
background_5v5 sha256: 7c0c6dfca623436c8f0d267161ed4f135987e1bcdff39dfcb694ab3bb2b80c81
minimap_5v5_bg sha256: b3040d6301fc1e0d8d3431adb97ed3535cebbd674c17cc0d56772b20e56fb6bf
map_setting override installed: false
mods\tfm2_lol_map_spike\setting\map_setting.map_setting exists: false
```

Runtime evidence summary:

```text
entered live 5v5: true
minimap candidate displayed: true
background displayed correctly: true
heroes, minions, towers, UI readable: true
camera frame readable on minimap: true
loader log: not available / not captured
```

Repository-external evidence:

```text
D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\minimap_runtime_summary.json
size: 4,998
sha256: c146da5ca90e31d41748bc3e0bc17dcdf2b5cba94e768d9b76eb530b69d3d872
```

Post-QA restore:

```text
installed package restored to background-only: true
minimap_5v5_bg.png exists in installed mod: false
map_setting.map_setting exists in installed mod: false
forbidden override matches for minimap|map_setting|setting: 0
```

Conclusion:

```text
Optional Minimap Visual Runtime QA Pass
default minimap override enablement: false
gameplay data modified: false
map_setting override installed: false
gameplay map editing: still blocked
```

This QA pass does not enable minimap override by default, does not prove gameplay map editing, and does not approve collision, pathing, spawn, brush gameplay, objective, AI-route, or `map_setting` edits.

## Route A Visual Detail Asset Inventory

Question:

```text
Which existing visual resources can be investigated for future LOL-like cosmetic skin work without entering gameplay map editing?
```

Result on 2026-07-02: inventory completed, no new runtime override enabled. `docs/visual_map_detail_asset_inventory.md` records the inventory.

Repository-external evidence:

```text
D:\tfm2_q2a_evidence\visual_map_detail_asset_inventory\visual_override_surface_inventory.json
size: 445,480
sha256: f8de752281550d1f18e6e6475e1793a305ef701b5ef9f47601fcf2e7c3efa03a
```

Inventory summary:

```text
total image candidates: 565
native/extracted reference candidates: 45
runtime/probe screenshots: 408
unclassified image candidates: 112
```

Candidate visual surfaces:

| Category | Candidate | Native reference | Default enabled | Risk | Next PR |
| --- | --- | --- | --- | --- | --- |
| Background | `background_5v5` | yes, `1280x1280` | yes | low | completed |
| Terrain wall | `wall_5v5` | yes, `1280x1280` | no | medium | PR #34 |
| Front wall | `wall_5v5_front` | yes, `1280x1280` | no | medium | PR #34 |
| Bush visual | `bush_5v5` | yes, `1280x1280` | no | high | PR #35 |
| Minimap | `minimap_5v5_bg` | yes, `320x320` | no | medium | PR #36 |
| Tower / crystal / base | actor or atlas candidates | yes | no | high | PR #37 |
| Jungle / neutral monsters | actor or atlas candidates | yes | no | high | PR #39 |

Conclusion:

```text
visual_detail_inventory_result: completed
default_runtime_package_changed: false
map_setting_override_installed: false
minimap_default_enabled: false
gameplay_data_modified: false
map_editing_allowed: false
```

This inventory does not replace walls, bushes, towers, crystals, jungle monsters, or minimap defaults. It only defines the next Route A investigation order. Gameplay map editing remains blocked.

## Stop Conditions

- If the game does not recognize `tfm2_lol_map_spike`, fix metadata or install layout before touching assets.
- If the game recognizes the mod but the background does not change, fix `mod.override_info` or asset path resolution before adding more layers.
- If a visual-only probe affects pathing or AI, stop and record the regression before any map data mutation.
- If `map_setting` equivalent remap fails, do not build a full map exporter. The project needs either a decoded loader-compatible asset pipeline or an SDK/API change.
