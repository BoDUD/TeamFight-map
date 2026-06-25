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

## Build And Validate

```powershell
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

The visual concept reference is stored at:

```text
docs/concept/tfm2_lol_like_map_imagegen_v1.png
```

## Runtime Status

This is not yet a playable Teamfight Manager 2 runtime map mod. The repository now includes a diagnostic-only spike package with `mod.mod_info` and `mod.override_info`, but it replaces only `asset/base/aseprite_resources/ingame/5v5/background_5v5` with a solid-color probe image.

It does not include runtime DLL hooks, game map data replacement, collision masks, walkable masks, brush gameplay masks, minimap export, spawn data, or an in-game navigation graph.

The image-gen PNG is concept art only. Runtime map assets should be exported as layered ground, water, wall, decoration, brush visual, brush gameplay mask, collision/walkable mask, minimap, entity spawn data, and navigation graph from one authoritative map source.

Do not start formal map texture, collision mask, or exporter work yet. Q2a proves the loader can read a byte-equivalent local `map_setting` override, and Q2b proves a structural decode/re-encode can be byte-identical, but safe modification still requires one tiny reversible data mutation. The repository package must continue to keep `asset/base/setting/map_setting` out of `mods/tfm2_lol_map_spike/mod.override_info`; the equivalent remap is staged only in the installed local game copy.

## Scope

The current PR implements the MVP/graybox specification layer:

1. Keep the square outer frame, base anchors, three lane identity, and two pit centers.
2. Convert the northwest to southeast water band into a continuous tactical river axis.
3. Limit each major objective pit to two entrances.
4. Convert each half jungle into one main loop with two clear exits.
5. Reduce functional brush to 12 groups.
6. Keep Serpen as permanent growth and Morgard as timed pushing pressure.
