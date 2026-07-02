# TeamFight-map

Non-runtime graybox specification for the Teamfight Manager 2 LOL-like map refactor.

This repository stores the first design/specification layer as data plus validators:

- `data/map/tfm2_lol_like_map.json` is the normalized map layout.
- `docs/concept/tfm2_lol_like_map_imagegen_v1.png` is image-gen concept art for visual direction only.
- `tools/validate_map_design.py` checks the design-book constraints.
- `tools/build_graybox_map.py` renders the validation/debug graybox and topology preview.
- `docs/design_compliance.md` maps the implementation back to the design book.
- `docs/imagegen_prompt.md` records the prompt used for the generated map art.
- `mods/tfm2_lol_map_spike/` is the minimal runtime spike package for one-asset map override testing.
- `docs/runtime_map_loading_spike.md` records the runtime asset audit, test order, and open loader questions.
- `docs/map_setting_layer_characterization.md` records the Q2c read-only layer inspection and symmetric edge candidate.
- `docs/map_setting_transform_validation.md` records the Q2c-1 read-only semantic checks and pending `30x30` transform validation.
- `docs/runtime_node_anchor_probe_plan.md` records why background UV captures do not prove `map_setting` node/world transform and defines the next read-only gate.
- `docs/runtime_node_anchor_api_discovery.md` records the PR #8 SDK/API audit and independent read-only DLL probe guardrails.
- `docs/q2s_map_setting_route_decision.md` records the Q2 route decision: gameplay `map_setting` editing is blocked pending runtime anchor and semantic proof; the next route should be either visual-only deliverable or a separate runtime-anchor spike.
- `docs/visual_only_lol_map_skin.md` records the Route A non-gameplay background skin scope and runtime QA result.
- `docs/visual_only_runtime_qa.md` records the live 5v5 visual-only QA pass for the reduced-obstacle background skin.
- `docs/visual_only_minimap_candidate.md` records the Route A minimap candidate asset, which is not enabled by default.
- `docs/visual_only_minimap_runtime_qa.md` records optional installed-copy runtime QA for the minimap candidate.
- `docs/visual_map_detail_asset_inventory.md` inventories map-detail visual override surfaces for future Route A work without enabling new overrides.
- `docs/visual_only_wall_terrain_candidates.md` records the wall/front-wall visual candidates and their mask-preservation gate.
- `docs/visual_only_wall_terrain_runtime_qa.md` records optional installed-copy runtime QA for the wall/front-wall candidates.
- `docs/visual_only_wall_terrain_default_enablement.md` records the default-package decision to enable wall/front-wall visual overrides while keeping default-package QA pending.

## Build And Validate

```powershell
python -m pip install -r requirements-dev.txt
python .\tools\validate_map_design.py
python .\tools\build_graybox_map.py
python .\tools\build_runtime_spike_assets.py
python -m unittest discover -s tests
```

Generated validation previews are written to `assets/graybox/`. These are not the map art; they exist to make the coordinate data reviewable.

To install the runtime spike into a local Teamfight Manager 2 folder that contains this checkout:

```powershell
python .\tools\install_runtime_spike_mod.py --clean --enable-exclusive
```

To reproduce the completed local-only `map_setting` equivalent-remap test, pass an extracted original binary source. The source and staged copy stay outside the repository; the installed copy is written as `setting/map_setting.map_setting` so the mod asset scanner can index it as `asset/tfm2_lol_map_spike/setting/map_setting`:

```powershell
python .\tools\install_runtime_spike_mod.py `
  --clean `
  --enable-exclusive `
  --stage-map-setting-equivalent `
  --map-setting-source "D:\path\to\original\map_setting"
```

To reproduce the local byte-identical `map_setting` structural round trip, keep both the original input and re-encoded output outside the repository:

```powershell
python .\tools\map_setting_round_trip.py `
  --input "D:\path\to\original\map_setting" `
  --evidence-dir "D:\path\to\round_trip_evidence"
```

To reproduce the read-only Q2c `map_setting` layer inspection, keep the original input, extracted original assets, overlays, masks, and manifest outside the repository:

```powershell
python .\tools\map_setting_inspect.py `
  --input "D:\path\to\original\map_setting" `
  --bundle "D:\steam\steamapps\common\Teamfight Manager2\bundle.game_data" `
  --output-dir "D:\path\to\map_setting_layer_inspection"
```

To reproduce the read-only Q2c-1 semantic and transform validation, keep all extracted original assets, overlays, and probe evidence outside the repository:

```powershell
python .\tools\map_setting_validate_semantics.py `
  --input "D:\path\to\original\map_setting" `
  --bundle "D:\steam\steamapps\common\Teamfight Manager2\bundle.game_data" `
  --output-dir "D:\path\to\map_setting_transform_validation"
```

To stage the generated coordinate grid as a visual-only background probe in the installed local mod copy:

```powershell
python .\tools\install_runtime_spike_mod.py `
  --clean `
  --enable-exclusive `
  --stage-background-source "D:\path\to\map_setting_transform_validation\runtime_grid_probe.png"
```

To audit the public runtime node-anchor API surface without installing any gameplay or asset override:

```powershell
python .\tools\audit_runtime_node_anchor_api.py `
  --sdk-dir "D:\steam\steamapps\common\Teamfight Manager2\mod-sdk" `
  --include-adjacent-rift-source `
  --output "D:\path\to\runtime_node_anchor_probe\runtime_node_anchor_api_audit.json"
```

To stage the independent read-only DLL anchor probe after building it locally:

```powershell
python .\tools\install_runtime_anchor_probe.py `
  --game-root "D:\steam\steamapps\common\Teamfight Manager2" `
  --dll "D:\local-build\runtime_node_anchor_probe.dll" `
  --enable-exclusive
```

To reproduce the Q2S route-decision status matrix:

```powershell
python .\tools\summarize_spike_status.py `
  --output "D:\tfm2_q2a_evidence\q2s_map_setting_route_decision\q2s_status_matrix.json"
```

To reproduce the Route A map-detail visual surface inventory, keep the metadata output outside the repository:

```powershell
python .\tools\inventory_visual_override_surfaces.py `
  --game-root "D:\steam\steamapps\common\Teamfight Manager2" `
  --output-dir "D:\tfm2_q2a_evidence\visual_map_detail_asset_inventory"
```

The visual concept reference is stored at:

```text
docs/concept/tfm2_lol_like_map_imagegen_v1.png
```

## Runtime Status

This is not yet a playable Teamfight Manager 2 gameplay map mod. The repository includes a visual-only spike package with `mod.mod_info` and `mod.override_info`, and it replaces `asset/base/aseprite_resources/ingame/5v5/background_5v5`, `asset/base/aseprite_resources/ingame/5v5/wall_5v5`, and `asset/base/aseprite_resources/ingame/5v5/wall_5v5_front` with non-gameplay LOL-like visual skin layers.

It does not include runtime DLL hooks, game map data replacement, collision masks, walkable masks, brush gameplay masks, minimap export, spawn data, or an in-game navigation graph.

Earlier image-gen PNGs under `docs/concept/` remain concept art only. The active runtime skin uses project-local source assets normalized by `tools/build_runtime_spike_assets.py` into deterministic cosmetic `background_5v5`, `wall_5v5`, and `wall_5v5_front` overrides. Gameplay map assets would still need proven layered ground, water, wall, decoration, brush visual, brush gameplay mask, collision/walkable mask, minimap, entity spawn data, and navigation graph from one authoritative map source.

Do not start formal gameplay map texture, collision mask, pathing, spawn, brush gameplay, objective-placement, or exporter work yet. The Q2 `map_setting` spike has proved visual override, loader takeover, byte-identical structural round trip, and bounded two-byte loader probes, but it has not proved `chunked_binary`, `packed4_0`, or `packed4_1` gameplay semantics, and it has not proved node/world transform.

Current route decision:

```text
q2_map_setting_route_status: blocked_pending_runtime_anchor
node_world_transform: unproven
semantic_safety: not_proven
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
```

The next route should be chosen explicitly:

- Route A: build a visual-only LOL-like map skin / concept mod using proven visual asset override paths. This must not include `map_setting`, collision, pathing, spawns, brush gameplay, objectives, or AI-route edits.
- Route B: run a separate runtime-anchor / instrumentation spike to prove node/world transform and field semantics before any further gameplay mutation.

The repository package must continue to keep `asset/base/setting/map_setting` out of `mods/tfm2_lol_map_spike/mod.override_info`; equivalent or mutated remaps are staged only in installed local game copies for explicitly reviewed probes.

Current visual package scope:

```text
background_5v5: enabled visual-only LOL-like skin
background runtime QA: pass for reduced-obstacle version
minimap_5v5_bg: candidate prepared and optional runtime QA passed; not enabled by default
map-detail visual inventory: completed
wall_5v5 / wall_5v5_front: default enabled visual-only layers
wall/front-wall optional runtime QA: pass when temporarily staged in installed copy
wall/front-wall default-package runtime QA: pending
map_setting: forbidden
```

## Scope

The current PR implements the MVP/graybox specification layer:

1. Keep the square outer frame, base anchors, three lane identity, and two pit centers.
2. Convert the northwest to southeast water band into a continuous tactical river axis.
3. Limit each major objective pit to two entrances.
4. Convert each half jungle into one main loop with two clear exits.
5. Reduce functional brush to 12 groups.
6. Keep Serpen as permanent growth and Morgard as timed pushing pressure.
