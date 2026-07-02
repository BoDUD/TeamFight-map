# Visual Map Detail Asset Inventory

This document records the Route A inventory for map-detail visual override surfaces. It is an investigation-only PR. It does not enable any new runtime override and does not modify gameplay data.

## Result

```text
visual_detail_inventory_result: completed
default_runtime_package_changed: false
map_setting_override_installed: false
minimap_default_enabled: false
gameplay_data_modified: false
map_editing_allowed: false
```

The inventory identifies likely visual surfaces for future LOL-like cosmetic work. It does not replace monsters, towers, crystals, bush visuals, wall layers, or minimap defaults. It does not approve `map_setting`, collision, pathing, spawn, brush gameplay, objective placement, AI-route, or packed4 edits.

## Evidence

Repository-external inventory output:

```text
D:\tfm2_q2a_evidence\visual_map_detail_asset_inventory\visual_override_surface_inventory.json
size: 445,480
sha256: f8de752281550d1f18e6e6475e1793a305ef701b5ef9f47601fcf2e7c3efa03a
```

Command:

```powershell
python .\tools\inventory_visual_override_surfaces.py `
  --game-root "D:\steam\steamapps\common\Teamfight Manager2" `
  --output-dir "D:\tfm2_q2a_evidence\visual_map_detail_asset_inventory"
```

Scan roots:

```text
D:\steam\steamapps\common\Teamfight Manager2\stage1b_evidence
D:\steam\steamapps\common\Teamfight Manager2\stage1c_evidence
D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence
D:\steam\steamapps\common\Teamfight Manager2\ModData
```

The scanner skips repository paths and runtime `mods` trees. It records metadata only: path, filename, size, image dimensions, SHA-256, suspected category, reference kind, and safety flags. No original payload is copied into the repository.

Summary:

```text
total image candidates: 565
native/extracted reference candidates: 45
runtime/probe screenshots: 408
unclassified image candidates: 112
```

Category counts:

| Category | Count |
| --- | ---: |
| Background | 3 |
| Brush visual | 95 |
| Jungle / neutral monsters | 6 |
| Minimap | 47 |
| Terrain / wall | 173 |
| Tower / crystal / base | 70 |
| Unknown | 171 |

## Surface Matrix

| Category | Asset candidate | Native reference found | Representative dimensions | Visual-only? | Default enabled? | Runtime QA needed? | Risk | Next PR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Background | `background_5v5` | yes | `1280x1280` | Proven visual-only background override | yes | no | low | completed |
| Terrain wall | `wall_5v5` | yes | `1280x1280` | Likely visual-only if replacing only the existing wall layer | no | yes | medium | PR #34 |
| Front wall | `wall_5v5_front` | yes | `1280x1280` | Likely visual-only if replacing only the existing front-wall layer | no | yes | medium | PR #34 |
| Bush visual | `bush_5v5` | yes | `1280x1280` | Visual-only only if the existing visual layer is replaced without changing gameplay brush masks | no | yes | high | PR #35 |
| Minimap | `minimap_5v5_bg` | yes | `320x320` | Candidate prepared and optional installed-copy QA passed | no | default-enable QA needed | medium | PR #36 |
| Tower | `tower` | yes | `23x24` | Unknown until actor or atlas surface is reviewed | no | yes | high | PR #37 |
| Crystal / base | `crystal / base` | yes | `54x30` | Unknown until actor or atlas surface is reviewed | no | yes | high | PR #37 |
| Jungle monsters | `monster / jungle objective actors` | yes | `1498x226` | Unknown; likely actor sprites or animation atlases, not background paint | no | yes | high | PR #39 |

## Interpretation

Terrain and wall resources are the safest next visual-detail candidates because `wall_5v5` and `wall_5v5_front` appear as existing visual layers. A future PR can propose candidate replacements, but it must not change collision, pathing, or `map_setting`.

Bush visuals are higher risk. The existing `bush_5v5` visual layer can be investigated, but Route A must not add, move, resize, or otherwise change gameplay brush masks.

The minimap candidate has optional installed-copy runtime QA, but it is still not enabled by default. A default enablement decision requires its own PR and a fresh default-package QA pass.

Tower, crystal, base, and jungle monster candidates appear to be actor or atlas-style resources. They need investigation before any replacement candidate is created. They should not be painted into the background skin.

## Recommended Follow-Ups

```text
PR #34  wall / stone / terrain visual candidates
PR #35  bush visual candidate, no gameplay brush edit
PR #36  minimap default enable decision + default-package QA
PR #37  tower / crystal visual asset investigation
PR #38  tower / crystal visual candidates if safe
PR #39  jungle monster visual asset investigation
PR #40  jungle monster visual candidates if safe
```

## Boundaries

Still forbidden:

```text
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
