# Visual-Only Wall And Terrain Candidates

This document records Route A wall and terrain visual candidates. The candidates are not enabled by default and have not received runtime QA.

## Result

```text
Wall / terrain visual candidates prepared, not enabled.

wall_5v5 override installed: false
wall_5v5_front override installed: false
background_5v5 override remains enabled: true
minimap default override: false
map_setting override installed: false
gameplay data modified: false
runtime QA performed: false
```

This PR adds candidate assets only. The candidates are position-locked to the existing wall visual layer coverage so they do not introduce new wall locations. It does not change collision, pathing, spawns, brush gameplay, objective placement, AI routes, or `map_setting`. It does not approve wall overrides by default.

## Native Reference

PR #33 found repository-external native or extracted references for both wall layers:

| Native asset | Native reference found | Native dimensions | Risk |
| --- | --- | --- | --- |
| `wall_5v5` | yes | `1280x1280` | medium |
| `wall_5v5_front` | yes | `1280x1280` | medium |

The original payload is not committed to the repository. It is used only as a size and route-planning reference.

## Candidate Assets

Full-frame stone material reference:

```text
assets/visual/lol_skin/wall_terrain_texture_reference.png
size: 1254x1254
mode: RGB
usage: material/style reference only, not a wall placement source
size_bytes: 2,557,535
sha256: 4d2f3a70db79a4059e6791d6066e33cc4bade8eb0bf51d7572d569b78ceffd94
```

Main wall position-locked source:

```text
assets/visual/lol_skin/wall_5v5_position_locked_source.png
size: 1280x1280
mode: RGBA
alpha_coverage_matches_native_reference: true
size_bytes: 546,997
sha256: f81921eea26f4b7bfea9b0ff2c6f1dcc13e6b76ed83b36f644645a321ee854ae
```

Main wall deterministic candidate:

```text
assets/visual/lol_skin/wall_5v5_candidate.png
size: 1280x1280
mode: RGBA
alpha_range: 0..224
size_bytes: 6,555,448
sha256: af0ff21fba1b8f51e111752ed96b6cc9a6b313bac64c2c33fab6edcebe5b2c8b
```

Front-wall position-locked source:

```text
assets/visual/lol_skin/wall_5v5_front_position_locked_source.png
size: 1280x1280
mode: RGBA
alpha_coverage_matches_native_reference: true
size_bytes: 90,187
sha256: 7240c91e6f5664026ffe470648d313b4d71573d6500f794e26ec77a62bbf8161
```

Front-wall deterministic candidate:

```text
assets/visual/lol_skin/wall_5v5_front_candidate.png
size: 1280x1280
mode: RGBA
alpha_range: 0..199
size_bytes: 6,555,448
sha256: 5d3e8a907e189f07ff220c0977f7303d05b30e2d9c0753de6a0eb2b51382399c
```

The free-layout wall art that informed this pass is treated only as a visual style reference. It is not used as a placement source because its wall positions do not match the native map. The committed wall candidates are instead clipped to the existing native wall-layer alpha coverage, with original low-contrast stone material applied inside that fixed mask. The source and candidate alpha masks preserve the existing wall/front-wall coverage exactly. `tools/build_runtime_spike_assets.py` tones the result for runtime readability and writes deterministic RGBA candidate PNGs.

Mask-preservation check:

```text
wall_5v5 native/reference nonzero pixels: 291,274
wall_5v5 candidate nonzero pixels: 291,274
wall_5v5 mask mismatch count: 0

wall_5v5_front native/reference nonzero pixels: 56,022
wall_5v5_front candidate nonzero pixels: 56,022
wall_5v5_front mask mismatch count: 0
```

## Visual Intent

Allowed visual direction:

```text
low-contrast stone wall segments
canyon / cliff-edge style
subtle moss and worn masonry
clearer terrain boundary language
consistent with the current reduced-obstacle background skin
```

Avoided visual direction:

```text
new walkable paths
new blocked paths
new grass or brush cues
new objective pit or jungle camp cues
hard debug-mask black outlines
copied League of Legends art, icons, logos, or texture fragments
```

## Runtime Package Boundary

The default runtime package remains background-only:

```text
mods/tfm2_lol_map_spike/mod.override_info contains:
asset/base/aseprite_resources/ingame/5v5/background_5v5
```

The default runtime package does not contain:

```text
asset/base/aseprite_resources/ingame/5v5/wall_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5_front
asset/base/aseprite_resources/ingame/5v5/minimap_5v5_bg
asset/base/setting/map_setting
setting/map_setting.map_setting
```

The wall candidates are intentionally not copied to:

```text
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/wall_5v5.png
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/wall_5v5_front.png
```

## Next Step

If these candidates are accepted, the next PR should be a separate optional installed-copy runtime QA:

```text
[visual] record optional wall terrain runtime QA
```

That QA should temporarily stage only:

```text
background_5v5
wall_5v5
wall_5v5_front
```

and verify live 5v5 readability, no loader warning, no visual confusion around walkable/non-walkable regions, default minimap still disabled, and no `map_setting` staged file.

## Still Forbidden

This candidate PR does not approve:

```text
default wall override enablement
map_setting mutation
packed4_0 mutation
packed4_1 mutation
third chunked_binary runtime probe
collision/path/spawn editing
brush gameplay mask editing
objective placement editing
AI route editing
formal gameplay map export
```

Gameplay map editing remains blocked pending independent node/world transform proof and semantic field proof.
