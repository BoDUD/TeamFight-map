# Visual-Only Minimap Candidate

This document records a Route A minimap visual candidate. The candidate is not enabled by default and has not received runtime QA. It is a repository asset for later review only.

## Result

```text
Minimap candidate prepared, not enabled.
minimap_5v5_bg override installed: false
background_5v5 override remains enabled: true
map_setting override installed: false
gameplay data modified: false
runtime QA performed: false
```

This PR does not approve the minimap override by default. A separate runtime QA PR must stage the candidate locally, verify HUD readability and direction consistency, and continue to keep `map_setting` and gameplay data out of the package.

## Native Size Reference

The native minimap background reference was read from repository-external original resource evidence:

```text
D:\tfm2_q2a_evidence\map_setting_layer_inspection\original_assets\minimap_5v5_bg.png
size: 320x320
mode: RGBA
size_bytes: 19,467
sha256: d14bb58ce5bab68a2ce747efe6e07b7978049e669201fdb2698e1d0cc77d12b1
```

The same SHA-256 was also present in the Q2c-1 transform validation and offline runtime anchor discovery evidence directories. No original minimap payload is committed to the repository.

## Candidate Assets

Image-gen source:

```text
assets/visual/lol_skin/minimap_5v5_bg_imagegen_source.png
size: 1254x1254
mode: RGB
size_bytes: 2,474,066
sha256: ef1d3fc2c7be326fa8b083fbcff4c65326e418e64483dc708e4b1a5f88dc871b
```

Deterministic candidate output:

```text
assets/visual/lol_skin/minimap_5v5_bg_candidate.png
size: 320x320
mode: RGBA
size_bytes: 410,018
sha256: b3040d6301fc1e0d8d3431adb97ed3535cebbd674c17cc0d56772b20e56fb6bf
```

The candidate uses a square, muted, LOL-like minimap visual language with a soft river band, abstract lane corridors, blue/red corner tint, and dark obstacle silhouettes. It deliberately contains no text, labels, logos, champion icons, minion icons, tower icons, objective icons, or UI controls.

## Runtime Package Boundary

The default runtime package remains background-only:

```text
mods/tfm2_lol_map_spike/mod.override_info contains:
asset/base/aseprite_resources/ingame/5v5/background_5v5
```

The default runtime package does not contain:

```text
asset/base/aseprite_resources/ingame/5v5/minimap_5v5_bg
asset/base/setting/map_setting
setting/map_setting.map_setting
```

The generated minimap candidate is intentionally not copied to:

```text
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/minimap_5v5_bg.png
```

## Future QA Gate

A later PR may run optional minimap runtime QA. That PR must verify:

```text
minimap_5v5_bg displays in the HUD correctly
orientation is not misleading
routes, bases, walls, objectives, and camera frame remain readable
background_5v5 still displays correctly
map_setting override installed: false
gameplay data modified: false
```

If the minimap candidate appears misleading in HUD scale, the candidate should be revised or left disabled. It must not be treated as gameplay map proof.

## Still Forbidden

This candidate does not approve:

```text
map_setting mutation
packed4_0 mutation
packed4_1 mutation
third chunked_binary runtime probe
collision/path/spawn editing
brush gameplay mask editing
objective placement editing
AI route editing
formal LOL gameplay map export
```

Gameplay map editing remains blocked pending independent node/world transform proof and semantic field proof.
