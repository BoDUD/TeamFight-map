# Visual-Only Default Wall Terrain Runtime QA

This document records live 5v5 runtime QA for the default visual-only package after `wall_5v5` and `wall_5v5_front` were promoted into the repository default package.

## Result

```text
Visual-only Default Wall Terrain Package Runtime QA Pass

default package runtime QA: pass
background_5v5 override: pass
wall_5v5 override: pass
wall_5v5_front override: pass
minimap_5v5_bg default override installed: false
map_setting override installed: false
gameplay data modified: false
default package changed in this PR: false
```

This QA proves only that the default cosmetic package can be clean-installed and displayed in live 5v5 with background, wall, and front-wall visual overrides active. It does not prove gameplay map editing, does not approve minimap default enablement, and does not approve `map_setting`, collision, pathing, spawn, brush gameplay, objective, or AI-route edits.

## Default Package Under Test

The installed package was created from the repository default package with:

```powershell
python .\tools\install_runtime_spike_mod.py `
  --game-root "D:\steam\steamapps\common\Teamfight Manager2" `
  --clean `
  --enable-exclusive
```

Installed override keys:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5_front
```

Installed asset hashes:

```text
background_5v5 sha256:
7c0c6dfca623436c8f0d267161ed4f135987e1bcdff39dfcb694ab3bb2b80c81

wall_5v5 sha256:
af0ff21fba1b8f51e111752ed96b6cc9a6b313bac64c2c33fab6edcebe5b2c8b

wall_5v5_front sha256:
5d3e8a907e189f07ff220c0977f7303d05b30e2d9c0753de6a0eb2b51382399c
```

Negative checks:

```text
mods\tfm2_lol_map_spike\aseprite_resources\ingame\5v5\minimap_5v5_bg.png exists: false
mods\tfm2_lol_map_spike\setting\map_setting.map_setting exists: false
map_setting override installed: false
gameplay data modified: false
```

## Runtime Observation

Observed in live 5v5:

```text
entered live 5v5: true
background displayed: true
wall_5v5 displayed: true
wall_5v5_front displayed: true
heroes, minions, towers, UI readable: true
no obvious new walkable path visual: true
no obvious new blocked path visual: true
no obvious debug collision mask visual: true
minimap default override installed: false
map_setting override installed: false
gameplay data modified: false
loader log: not available / not captured
```

The visual check covered early in-game, midlane, river/center, jungle, and tower/base-adjacent views. The default wall/front-wall layers remained visually aligned with existing wall coverage and did not show an obvious new pathing or collision cue in the captured views.

## Repository-External Evidence

Evidence is stored outside the repository:

```text
D:\tfm2_q2a_evidence\visual_default_wall_runtime_qa\
```

Evidence files:

| Evidence | Size | SHA-256 |
| --- | ---: | --- |
| `default_wall_runtime_setup_manifest.json` | 2,236 | `40df02be01489164a1cfd7d57b095670ddf57bf2219e9117806831faaaf08201` |
| `default_wall_runtime_override_info.txt` | 548 | `8f7351560072711bcd6a6dc078877a210782f1b94f117cafe774144642dfb9a1` |
| `default_wall_runtime_map_setting_absence.txt` | 10 | `f07989c548da10e199e8b420ed198c2ae78ff5648ccd84142d5d81a66aabd3a2` |
| `default_wall_runtime_minimap_absence.txt` | 10 | `f07989c548da10e199e8b420ed198c2ae78ff5648ccd84142d5d81a66aabd3a2` |
| `default_wall_runtime_ingame_0030.png` | 936,792 | `9d14f39a64470537df268c4bb3641741e0d0250bef3c63d3aa1df68e8fcc8ae4` |
| `default_wall_runtime_midlane.png` | 1,189,292 | `24b781b7d854fb067304128bfac00500213ae274930e10ddb097dad82f41235c` |
| `default_wall_runtime_river_center.png` | 1,190,105 | `d1052bf59a4b8c06aa5e2cad8a389f11cadfc5c96189a1e4d13dece0ca2cc81b` |
| `default_wall_runtime_jungle.png` | 1,456,191 | `b7ce9158293694c02179139018c858a4cf3dc3d733f6b2b2835872b765d11d65` |
| `default_wall_runtime_tower_base.png` | 1,085,115 | `ecdc99e6ce5527c9e5ad74532490da1dc168c056c35b49c07b7171c4f17ccfe4` |
| `default_wall_runtime_post_qa_override_info.txt` | 548 | `8f7351560072711bcd6a6dc078877a210782f1b94f117cafe774144642dfb9a1` |
| `default_wall_runtime_post_qa_map_setting_absence.txt` | 10 | `f07989c548da10e199e8b420ed198c2ae78ff5648ccd84142d5d81a66aabd3a2` |
| `default_wall_runtime_post_qa_minimap_absence.txt` | 10 | `f07989c548da10e199e8b420ed198c2ae78ff5648ccd84142d5d81a66aabd3a2` |
| `default_wall_runtime_summary.json` | 6,949 | `55b6318d12ea673c029261c18133b5bdb479daa65c62d535c119adc75a0e60ff` |

## Post-QA State

Post-QA installed-copy checks still showed the default visual-only package:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5_front
```

Still absent after QA:

```text
minimap_5v5_bg.png
setting/map_setting.map_setting
asset/base/setting/map_setting
```

## Boundary

This QA pass does not approve:

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
