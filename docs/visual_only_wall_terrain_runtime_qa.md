# Visual-Only Wall Terrain Runtime QA

This document records optional installed-copy runtime QA for the Route A wall and terrain visual candidates. A later decision promotes these candidates into the default visual-only package; that decision still requires a separate default-package runtime QA pass.

## Result

```text
Optional Wall Terrain Visual Runtime QA Pass

wall_5v5 override: pass when temporarily staged in installed copy
wall_5v5_front override: pass when temporarily staged in installed copy
background_5v5 override: pass
map_setting override installed: false
minimap default override installed: false
gameplay data modified: false
default runtime package changed by this QA PR: false
later default wall/front-wall enablement: accepted
default-package runtime QA: pending
```

This QA proves only that the `wall_5v5` and `wall_5v5_front` visual candidates can be temporarily staged in a local installed copy and displayed in live 5v5 with the current background skin. It does not by itself prove the default package has been QA-passed, does not prove gameplay map editing, does not approve collision/path/spawn/brush/objective/AI edits, and does not approve `map_setting` mutation.

## Temporary Staging

At the time of this optional QA, the repository default package remained background-only. For this QA only, the installed local copy temporarily contained these visual overrides:

```text
asset/base/aseprite_resources/ingame/5v5/background_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5
asset/base/aseprite_resources/ingame/5v5/wall_5v5_front
```

Installed asset hashes during QA:

```text
background_5v5 sha256:
7c0c6dfca623436c8f0d267161ed4f135987e1bcdff39dfcb694ab3bb2b80c81

wall_5v5 sha256:
af0ff21fba1b8f51e111752ed96b6cc9a6b313bac64c2c33fab6edcebe5b2c8b

wall_5v5_front sha256:
5d3e8a907e189f07ff220c0977f7303d05b30e2d9c0753de6a0eb2b51382399c
```

Safety checks during staging:

```text
map_setting.map_setting exists: false
minimap override installed: false
map_setting override installed: false
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

The visual check covered early in-game, midlane, river, jungle, and tower/base-adjacent views. The wall candidates remained visually aligned with existing wall coverage and did not show an obvious new pathing or collision cue in the captured views.

## Repository-External Evidence

Evidence is stored outside the repository:

```text
D:\tfm2_q2a_evidence\visual_only_wall_runtime_qa\
```

Evidence files:

```text
wall_runtime_stage_manifest.json
size: 2,030
sha256: becc4145f0152e984529e1250dfd85498cb8ceeec05b42182ffe79bd07e16109

wall_runtime_override_info.txt
size: 534
sha256: ac0ce7ad90cf851841d4ea01f2ff68207bd348763baa097d0c5156546cfbe22a

wall_runtime_map_setting_absence.txt
size: 6
sha256: 7fc755fadc1b31a6696b8ed57c69d2bfc37f5457735c8fcfae31fcbd7bba97d5

wall_runtime_ingame_0030.png
size: 1,000,718
sha256: ad84961c8714199b8afb1162dfca8a789ca40d1293738b3e5eab46ede175b0a4

wall_runtime_midlane.png
size: 1,215,213
sha256: 6062c97cd98e03ec57fc6c76309be72f9c62b9ea02c9fe19f117cb6d2b37cc4d

wall_runtime_river.png
size: 1,097,255
sha256: 38f33a422a4fd9579de5560b0d37631f9a8eec7913e0f12e94129a9be594996d

wall_runtime_jungle.png
size: 1,150,916
sha256: c6e405e23f311875451552536c3762e58c7dcffcc5e498d6df87128b3be9be17

wall_runtime_base_or_tower.png
size: 1,056,642
sha256: e998a3f87627271444bc6c7844d5fb78ae15a3fe794dde92989087be7666219d

wall_runtime_summary.json
size: 4,065
sha256: 4fa5bb32686586cc9d0dcce2de82428ac6ebf6bc08998cbdbc83220c9a032242
```

## Post-QA Restore

After QA, the installed local copy was restored with `tools/install_runtime_spike_mod.py --clean --enable-exclusive`.

Post-restore checks:

```text
installed package restored to background-only: true
wall_5v5.png exists in installed mod: false
wall_5v5_front.png exists in installed mod: false
map_setting.map_setting exists in installed mod: false
forbidden override matches for wall|minimap|map_setting|setting: 0
```

Post-restore evidence:

```text
wall_runtime_post_restore_override_info.txt
size: 184
sha256: 9c6907b3b268be654a2e07ca10277491a6512ac745fe8c340e84ed1047f3011d

wall_runtime_post_restore_wall_absence.txt
size: 12
sha256: 6610d3d9d7e326f3941a1a9e130da0f795dd6b7ce5492eae3f8c848136387306

wall_runtime_post_restore_map_setting_absence.txt
size: 6
sha256: 7fc755fadc1b31a6696b8ed57c69d2bfc37f5457735c8fcfae31fcbd7bba97d5
```

## Boundary

This QA does not approve:

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
