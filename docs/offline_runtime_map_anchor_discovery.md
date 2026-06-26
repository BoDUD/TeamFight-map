# Offline Runtime Map Anchor Discovery

Date: 2026-06-26

This read-only spike checks whether original runtime bundle data contains an independent anchor for mapping `map_setting` logical nodes to game-world coordinates. It does not mutate `map_setting`, install a `map_setting` override, install an asset override, or commit original game resource payloads.

## Commands

```powershell
python .\tools\audit_bundle_map_assets.py `
  --bundle "D:\steam\steamapps\common\Teamfight Manager2\bundle.game_data" `
  --output-dir "D:\tfm2_q2a_evidence\offline_runtime_map_anchor_discovery"

python .\tools\scan_setting_anchor_candidates.py `
  --bundle "D:\steam\steamapps\common\Teamfight Manager2\bundle.game_data" `
  --asset-index "D:\tfm2_q2a_evidence\offline_runtime_map_anchor_discovery\bundle_map_related_assets.json" `
  --output-dir "D:\tfm2_q2a_evidence\offline_runtime_map_anchor_discovery"

python .\tools\derive_map_setting_path_graph.py `
  --bundle "D:\steam\steamapps\common\Teamfight Manager2\bundle.game_data" `
  --output-dir "D:\tfm2_q2a_evidence\offline_runtime_map_anchor_discovery"
```

## Evidence

All generated evidence is stored outside the repository at:

```text
D:\tfm2_q2a_evidence\offline_runtime_map_anchor_discovery\
```

| File | SHA-256 |
| --- | --- |
| `bundle_asset_index.json` | `7641a29a8626df715e82f499380845d4b9759ab4f4bc5f9b08efd0fef159328d` |
| `bundle_map_related_assets.json` | `df0a15db39b791d9a6787e6419bef3fa8735138a83c61760b63ec5e1f4e2d6e8` |
| `bundle_map_anchor_candidates.json` | `54241c5a589630a2e4eba69ace0d70d8b118ce4186ec9cd2b7c92bc9a7d2d08d` |
| `setting_blob_signatures.json` | `6dfe6675f2fb87f9105d62d6ae972fcf26bfc4f50197bead8e5431008f3b38ba` |
| `possible_coordinate_tables.json` | `bdb1d9e494682f80d418f053bf0925e080792729fa9cbe0551083d91586be29e` |
| `anchor_candidate_report.json` | `0344ee6d66a8d2f8b23dd719f2b46aa86e864e76640f4544a043990291213acf` |
| `packed4_path_follow_validation.json` | `d61b69e842e8c740c1a74d7d654fb66ad1ca746ef55fa2b41dd96ac82a5376a9` |
| `derived_local_adjacency_graph.json` | `385efc9ddcf04c2ca1f76e918518cbd69d149bdbbdee8d20944f63afcbecdb54` |
| `transform_scores_path_graph.json` | `7678ec7330de54370f22333daa58c2065fd4f31a7a90d9ed2259ab86cf91e1f6` |
| `best_transform_path_graph_overlay.png` | `74b2647f2567f93357789fb56ea4855bd7ebd3ce6b4d4f056214529c57197ace` |

The audit and scan tools write metadata and diagnostic summaries only. `derive_map_setting_path_graph.py` extracts original visual reference PNGs into the repository-external evidence directory only so it can create the diagnostic overlay; those payloads are not committed.

## Bundle Asset Audit

`audit_bundle_map_assets.py` indexes the bundle and filters map-related metadata using conservative keywords such as `map`, `setting`, `5v5`, `path`, `visible`, `collision`, `wall`, `bush`, `tower`, `nexus`, `spawn`, `serpen`, `morgard`, `epic`, `monster`, and `minimap`.

Result:

```json
{
  "related_asset_count": 143,
  "candidate_count": 143,
  "payloads_written": false,
  "result": {
    "offline_anchor_result": "metadata_only_candidates_unverified",
    "map_setting_node_world_transform": "unproven",
    "candidate_369_370": "blocked"
  }
}
```

Category counts:

| Category | Count |
| --- | ---: |
| `actor_or_objective_visual_reference` | 55 |
| `map_related_unverified` | 11 |
| `map_setting` | 1 |
| `map_visual_layer_reference` | 9 |
| `minimap_visual_reference` | 11 |
| `possible_runtime_anchor_data` | 11 |
| `setting_or_runtime_data_candidate` | 15 |
| `unrelated` | 30 |

Candidate kind counts:

| Candidate kind | Count |
| --- | ---: |
| `possible_binary_anchor_source` | 27 |
| `visual_alignment_reference` | 75 |
| `map_related_unverified` | 41 |

This confirms there are metadata-level candidates beyond `asset/base/setting/map_setting`, but metadata alone does not provide entity coordinates, world bounds, or a node/world transform.

## Setting Blob Scan

`scan_setting_anchor_candidates.py` scans the binary candidates for size markers, possible length-prefixed arrays, and possible coordinate-pair encodings. It does not decode payload semantics.

Result:

```json
{
  "candidate_asset_count": 29,
  "unverified_coordinate_table_count": 68,
  "offline_anchor_result": "no_sufficient_anchor_found",
  "map_setting_node_world_transform": "unproven",
  "candidate_369_370": "blocked"
}
```

The scan found coordinate-like numeric patterns in multiple setting blobs, including `asset/base/setting/map_setting`, but none of them are tied to semantic labels such as base, tower, jungle camp, objective, world bounds, or a known path-grid anchor. They remain `unverified_coordinate_table` candidates only.

## Path Graph Derivation

`derive_map_setting_path_graph.py` reads `asset/base/setting/map_setting` from the bundle, decodes the known structural shell, and derives diagnostics from `chunked_binary` and `packed4_0`.

Path-follow validation result:

```json
{
  "next_hop_hypothesis": "weak_or_unresolved",
  "tested_connected_pairs": 20000,
  "status_counts": {
    "reached": 17986,
    "unresolved_code": 2014
  }
}
```

Transform scoring result:

```json
{
  "best_transform": "rotate180",
  "second_transform": "identity",
  "score_margin": 0.000198,
  "conclusion": "ambiguous",
  "direction_code_stability": "ambiguous"
}
```

The stricter path-graph scoring still cannot distinguish `rotate180` from `identity` with a meaningful margin. This preserves the previous conclusion: visual or graph overlay evidence alone is not enough to prove `map_setting` node/world mapping.

## Decision

```json
{
  "offline_anchor_result": "no_sufficient_anchor_found",
  "map_setting_node_world_transform": "unproven",
  "candidate_369_370": "blocked",
  "may_enter_mutation_pr": false
}
```

PR #9 does not approve any `map_setting` mutation. Candidate `369-370` remains blocked until an independent anchor is found through a stronger original-data decoder, a newly exposed SDK/debug surface, or an explicit risk-acceptance document for a tiny controlled probe.
