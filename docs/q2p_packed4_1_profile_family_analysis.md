# Q2p Packed4_1 Profile Family Analysis

This PR classifies `packed4_1` node-major profiles into exact profile families and separate Hamming-neighbor clusters. It is read-only: it does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not approve a third `chunked_binary` runtime probe, and does not mutate `packed4_0` or `packed4_1`.

## Boundary

Current project status remains:

```text
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

The analysis uses `30x30` table coordinates. These coordinates are not proven game-world coordinates.

## Tool

`tools/analyze_packed4_1_profile_families.py` reads the original local `map_setting`, reuses the Q2K/Q2L/Q2M no15 component graph, and writes JSON plus diagnostic PNGs outside the repository.

Example command:

```powershell
python .\tools\analyze_packed4_1_profile_families.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2p_packed4_1_profile_families"
```

The tool rejects repository outputs, runtime `mods` tree outputs, output paths inside the input tree, and generated-output hardlink/samefile aliases of the `map_setting` input.

## Evidence

The generated diagnostics are repository-external:

```text
D:\tfm2_q2a_evidence\q2p_packed4_1_profile_families\
```

Core outputs:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `packed4_1_profile_family_catalog.json` | 2,254,100 | `ffb0c6a3d2a1b24d5ffd73fc61c116fa1f41b448daf197d611d2bdfef76509a0` |
| `packed4_1_profile_hamming_clusters.json` | 33,718 | `5ca8360edce6cc001f32d9ddf1604a28d11b715f48fc6a358a00da515d9125ab` |
| `packed4_1_profile_family_spatial_patterns.json` | 706,370 | `4b7c1c48459b1eee756f21760fc23343f0ff1214ea20d72a10984d03cdfb6a0c` |
| `packed4_1_profile_family_component_correlation.json` | 417,308 | `e8e564df6765178be81bbb0d97adfdad2c55dc0f8c86a98d538d3ff082be9627` |
| `packed4_1_profile_family_anchor_candidates.json` | 44,550 | `0c64a66751e9c07f7074e814c7c7608e64366aca454a89418dde85575baea7fc` |
| `tracked_profile_family_nodes.json` | 16,642 | `6a938414a1a6341d22bc92ebe9497af8dadc7f43b5326f5c0389da951af12002` |
| `q2p_profile_family_interpretation.json` | 1,901 | `127b19d1ecbe530500ed43129f88d143c32771e199d3e2386e94e4373301e176` |
| `profile_family_masks\top_profile_family_contact_sheet.png` | 20,614 | `95d7a902faa4dfe120802643a05d335c33f53e62af86d03285ae9bcf7d43cd82` |

The tool also generated `40` repository-external family mask PNGs under:

```text
D:\tfm2_q2a_evidence\q2p_packed4_1_profile_families\profile_family_masks\
```

Input baseline:

```text
map_setting size: 1,451,980
map_setting sha256: 6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0
```

## Family Definitions

Q2P uses two separate concepts:

```text
exact profile family:
  nodes with the exact same packed4_1[node * 30 : node * 30 + 30] profile

Hamming cluster:
  diagnostic connected components between exact profiles with Hamming distance <= 2
```

The exact profile families are the primary interpretation surface. Hamming clusters are diagnostic only and do not override exact profile-family conclusions.

## Exact Profile Families

Observed family summary:

```text
unique_profile_count: 507
exact_family_count: 507
top_family: family_0001
top_family_node_count: 90
top_family_dominant_role: singleton_component
```

`family_0001` is the full singleton profile:

```text
[8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
 8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
 8, 0, 8, 0, 8, 0, 8, 0, 8, 0]
```

This keeps the Q2M/Q2O conclusion intact: the complete profile identifies all 90 no15 singleton nodes, but individual slot values are not sufficient.

## Hamming Clusters

With default `--hamming-threshold 2`:

```text
hamming_cluster_count: 73
hamming_edge_count: 1,337
```

This shows many exact profiles are close in slot space. It does not mean those profiles have the same runtime role. Q2P keeps exact profile families and Hamming clusters separate for that reason.

## Asymmetric Anchor Candidates

Q2P looks for small, asymmetric, non-singleton-only exact profile-family masks that may be useful in a later read-only visual-correlation pass.

Result:

```text
asymmetric_anchor_candidates_found: true
anchor_candidate_count: 134
may_use_for_visual_correlation: true
node_world_transform: unproven
```

Top candidate examples:

| Family | Nodes | Dominant role | Asymmetry | Avg code15 endpoint degree | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| `family_0120` | 2 | `large_component` | `1.0` | `160.0` | small asymmetric mask, not singleton-only |
| `family_0112` | 2 | `large_component` | `1.0` | `75.0` | small asymmetric mask, not singleton-only |
| `family_0023` | 5 | `large_component` | `1.0` | `66.4` | small asymmetric mask, not singleton-only |
| `family_0042` | 4 | `large_component` | `1.0` | `57.0` | small asymmetric mask, not singleton-only |
| `family_0049` | 3 | `large_component` | `1.0` | `52.666666666666664` | small asymmetric mask, not singleton-only |

These are not runtime anchors. They are only candidate masks for a later read-only visual-correlation PR.

## Historical Probe Context

Tracked nodes:

```text
369, 370, 59, 837, 126, 617, 654, 184, 773, 498
```

Key results:

```text
node 369:
  profile_id: profile_0001
  family_id: family_0001
  component_role: singleton_component
  q2e/q2f endpoint: true

node 370:
  profile_id: profile_0287
  family_id: family_0287
  component_role: large_component
  q2e/q2f endpoint: true

node 59:
  profile_id: profile_0156
  family_id: family_0156
  component_role: large_component
  row_class: sparse
  q2g endpoint: true

node 837:
  profile_id: profile_0002
  family_id: family_0002
  component_role: large_component
  row_class: universal_like
  column_class: universal_like
  q2g endpoint: true
```

This keeps the Q2e/Q2f/Q2g runtime probes in static context:

```text
Q2e/Q2f: cross singleton/large bridge context
Q2g: large-component internal direction-like context plus universal-like node
```

It still does not explain the missing runtime semantic signal.

## Conclusion

Q2P result:

```json
{
  "packed4_1_profile_family_role": "profile_level_node_class_descriptor_candidate",
  "asymmetric_anchor_candidates_found": true,
  "runtime_mutation_allowed": false,
  "packed4_mutation_allowed": false,
  "third_chunked_binary_runtime_probe_allowed": false,
  "map_editing_allowed": false,
  "next_recommended_step": "continue_static_decoding"
}
```

Q2P strengthens the static hypothesis that exact `packed4_1` node-major profiles describe node classes, and it finds asymmetric masks that may be useful for a later read-only visual-correlation pass. It does not prove gameplay semantics, does not prove node/world transform, does not approve any runtime probe, and does not approve mutation of `packed4_1`, `packed4_0`, `chunked_binary`, regions, collision, pathing, spawns, or visual sync.
