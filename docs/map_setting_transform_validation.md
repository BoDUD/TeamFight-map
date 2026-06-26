# MapSetting Transform Validation

Date: 2026-06-26

This is Q2c-1 read-only validation for relation semantics and the `30x30` grid transform. It does not create a mutated `map_setting`, does not install a `map_setting` override, and does not change gameplay fields.

## Reproduction

Run the semantic validator against the local original `map_setting` and keep all evidence outside the repository:

```powershell
python .\tools\map_setting_validate_semantics.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --bundle "D:\steam\steamapps\common\Teamfight Manager2\bundle.game_data" `
  --output-dir "D:\tfm2_q2a_evidence\map_setting_transform_validation"
```

The tool writes:

```text
D:\tfm2_q2a_evidence\map_setting_transform_validation\
  semantic_validation_manifest.json
  chunked_packed4_contingency.json
  direction_code_mapping.json
  transform_scores.json
  best_transform_overlay.png
  blocked_edge_overlay_<transform>.png
  open_edge_overlay_<transform>.png
  runtime_grid_probe.png
  runtime_anchor_measurements.json
  candidate_decision.json
  original_assets\
```

Evidence hashes from the local run:

```text
semantic_validation_manifest.json: 071117b8c98454eec3e45bb8b3dbf9f6ff0147a75d235251063585ee119d32b1
chunked_packed4_contingency.json:  c491d8ffbacbd92b6ad2ce41a9720d6d81c9fea76fbe3ff49455b988ed163150
direction_code_mapping.json:       d3ae47d8c0c5012443b54855a011a64fdb3a3f43b82919129d43d9c810e1a74a
transform_scores.json:             458ce3e11ea874fbbff1d26444a41d1e979128a45b5c8ab1de33d6bc6d0d333a
runtime_grid_probe.png:            b32cd9669b2f9d1147e7612ab91996ac0152a6156592858e2f622ea73757ddc8
candidate_decision.json:           1f7e1f43148c36d1a7e093ca62950b3f017ecf30029d5dc29b6204d20dbd6ee9
```

The extracted original assets, overlays, probe screenshot, and manifests are local evidence only. They must not be committed.

## Semantic Findings

`chunked_binary` remains a symmetric source-target relation, but it does not behave like a connected-component or reachability transitive closure:

```json
{
  "diagonal_0_count": 596,
  "diagonal_1_count": 304,
  "transpose_mismatch_count": 0,
  "unique_row_count": 897,
  "connected_pair_count": 106670,
  "connected_pair_row_signature_mismatch_count": 106658,
  "connected_pair_row_signature_mismatch_ratio": 0.999888,
  "transitivity_violation_count": 34691814,
  "closure_like": false
}
```

This keeps a symmetric two-cell edit theoretically possible from an invariant perspective, but it does not prove gameplay safety.

The `chunked_binary` and `packed4_0` cross-table does not support a strong `packed4_0 == 15` sentinel rule:

```json
{
  "p_packed4_0_eq_15_given_chunked_binary_eq_0": 0.196971,
  "p_chunked_binary_eq_0_given_packed4_0_eq_15": 0.895068,
  "packed4_0_15_strongly_implies_chunked_0": false,
  "chunked_0_strongly_implies_packed4_0_15": false
}
```

For candidate edge `369-370`, both chunked directions are `1` and both `packed4_0` directions are `15`. The hypothetical two-cell chunked edit therefore does not conflict with the current sentinel heuristic:

```json
{
  "edge": [369, 370],
  "chunked_forward": 1,
  "chunked_reverse": 1,
  "packed4_forward": 15,
  "packed4_reverse": 15,
  "cross_layer_consistency_after_hypothetical_edit": "no_packed4_0_conflict_detected_for_this_edge"
}
```

## Direction Codes

Adjacent-node sampling makes codes `0-7` look direction-like, but code `15` is unresolved and too mixed to call the whole table stable:

```json
{
  "code_to_direction": {
    "0": "E",
    "1": "S",
    "2": "W",
    "3": "N",
    "4": "SE",
    "5": "SW",
    "6": "NE",
    "7": "NW",
    "15": "SW"
  },
  "purity_by_code": {
    "0": 0.908976,
    "1": 0.908976,
    "2": 0.908976,
    "3": 0.908976,
    "4": 1.0,
    "5": 1.0,
    "6": 1.0,
    "7": 1.0,
    "15": 0.136223
  },
  "unresolved_codes": [15],
  "stability": "ambiguous"
}
```

This supports the hypothesis that `packed4_0` contains path or next-hop information, but it is not strong enough to approve a mutation target.

## Transform Scoring

The validator builds a local adjacent-edge graph from symmetric `chunked_binary` neighbors and scores all eight square transforms against local `wall_5v5`, `wall_5v5_front`, and `minimap_5v5_bg` resources.

Top results:

| Rank | Transform | Score | Notes |
| ---: | --- | ---: | --- |
| 1 | `rotate180` | `0.013291` | Best numeric score. |
| 2 | `identity` | `0.013200` | Only `0.000091` behind first place. |
| 3 | `anti_transpose` | `0.004171` | Clearly lower. |
| 4 | `transpose` | `0.003777` | Clearly lower. |

The margin between first and second place is far below the `0.05` threshold, so the offline transform conclusion is:

```text
ambiguous
```

This means the original-map world/grid transform is not proven by offline resource matching.

## Runtime Grid Probe

The tool generates a pure visual background probe at:

```text
D:\tfm2_q2a_evidence\map_setting_transform_validation\runtime_grid_probe.png
```

It marks:

- `30x30` grid lines.
- Four logical corners with different colors.
- Logical `+X` and `+Y` directions.
- Nodes `369` and `370`.
- A center reference node.

To stage it in the installed local mod copy without touching the repository package:

```powershell
python .\tools\install_runtime_spike_mod.py `
  --clean `
  --enable-exclusive `
  --stage-background-source "D:\tfm2_q2a_evidence\map_setting_transform_validation\runtime_grid_probe.png"
```

Manual runtime capture is still pending. The expected local evidence file is:

```text
D:\tfm2_q2a_evidence\map_setting_transform_validation\runtime_grid_probe_screenshot.png
```

At minimum, the screenshot or measurements must record:

- Blue base.
- Red base.
- Map center.
- Two visible towers or objectives.
- Candidate edge `369-370` actual in-match location.

## Candidate Decision

Current decision:

```json
{
  "candidate_edge": [369, 370],
  "candidate_status": "pending_runtime_grid_confirmation",
  "may_enter_mutation_pr": false,
  "blockers": [],
  "remaining_validation": [
    "packed4_0 direction code mapping is ambiguous",
    "offline wall/minimap transform scoring is ambiguous",
    "runtime visual grid screenshot has not been captured in this PR"
  ]
}
```

No PR should generate a mutated `map_setting` from edge `369-370` until the remaining validation is closed or the risk is explicitly accepted in a separate review. If it later becomes valid, the approved mutation shape remains exactly two symmetric `chunked_binary` cells and two serialized bytes, preserving transpose symmetry and the original SHA-256 rollback baseline.

Result of this PR: Q2c-1 read-only semantics and transform validation is implemented, but the candidate is not approved for mutation.
