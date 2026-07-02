# Visual-Only Background Runtime QA

This document records the runtime QA for the reduced-obstacle Route A background skin. It is a visual-only check. It does not modify `map_setting`, minimap resources, collision, pathing, spawn data, brush gameplay, objective placement, or AI routes.

## Result

```text
Visual-only LOL-like Background Runtime QA Pass
background_5v5 override: pass
reduced-obstacle background version: pass
map_setting override installed: false
minimap override installed: false
gameplay data modified: false
collision/path/spawn modified: false
brush gameplay modified: false
objective placement modified: false
```

This proves only that the cosmetic `background_5v5` override displays correctly in a live 5v5 match with the current visual package. It does not prove gameplay map editing, does not approve a minimap override, and does not approve `map_setting` or collision/path/spawn/brush/objective edits.

## Installed Package Check

QA was run against the installed local spike mod after a clean install from `main`.

```text
repository head: f4e49db032f573e6ee70ac825a72a16fbfc487ef
installed background_5v5 sha256: 7c0c6dfca623436c8f0d267161ed4f135987e1bcdff39dfcb694ab3bb2b80c81
```

Installed `mod.override_info` contains only:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
```

Negative checks:

```text
mods/tfm2_lol_map_spike/setting/map_setting.map_setting exists: false
forbidden override matches for minimap|map_setting|setting: 0
```

The runtime package therefore remained background-only during this historical QA pass. Later wall/front-wall default enablement and default-package runtime QA are tracked separately.

## Runtime Observation

The game entered live 5v5 with the reduced-obstacle background skin active. Four runtime screenshots were captured:

| Evidence | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_reduced_obstacle_ingame_0030.png` | 1,095,232 | `98696299d676fa5519e56a7bd1335a2841aac60fb91015b9e84d6ede2002e205` |
| `D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_reduced_obstacle_midlane.png` | 955,408 | `a1060b33f0d437f8743dba6d7e8721184bcf4907fb1636b8953586e1fd1f6d8b` |
| `D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_reduced_obstacle_river.png` | 1,074,295 | `034a6278a7aca0d9f903d92cfd85280351c3e2ab96cacfb2ea9e665e6e387061` |
| `D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_reduced_obstacle_jungle.png` | 1,124,378 | `11eca2c86f9964351ec31a4a97411d8e19be6e944f9948b26f88d3d262e24096` |

Observed result:

```text
background skin visible: true
heroes visible/readable: true
minions visible/readable: true
towers visible/readable: true
UI visible/readable: true
minimap remained original: true
obvious misleading obstacle cues from the previous version: reduced
```

No loader-warning dialog was observed during this visual QA pass. A reliable loader log was not captured, so the evidence records:

```text
loader log: not available / not captured
```

## Evidence Manifest

Repository-external evidence is stored under:

```text
D:\tfm2_q2a_evidence\visual_only_runtime_qa\
```

Summary file:

```text
D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_runtime_summary.json
size: 4,851
sha256: fb077c667ad56cbfbf196bad1bc4f9e64559bafbd18906245b151304ffeb7edd
```

Supporting installation evidence:

| Evidence | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_stage_manifest.json` | 1,925 | `b3691a718700c4de424b3b68b01a20f18b134c7b7a878be1edbca115421a26a5` |
| `D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_override_info.txt` | 190 | `917e8462f7f2d0f68f799772dbc1ae94a31d53706e80d959330ba8961793e48f` |
| `D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_map_setting_absence.txt` | 7 | `b625e5139b05722842537c7016e2e78c22d36212eaeae63fce2b2005b7808f33` |
| `D:\tfm2_q2a_evidence\visual_only_runtime_qa\visual_only_loader_log_excerpt.txt` | 179 | `3fb255c7d1b936ab58e36ce7af0dca5375eaefcec86ddf47d1720ecfa756761c` |

## Boundaries

This QA pass does not approve:

```text
map_setting mutation
minimap override
third chunked_binary runtime probe
packed4_0 mutation
packed4_1 mutation
multi-edge or region mutation
collision/path/spawn editing
brush gameplay mask editing
objective placement editing
formal LOL gameplay map export
```

Gameplay map editing remains blocked pending independent node/world transform proof and semantic field proof.
