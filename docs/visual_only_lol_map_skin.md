# Visual-Only LOL-Like Map Skin

This package is a non-gameplay cosmetic map skin for Teamfight Manager 2. It uses the proven visual asset override route and intentionally avoids all `map_setting` gameplay data.

## Scope

This PR updates only:

```text
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/background_5v5.png
tools/build_runtime_spike_assets.py
```

Active runtime override:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
```

The skin is generated deterministically at native size:

```text
background_5v5.png
size: 1280x1280
sha256: 53524fcd452ffe606a166e6bf6108c81f56069d9f190597a26f941ea1a3fa21a
```

## Design Intent

The background keeps the native gameplay map shape and simulation data intact. It visually suggests a LOL-like map language without adding any gameplay meaning:

```text
three clear lane bands
subtle diagonal river band
jungle-color visual quadrants
soft blue/red base tint
objective-pit decoration as background art only
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

`minimap_5v5_bg` is not enabled in this PR.

Reason:

```text
background_5v5 override has already been proven in live 5v5;
minimap_5v5_bg still needs separate visual-only QA before default enablement.
```

A later visual PR may add and QA a minimap candidate. That PR must still keep `map_setting` and gameplay data out of the runtime package.

## Runtime QA Plan

After this visual package is merged, run a separate visual-only QA PR:

```text
[visual] record LOL-like background skin runtime QA
```

QA should verify:

```text
mod only enables visual override
mod.override_info does not contain map_setting
5v5 can be entered
background skin is visible
heroes, minions, towers, minimap, and AI routes appear native/stable
no Override source not found warning
no Only 1/2 override applied warning
```

This QA should not stage or mutate `map_setting`.
