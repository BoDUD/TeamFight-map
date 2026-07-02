# Visual-Only Wall Terrain Default Enablement

This document records the Route A decision to enable the `wall_5v5` and `wall_5v5_front` visual overrides in the default repository package.

## Decision

```text
Wall / terrain default enablement: accepted

default package changed: true
background_5v5 default override: true
wall_5v5 default override: true
wall_5v5_front default override: true
minimap_5v5_bg default override: false
map_setting override installed: false
gameplay data modified: false
default-package runtime QA: pass
```

This PR promotes the previously prepared and optional-QA-passed wall/front-wall visual candidates into the default visual-only package. The follow-up default-package runtime QA is recorded separately in `docs/visual_only_wall_terrain_default_runtime_qa.md`.

## Evidence Used For The Decision

The wall/front-wall candidates have completed these prior gates:

```text
candidate assets prepared: true
wall_5v5 mask mismatch count: 0
wall_5v5_front mask mismatch count: 0
optional installed-copy runtime QA: pass
post-QA installed-copy restore: clean
```

The optional installed-copy runtime QA is recorded in:

```text
docs/visual_only_wall_terrain_runtime_qa.md
```

That QA temporarily staged `background_5v5`, `wall_5v5`, and `wall_5v5_front` in the installed copy, entered live 5v5, and checked early in-game, midlane, river, jungle, and tower/base-adjacent views. It did not enable wall overrides by default.

## Default Runtime Package

The default repository package now contains these visual overrides:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5_front
```

Runtime files:

```text
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/background_5v5.png
sha256: 7c0c6dfca623436c8f0d267161ed4f135987e1bcdff39dfcb694ab3bb2b80c81

mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/wall_5v5.png
sha256: af0ff21fba1b8f51e111752ed96b6cc9a6b313bac64c2c33fab6edcebe5b2c8b

mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/wall_5v5_front.png
sha256: 5d3e8a907e189f07ff220c0977f7303d05b30e2d9c0753de6a0eb2b51382399c
```

The default repository package still excludes:

```text
asset/base/aseprite_resources/ingame/5v5/minimap_5v5_bg
asset/base/setting/map_setting
setting/map_setting.map_setting
collision/path/spawn data
brush gameplay data
objective placement data
AI route data
```

## Completed Follow-Up

Default-package runtime QA has been recorded in:

```text
docs/visual_only_wall_terrain_default_runtime_qa.md
```

That QA installed the repository default package without manual installed-copy staging, entered live 5v5, and verified:

```text
background_5v5 displays
wall_5v5 displays
wall_5v5_front displays
minimap_5v5_bg is still not installed by default
map_setting.map_setting does not exist
heroes, minions, towers, UI remain readable
no obvious new walkable path visual
no obvious new blocked path visual
no debug collision-mask visual
```

## Boundary

This decision does not approve:

```text
minimap default override enablement
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
