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

The visual concept reference is stored at:

```text
docs/concept/tfm2_lol_like_map_imagegen_v1.png
```

## Runtime Status

This is not yet a playable Teamfight Manager 2 runtime map mod. The repository now includes a diagnostic-only spike package with `mod.mod_info` and `mod.override_info`, but it replaces only `asset/base/aseprite_resources/ingame/5v5/background_5v5` with a solid-color probe image.

It does not include runtime DLL hooks, game map data replacement, collision masks, walkable masks, brush gameplay masks, minimap export, spawn data, or an in-game navigation graph.

The image-gen PNG is concept art only. Runtime map assets should be exported as layered ground, water, wall, decoration, brush visual, brush gameplay mask, collision/walkable mask, minimap, entity spawn data, and navigation graph from one authoritative map source.

Do not start formal map texture, collision mask, or exporter work yet. Q2a proves the loader can read a byte-equivalent local `map_setting` override, Q2b proves a structural decode/re-encode can be byte-identical, Q2c has characterized a read-only symmetric edge candidate, and Q2c-1 shows that the candidate still needs independent runtime node/world anchoring because direction-code and offline transform results are ambiguous. PR #8 checked the public SDK/source surface and found no sufficient node/world anchor API, so candidate `369-370` remains blocked. Safe modification still requires a separate tiny reversible data mutation with A/B/A runtime proof after anchoring is solved. The repository package must continue to keep `asset/base/setting/map_setting` out of `mods/tfm2_lol_map_spike/mod.override_info`; the equivalent remap is staged only in the installed local game copy.

## Scope

The current PR implements the MVP/graybox specification layer:

1. Keep the square outer frame, base anchors, three lane identity, and two pit centers.
2. Convert the northwest to southeast water band into a continuous tactical river axis.
3. Limit each major objective pit to two entrances.
4. Convert each half jungle into one main loop with two clear exits.
5. Reduce functional brush to 12 groups.
6. Keep Serpen as permanent growth and Morgard as timed pushing pressure.
