# TFM2 LOL Runtime Node Anchor Probe

This is a diagnostic-only Teamfight Manager 2 mod package for runtime node/world anchor API discovery.

It is not a map replacement, does not include `mod.override_info`, and must not ship any `map_setting`, background, collision, pathing, spawn, or gameplay asset override.

## Purpose

The Q2c-1 background grid captures prove only that a visual `background_5v5` probe maps into the match scene. They do not prove that binary `map_setting` nodes `369` and `370` control that world location.

This package exists to load a read-only DLL probe and discover whether the public runtime SDK exposes an independent anchor surface such as entity positions, camera/viewport transforms, `visible_view`, `path`, world-to-screen conversion, or debug drawing.

## Guardrails

- Do not add `mod.override_info`.
- Do not add `setting/map_setting.map_setting`.
- Do not add `aseprite_resources/ingame/5v5/background_5v5.png`.
- Do not mutate `Scene`, `GameUI`, `Assets`, actors, AI, pathing, collision, camera, or assets.
- Do not use this package to stage `tfm2_lol_map_spike` visual probes.

## Install

Build the DLL from `native/runtime_node_anchor_probe/`, then stage it into the installed game copy:

```powershell
python .\tools\install_runtime_anchor_probe.py `
  --game-root "D:\steam\steamapps\common\Teamfight Manager2" `
  --dll "D:\local-build\runtime_node_anchor_probe.dll" `
  --enable-exclusive
```

The installer copies only this metadata package plus the supplied DLL into `mods/tfm2_lol_anchor_probe`, writes local evidence outside the repository, and enables the probe as the only active mod when requested.

## Expected Outcome

The current committed DLL skeleton proves only that a read-only extension can be built and can emit one external evidence file when loaded. It does not yet prove `map_setting_node_world_transform`.

If no public SDK anchor surface exists, the correct result is:

```text
runtime_node_anchor_api: unavailable_in_public_sdk
map_setting_node_world_transform: unproven
candidate_369_370: blocked
```
