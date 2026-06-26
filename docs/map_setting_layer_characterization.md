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
  chunked_binary_values.png
  packed4_0_values.png
  packed4_0_value_0_mask.png ... packed4_0_value_15_mask.png
  packed4_1_slices\
  original_assets\
  overlays\
  layer_inspection_manifest.json
```

Manifest SHA-256:

```text
52427ca7932cb88156e3f7195ba5e3fce43b6d5997034beb717f8a03a4d852cb
```

The extracted original assets and overlay images are local evidence only. They must not be committed.

## Layer Findings

| Layer | Shape | Histogram | Current hypothesis | Mutation status |
| --- | ---: | --- | --- | --- |
| `chunked_binary` | `900x900` | `0: 703026`, `1: 106974` | Symmetric source-target relation over a `30x30` logical grid, most likely visibility or reachability. Because `transpose_mismatch_count` is `0`, it behaves like an undirected relation rather than a direct map texture. | Candidate layer for the first one-cell mutation, still hypothesis only. |
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

## Selected Read-Only Candidate

Candidate for the next PR, not mutated here:

```json
{
  "layer": "chunked_binary",
  "logical_coordinate": [32, 31],
  "source_node": 31,
  "target_node": 32,
  "source_xy_30x30": [1, 1],
  "target_xy_30x30": [2, 1],
  "serialized_byte_offset": 35668,
  "old_value": 1,
  "new_value": 0,
  "new_value_source_coordinate": [32, 30],
  "rollback_source_sha256": "6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0",
  "prediction_confidence": "hypothesis"
}
```

Selection rationale:

- The layer is binary and heavily uses both legal values.
- The selected `new_value` comes from an adjacent cell, so the first mutation would not introduce a new state.
- The candidate maps to the upper-left outer logical edge of the `30x30` grid, away from bases, tower clusters, objectives, jungle camps, functional brush, and normal lane flow.
- The predicted effect is a one-edge visibility or reachability relation change. No broad visual, spawn, tower, monster, minion, or AI path effect is expected.
- The candidate is chosen for review only. The semantic field is still a hypothesis until an A/B/A runtime mutation proves a local effect and rollback.

## Rollback Plan

The next mutation PR must:

1. Verify the input SHA-256 is exactly `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0`.
2. Write the mutated output outside the repository and never overwrite the original input.
3. Prove the diff changes exactly one byte at serialized offset `35668` and exactly one logical cell.
4. Stage the mutated file only in the installed local mod copy for run B.
5. Restore the byte-equivalent original file for A2 from the SHA-256 baseline above.
6. Stop immediately on crash, load error, unit spawn abnormality, stuck lanes, AI route regression, or failed rollback.

Result of this PR: candidate selected for follow-up review. No Q2c loader mutation pass or semantic mutation pass is claimed.
