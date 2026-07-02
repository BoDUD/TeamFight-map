# Optional Minimap Runtime QA

This document records the optional runtime QA for the Route A minimap visual candidate. The candidate was staged only in the local installed game copy. The default repository package remains background-only.

## Result

```text
Optional Minimap Visual Runtime QA Pass
minimap_5v5_bg override: pass when temporarily staged in installed copy
background_5v5 override: pass
map_setting override installed: false
gameplay data modified: false
default runtime package changed: false
```

This proves only that the optional cosmetic minimap candidate can display in the live 5v5 HUD when temporarily staged. It does not enable the minimap override by default, does not prove gameplay map editing, and does not approve `map_setting`, collision, pathing, spawn, brush gameplay, objective, or AI-route edits.

## Staging Scope

The starting installed package was clean `main` and background-only. For QA only, the installed copy was temporarily changed to include:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
asset/base/aseprite_resources/ingame/5v5/minimap_5v5_bg
```

The repository default `mods/tfm2_lol_map_spike/mod.override_info` was not changed.

Installed asset hashes during QA:

```text
background_5v5 sha256: 7c0c6dfca623436c8f0d267161ed4f135987e1bcdff39dfcb694ab3bb2b80c81
minimap_5v5_bg sha256: b3040d6301fc1e0d8d3431adb97ed3535cebbd674c17cc0d56772b20e56fb6bf
```

Negative checks during QA:

```text
mods/tfm2_lol_map_spike/setting/map_setting.map_setting exists: false
map_setting override installed: false
gameplay data modified: false
```

An initial local staging attempt wrote invalid installed override JSON and triggered a loader parse error before QA. The installed copy was clean reinstalled, re-enabled, and restaged with UTF-8 without BOM before the successful QA evidence recorded here.

## Runtime Observation

The game entered live 5v5 with both visual-only overrides active. Four runtime screenshots were captured:

| Evidence | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\minimap_runtime_ingame_0030.png` | 1,124,668 | `cd032ffae61b5f60d639763ee037af6c69347a0b129cd5bcc95242184cea6b88` |
| `D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\minimap_runtime_full_ui.png` | 1,126,042 | `dfe78accc28d602c6e0295db105007fce5356666d0658a180c6a56a47b19bcd6` |
| `D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\minimap_runtime_midlane.png` | 1,075,075 | `f22fda3c6dc8a0dbfe46d594557cbcf2b99a6d298ce24c8d98eacc513290a7b0` |
| `D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\minimap_runtime_river.png` | 1,199,338 | `b7d84dfe2d6c138a003d55017b0f07cf68df9a4f6c0cce945892f6e39c3d8770` |

Observed result:

```text
minimap candidate displayed: true
background displayed correctly: true
heroes, minions, towers, UI readable: true
camera frame readable on minimap: true
blue lower-left / red upper-right HUD convention visually consistent: true
loader warning after corrected staging: none observed
loader log: not available / not captured
```

The orientation observation is a visual HUD check only. It is not a `map_setting` node/world transform proof and does not approve gameplay map editing.

## Evidence Manifest

Repository-external evidence is stored under:

```text
D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\
```

Summary file:

```text
D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\minimap_runtime_summary.json
size: 4,998
sha256: c146da5ca90e31d41748bc3e0bc17dcdf2b5cba94e768d9b76eb530b69d3d872
```

Supporting staging evidence:

| Evidence | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\minimap_runtime_override_info.txt` | 365 | `521bcc8c5af779eff472aa4bc680b6bfda3c1fc20f5c543926a2138c9c021985` |
| `D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\minimap_runtime_map_setting_absence.txt` | 6 | `7fc755fadc1b31a6696b8ed57c69d2bfc37f5457735c8fcfae31fcbd7bba97d5` |
| `D:\tfm2_q2a_evidence\visual_only_minimap_runtime_qa\minimap_runtime_loader_log_excerpt.txt` | 41 | `9e67a1adaf12d9137813d35fb88e90bd93385c65aa65cf5d0f678cd90e2e41c4` |

## Post-QA Restore

After the screenshots and summary were captured, the installed local mod was restored to background-only:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
```

Restore checks:

```text
mods/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/minimap_5v5_bg.png exists: false
mods/tfm2_lol_map_spike/setting/map_setting.map_setting exists: false
forbidden override matches for minimap|map_setting|setting: 0
```

## Boundaries

This QA pass does not approve:

```text
default minimap override enablement
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
