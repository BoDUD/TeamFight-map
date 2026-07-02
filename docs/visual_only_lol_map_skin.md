# Visual-Only LOL-Like Map Skin

This package is a non-gameplay cosmetic map skin for Teamfight Manager 2. It uses the proven visual asset override route and intentionally avoids all `map_setting` gameplay data.

## Scope

The default visual package currently includes:

```text
assets/visual/lol_skin/background_5v5_imagegen_source.png
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/background_5v5.png
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/wall_5v5.png
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/wall_5v5_front.png
tools/build_runtime_spike_assets.py
```

Active runtime overrides:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5_front
```

The skin uses an image-gen bitmap source, then the build tool normalizes it into a deterministic native runtime PNG:

```text
background_5v5_imagegen_source.png
size: 1254x1254
sha256: a5dc8dd8e50b007559c3571266481ddbaefb6655b4c95c433796500d2a496436
```

Runtime output:

```text
background_5v5.png
size: 1280x1280
sha256: 7c0c6dfca623436c8f0d267161ed4f135987e1bcdff39dfcb694ab3bb2b80c81
```

Wall/front-wall runtime outputs:

```text
wall_5v5.png
size: 1280x1280
sha256: af0ff21fba1b8f51e111752ed96b6cc9a6b313bac64c2c33fab6edcebe5b2c8b

wall_5v5_front.png
size: 1280x1280
sha256: 5d3e8a907e189f07ff220c0977f7303d05b30e2d9c0753de6a0eb2b51382399c
```

The wall and front-wall layers are locked to the native wall alpha coverage. They do not define new wall positions and do not change gameplay collision/pathing.

## Design Intent

The background keeps the native gameplay map shape and simulation data intact. It visually suggests a LOL-like map language without adding any gameplay meaning:

```text
hand-painted MOBA-like terrain
soft lane and river language
low-contrast jungle-color ground texture
soft blue/red base tint
decorative terrain detail as background art only
```

The art is deliberately painted as a background texture. It does not claim that any new terrain, brush, objective, spawn, path, or collision exists.

## Guardrails

This skin does not modify:

```text
map_setting
collision/path/spawn
brush gameplay
objective placement
AI route
packed4_0
packed4_1
chunked_binary
```

Current route status remains:

```text
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
```

## Minimap

`minimap_5v5_bg` is not enabled by default.

Reason:

```text
minimap_5v5_bg has optional installed-copy runtime QA;
default minimap enablement still needs a separate decision and default-package QA.
```

The repository now includes a disabled candidate recorded in:

```text
docs/visual_only_minimap_candidate.md
assets/visual/lol_skin/minimap_5v5_bg_imagegen_source.png
assets/visual/lol_skin/minimap_5v5_bg_candidate.png
```

The candidate is intentionally not copied into `mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/`, and `mod.override_info` does not contain `minimap_5v5_bg`.

A later visual PR may stage and QA the minimap candidate. That PR must still keep `map_setting` and gameplay data out of the runtime package.

## Runtime QA Result

The reduced-obstacle background version has passed a live visual-only runtime QA pass:

```text
Visual-only LOL-like Background Runtime QA Pass
```

Recorded in:

```text
docs/visual_only_runtime_qa.md
```

QA confirmed:

```text
background_5v5 override displays in live 5v5
mod.override_info does not contain map_setting
mods/tfm2_lol_map_spike/setting/map_setting.map_setting does not exist
heroes, minions, towers, UI, and original minimap remain readable
```

Wall/front-wall optional installed-copy QA has also passed, and the default-package enablement decision is recorded in `docs/visual_only_wall_terrain_default_enablement.md`. Default-package runtime QA for the wall-enabled package is still pending.

These QA passes do not prove gameplay map editing and do not approve minimap default enablement, `map_setting`, collision, pathing, spawn, brush gameplay, objective, or AI-route edits.
