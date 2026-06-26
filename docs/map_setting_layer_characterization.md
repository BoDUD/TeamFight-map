# MapSetting Layer Characterization

Date: 2026-06-26

This is Q2c read-only semantic localization. It does not create a mutated `map_setting`, does not install a runtime override, and does not change gameplay fields.

## Reproduction

Run the inspector against the local original `map_setting` and keep every diagnostic output outside the repository:

```powershell
python .\tools\map_setting_inspect.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --bundle "D:\steam\steamapps\common\Teamfight Manager2\bundle.game_data" `
  --output-dir "D:\tfm2_q2a_evidence\map_setting_layer_inspection"
```

The tool writes:

```text
D:\tfm2_q2a_evidence\map_setting_layer_inspection\
  candidate_clearance_manifest.json
  candidate_nodes_on_minimap.png
  chunked_binary_values.png
  packed4_0_values.png
  packed4_0_value_0_mask.png ... packed4_0_value_15_mask.png
  packed4_1_slices\
  source_369_relation_mask_30x30.png
  target_370_relation_mask_30x30.png
  original_assets\
  overlays\
  layer_inspection_manifest.json
```

Evidence hashes:

```text
layer_inspection_manifest.json:      ef3d1ae47b0a75a8e27eb2c9df89c0f4ea76ac8725c22b4a64dde7504330ef78
candidate_clearance_manifest.json:  792a33f2c310b68e05e569e1088b3df81c3c3210b7ab26e1c18a8ebc917c0e3c
```

The extracted original assets, overlay images, and diagnostic masks are local evidence only. They must not be committed.

## Layer Findings

| Layer | Shape | Histogram | Current hypothesis | Mutation status |
| --- | ---: | --- | --- | --- |
| `chunked_binary` | `900x900` | `0: 703026`, `1: 106974` | Symmetric source-target relation over a `30x30` logical grid, most likely visibility or reachability. Because `transpose_mismatch_count` is `0`, it behaves like an undirected relation rather than a direct map texture. | Candidate layer for a symmetric edge probe only. A single-cell mutation would violate the observed invariant. |
| `packed4_0` | `900x900` | `0: 102437`, `1: 97875`, `2: 100737`, `3: 99689`, `4: 64638`, `5: 62108`, `6: 64280`, `7: 63526`, `15: 154710` | Likely a path or next-hop table over the same `30x30` source-target grid. Values `0-7` look direction-like and `15` looks sentinel-like, but this is not confirmed. | Do not use for the first mutation because a wrong path value is more likely to disturb AI or lane routing. |
| `packed4_1` | `27000` values | `0: 12094`, `1: 578`, `2: 753`, `3: 1280`, `4: 321`, `5: 262`, `6: 250`, `7: 278`, `8: 11184` | Unverified table. The inspector exports `30x30x30` candidate slices, but that shape is only a diagnostic view. | Excluded from first mutation target selection. |

Overlay checks used local copies of:

```text
wall_5v5
wall_5v5_front
bush_5v5
minimap_5v5_bg
background_5v5
```

The overlays do not show a direct pixel mask matching wall or bush art. Instead, the two `900x900` layers show repeated source-target matrix structure that lines up with the map only as graph-like relations. That supports a cautious `visible_view` / path-table hypothesis, not a confirmed terrain-category interpretation.

## Candidate Status

The selected structural candidate is an undirected edge, not a single cell:

```json
{
  "status": "needs_world_grid_validation",
  "candidate_unit": "undirected_edge",
  "layer": "chunked_binary",
  "edge": {
    "source_node": 369,
    "target_node": 370,
    "source_xy_30x30": [9, 12],
    "target_xy_30x30": [10, 12],
    "source_world": [31.666666666666668, 41.666666666666664],
    "target_world": [35.0, 41.666666666666664]
  },
  "cells": [
    {
      "logical_coordinate": [370, 369],
      "serialized_byte_offset": 427536,
      "old_value": 1,
      "new_value": 0
    },
    {
      "logical_coordinate": [369, 370],
      "serialized_byte_offset": 427573,
      "old_value": 1,
      "new_value": 0
    }
  ],
  "changed_cell_count": 2,
  "changed_byte_count": 2,
  "transpose_mismatch_count_before": 0,
  "transpose_mismatch_count_after_if_applied": 0,
  "risk_classification": "unverified",
  "rollback_source_sha256": "6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0"
}
```

This edge is chosen because it preserves the strongest observed invariant: the chunked matrix remains transpose-symmetric after the hypothetical two-cell edit. It is not yet approved for runtime mutation.

## Clearance Evidence

The inspector also writes:

```text
candidate_nodes_on_minimap.png
source_369_relation_mask_30x30.png
target_370_relation_mask_30x30.png
candidate_clearance_manifest.json
```

The clearance transform is explicitly unverified:

```text
30x30 node centers mapped linearly to normalized design coordinates
```

Under that assumption, the candidate has:

```text
source lane clearance: 18.856
target lane clearance: 16.499
nearest feature: GATE_BLUE_TOP_RIVER
minimum feature clearance: 7.401
risk classification: unverified
```

Because the nearest known design feature is still a jungle-to-river gate and because the original `map_setting` world/grid transform is not proven, this PR does not claim the edge is low traffic or safe. The next runtime mutation PR must either validate the world/grid transform against original-map anchors or explicitly accept this risk before staging a changed binary.

## Rollback Plan

A future mutation tool must:

1. Verify the input SHA-256 is exactly `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0`.
2. Write the mutated output outside the repository and never overwrite the original input, manifest, bundle, or hardlink/symlink aliases.
3. Change exactly the two listed `chunked_binary` cells at offsets `427536` and `427573`.
4. Prove `changed_cell_count == 2`, `changed_byte_count == 2`, `transpose_mismatch_count_before == 0`, and `transpose_mismatch_count_after == 0`.
5. Stage the mutated file only in the installed local mod copy for run B.
6. Restore the byte-equivalent original file for A2 from the SHA-256 baseline above.
7. Stop immediately on crash, load error, unit spawn abnormality, stuck lanes, AI route regression, broader-than-expected diff, or failed rollback.

Result of this PR: a symmetric edge candidate is characterized, but its runtime risk remains unverified. No Q2c loader mutation pass or semantic mutation pass is claimed.

Follow-up Q2c-1 is recorded in `docs/map_setting_transform_validation.md`. It confirms `chunked_binary` is not closure-like, but direction-code and offline transform checks remain ambiguous, so edge `369-370` is still not approved for mutation.
