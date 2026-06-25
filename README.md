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

The visual concept reference is stored at:

```text
docs/concept/tfm2_lol_like_map_imagegen_v1.png
```

## Runtime Status

This is not yet a playable Teamfight Manager 2 runtime map mod. The repository now includes a diagnostic-only spike package with `mod.mod_info` and `mod.override_info`, but it replaces only `asset/base/aseprite_resources/ingame/5v5/background_5v5` with a solid-color probe image.

It does not include runtime DLL hooks, game map data replacement, collision masks, walkable masks, brush gameplay masks, minimap export, spawn data, or an in-game navigation graph.

The image-gen PNG is concept art only. Runtime map assets should be exported as layered ground, water, wall, decoration, brush visual, brush gameplay mask, collision/walkable mask, minimap, entity spawn data, and navigation graph from one authoritative map source.

Do not start formal map texture, collision mask, or exporter work until the runtime spike answers whether `map_setting` and related map data can be safely remapped.

## Scope

The current PR implements the MVP/graybox specification layer:

1. Keep the square outer frame, base anchors, three lane identity, and two pit centers.
2. Convert the northwest to southeast water band into a continuous tactical river axis.
3. Limit each major objective pit to two entrances.
4. Convert each half jungle into one main loop with two clear exits.
5. Reduce functional brush to 12 groups.
6. Keep Serpen as permanent growth and Morgard as timed pushing pressure.
