# Q2m Packed4_1 Node Profile Analysis

This PR analyzes `packed4_1` under the `900x30 node-major` hypothesis. It is read-only: it does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not approve a third `chunked_binary` runtime probe, and does not mutate `packed4_0` or `packed4_1`.

## Boundary

Current project status remains:

```text
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

The analysis uses `30x30` table coordinates only. Those coordinates are still not proven to be game-world coordinates.

## Tool

`tools/analyze_packed4_1_node_profiles.py` reads the original local `map_setting`, reuses the Q2k/Q2l no15 weak-component graph, and writes JSON diagnostics outside the repository.

Example command:

```powershell
python .\tools\analyze_packed4_1_node_profiles.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2m_packed4_1_node_profiles"
```

The tool rejects repository outputs, runtime `mods` tree outputs, output paths inside the input tree, and generated-output hardlink/samefile aliases of the input.

## Evidence

The generated diagnostics are repository-external:

```text
D:\tfm2_q2a_evidence\q2m_packed4_1_node_profiles\
```

| File | Size | SHA-256 |
| --- | ---: | --- |
| `packed4_1_node_profile_catalog.json` | 510,584 | `f38e9946012918cc1e86ca7b0aeed10a696fa43628f05c451d31157480ca49fe` |
| `packed4_1_profile_spatial_patterns.json` | 45,774 | `a6141fd338381e50fd195a8f7e1ced938548d77a3e8d35e96342f0036eb39a3a` |
| `packed4_1_profile_component_correlation.json` | 379,599 | `4b3babdc65c35c49ae94382e247e94ce3dc443e3738b9f1cd1e86131fb0b3284` |
| `packed4_1_profile_bridge_correlation.json` | 904,423 | `bfb01cf453f51152dcac8d39efe6cd7c70b5096c66c621e70789f48b08078201` |
| `packed4_1_profile_tracked_nodes.json` | 11,151 | `5dfe141bfe776d39d081da80b5a37364ec358cd30e8c8e858485a30b7f8e013c` |
| `q2m_packed4_1_profile_interpretation.json` | 2,934 | `c55b685a83e40ed3c886187c90ba357d71e8a15549f42f390f83c92a3f3a457d` |

Input baseline:

```text
size: 1,451,980
sha256: 6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0
```

## Profile Catalog

Under the `node-major` hypothesis:

```text
profile = packed4_1[node * 30 : node * 30 + 30]
```

Observed profile space:

```text
node_count: 900
unique_profile_count: 507
profile_frequency_histogram:
  1: 372
  2: 77
  3: 15
  4: 19
  5: 7
  6: 8
  7: 3
  9: 1
  10: 1
  12: 1
  14: 2
  90: 1
```

The frequency-90 profile is the singleton profile:

```text
profile_id: profile_0001
node_count: 90
exclusive_role: singleton_only
profile:
  [8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
   8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
   8, 0, 8, 0, 8, 0, 8, 0, 8, 0]
```

Singleton profile summary:

```text
singleton_node_count: 90
singleton_unique_profile_count: 1
singleton_profile_id: profile_0001
shared_profile_count_with_large_component: 0
singleton_profiles_disjoint_from_large: true
```

Large component summary:

```text
large_component_id: 0
large_component_node_count: 810
large_component_unique_profile_count: 506
```

This is a stronger version of the Q2l signal: all no15 singleton nodes share a `packed4_1` node-major profile, and no node in the 810-node large component uses that exact profile.

## Spatial Pattern

`profile_0001` matches the Q2l no15 singleton set exactly:

```text
profile_id: profile_0001
node_count: 90
spatial_pattern: matches_no15_singleton_band
singleton_overlap_count: 90
bounding_box:
  min_x: 3
  max_x: 26
  min_y: 3
  max_y: 26
```

This remains table-coordinate evidence only. It does not prove a game-world band or any runtime position.

## Component Correlation

The profile/component split is clean for the singleton set:

```text
profile_0001:
  singleton_component: 90
  large_component: 0

large component:
  unique profiles: 506
  does not contain profile_0001
```

Other frequent profiles belong only to the large component. The largest large-component profiles have counts `14`, `14`, `12`, `10`, and `9`, which are much smaller than the singleton profile count of `90`.

## Bridge Correlation

`profile_0001` is not a simple bridge-strength descriptor. The 90 nodes share the same profile, but their code15 endpoint degrees vary widely:

```text
profile_id: profile_0001
total_code15_endpoint_count: 16,642
degree_min: 90
degree_max: 400
degree_average: 184.9111111111111
```

Interpretation note from the tool:

```text
same profile has varied bridge degrees; profile may be a class marker rather than a bridge-strength descriptor
```

This supports a static `node_class_descriptor_candidate` reading more than a direct bridge-count or bridge-strength interpretation.

## Tracked Nodes

Tracked nodes include the prior runtime probes and Q2l top bridge singleton nodes.

| Node | Role | Profile | Notes |
| ---: | --- | --- | --- |
| `369` | singleton component | `profile_0001` | Q2e/Q2f source; total code15 endpoint degree `262`. |
| `370` | large component | `profile_0287` | Q2e/Q2f target; total code15 endpoint degree `30`. |
| `59` | large component | `profile_0156` | Q2g source; no observed code15 endpoint degree. |
| `837` | large component | `profile_0002` | Q2g target and universal-like node; total code15 endpoint degree `180`. |
| `126` | singleton component | `profile_0001` | Top singleton bridge node; total code15 endpoint degree `400`. |
| `617` | singleton component | `profile_0001` | Top singleton bridge node; total code15 endpoint degree `370`. |
| `654` | singleton component | `profile_0001` | Top singleton bridge node; total code15 endpoint degree `364`. |
| `184` | singleton component | `profile_0001` | Top singleton bridge node; total code15 endpoint degree `362`. |
| `773` | singleton component | `profile_0001` | Top singleton bridge node; total code15 endpoint degree `362`. |
| `498` | singleton component | `profile_0001` | Top singleton bridge node; total code15 endpoint degree `360`. |

Node `837` remains a static diagnostic point only. It is not a node/world anchor.

## Conclusion

Q2m result:

```json
{
  "packed4_1_node_major_role": "node_class_descriptor_candidate",
  "runtime_mutation_allowed": false,
  "packed4_mutation_allowed": false,
  "third_chunked_binary_runtime_probe_allowed": false,
  "map_editing_allowed": false,
  "next_recommended_step": "continue_static_decoding"
}
```

This PR strengthens the static case that `packed4_1` node-major profiles describe some node class or special-node membership. It does not prove gameplay semantics, does not prove node/world transform, and does not approve mutation of `packed4_1`, `packed4_0`, `chunked_binary`, regions, collision, pathing, spawns, or visual sync.
