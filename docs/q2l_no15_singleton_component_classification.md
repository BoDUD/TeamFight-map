# Q2l No15 Singleton Component Classification

Date: 2026-06-28

This PR classifies the `90` no15 singleton components found in Q2k. It is read-only: it does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not approve a third `chunked_binary` runtime probe, and does not mutate `packed4_0` or `packed4_1`.

## Question

```text
Are the 90 no15 singleton components structured special nodes, or just scattered graph leftovers?
```

Q2k found:

```text
no15 component_count: 91
component_size_histogram:
  size 810: 1
  size 1: 90
```

Q2l focuses on those `90` singleton nodes.

## Read-Only Tool

`tools/analyze_no15_singleton_components.py` reads the original local `map_setting`, reuses the Q2k no15 weak-component definition, and writes JSON diagnostics outside the repository.

Command used locally:

```powershell
python .\tools\analyze_no15_singleton_components.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2l_no15_singleton_components"
```

Output evidence:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\q2l_no15_singleton_components\no15_singleton_nodes.json` | 28,505 | `74f7c439bdab16f7618e9e29ba6d9bb1803c0396832aa1b50118497aa0347328` |
| `D:\tfm2_q2a_evidence\q2l_no15_singleton_components\no15_singleton_spatial_pattern.json` | 7,846 | `d09a031fab0bd3e368c78004b0644783cc195ca60d331d0d88ddd71995422d53` |
| `D:\tfm2_q2a_evidence\q2l_no15_singleton_components\code15_singleton_bridge_edges.json` | 33,163 | `fa77819df77455eefc81e0c4d83b0004337543d536cbafdbcf15aadfa38051ea` |
| `D:\tfm2_q2a_evidence\q2l_no15_singleton_components\singleton_packed4_1_profiles.json` | 61,886 | `c5ca0a701478edc00822c0de54e357237f0a54e124377d34e71a93a387b7758f` |
| `D:\tfm2_q2a_evidence\q2l_no15_singleton_components\q2l_singleton_component_interpretation.json` | 2,992 | `f8649e6db505e758f36fd1fbd011ca5e8770077c62950b8e3ebd7c59646a2f1f` |

Safety:

```text
read_only: true
mutated_map_setting_generated: false
runtime_install_modified: false
map_setting_override_installed: false
outputs_inside_repository: false
outputs_under_mods_tree: false
```

## Singleton Node Classes

The singleton set is not row/column-class uniform, but it is mostly middle/middle:

```text
singleton_count: 90
large_component_id: 0
large_component_size: 810

row/column class pairs:
  middle|middle: 88
  sparse|sparse: 2

edge positions:
  interior: 90
```

Each singleton node's `packed4_0` row contains only code `15` in the observed table. This is static evidence that singleton nodes cannot use ordinary `0-7` direction rows as sources. It does not prove gameplay semantics.

Tracked nodes:

| Node | Component | Row class | Column class |
| ---: | ---: | --- | --- |
| `369` | `36` singleton | `middle` | `middle` |
| `370` | `0` large | `middle` | `middle` |
| `59` | `0` large | `sparse` | `sparse` |
| `837` | `0` large | `universal_like` | `universal_like` |

## Spatial Pattern

The singleton nodes form a table-coordinate interior band candidate, not complete rows or columns:

```text
spatial_pattern: band_candidate
complete_rows: []
complete_columns: []
edge_distribution:
  interior: 90
bounding_box:
  min_x: 3
  max_x: 26
  min_y: 3
  max_y: 26
```

Row and column runs:

```text
row_runs:
  [3..21]
  [23..26]

column_runs:
  [3..21]
  [23..26]
```

The row and column histograms are identical under table coordinates, which is consistent with the broader symmetric structure observed in earlier Q2 analyses. This remains table-coordinate evidence only; it is not game-world location proof.

## Code15 Bridge Edges

Every singleton has code15 bridge edges, and in/out bridge degree is symmetric for every singleton:

```text
large_component_to_singleton: 7,609
singleton_to_large_component: 7,609
singleton_to_singleton: 712
all_singletons_have_code15_bridge: true
all_singleton_bridge_degrees_symmetric: true
```

Top bridge singleton nodes by total degree:

| Node | x | y | Total degree |
| ---: | ---: | ---: | ---: |
| `126` | `6` | `4` | `400` |
| `617` | `17` | `20` | `370` |
| `654` | `24` | `21` | `364` |
| `184` | `4` | `6` | `362` |
| `773` | `23` | `25` | `362` |
| `498` | `18` | `16` | `360` |

This supports a structured special-node-set hypothesis. It does not approve editing those bridges.

## Packed4_1 Profiles

Q2l keeps `packed4_1` read-only and compares singleton nodes to the large component under three reshape assumptions.

| Assumption | Singleton unique profiles | Large unique profiles | Shared profiles | Signal |
| --- | ---: | ---: | ---: | --- |
| `900x30 node-major` | `1` | `506` | `0` | `strong_unverified` |
| `30x900 layer-major` | `58` | `359` | `6` | `weak_or_absent` |
| `30x30x30 layer-major slices` | `58` | `359` | `6` | `weak_or_absent` |

Under the `900x30 node-major` assumption, every singleton shares this exact profile:

```text
[8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0]
```

That profile does not appear in the large component. This is useful static correlation, not a decoded `packed4_1` meaning and not permission to mutate `packed4_1`.

Tracked profile note:

```text
node 837 node-major profile:
[8, 0, 7, 0, 8, 0, 8, 0, 3, 0, 8, 0, 8, 0, 8, 0, 3, 0, 8, 0, 8, 0, 8, 2, 8, 0, 8, 0, 8, 0]
```

Node `837` remains in the large component, not the singleton set.

## Conclusion

```json
{
  "no15_singleton_role": "structured_special_node_set_candidate",
  "runtime_mutation_allowed": false,
  "packed4_mutation_allowed": false,
  "map_editing_allowed": false
}
```

What improved:

```text
the 90 singleton components are all interior and form a table-coordinate band candidate
all singleton nodes have symmetric code15 bridge degrees
all singleton packed4_0 source rows are entirely code15
node-major packed4_1 profiles separate singleton nodes from the large component
Q2e/Q2f touched one of these singleton bridge contexts
Q2g did not touch a singleton bridge context
```

What remains unproven:

```text
what singleton nodes mean in gameplay
whether code15 bridge semantics are pathing, visibility, layer transition, cache, or another system
whether packed4_1 node-major profiles are authoritative or descriptive
node/world transform
any safe gameplay mutation path
```

Blocked actions:

```text
third chunked_binary edge runtime probe
packed4_0 mutation
packed4_1 mutation
multi-edge or region mutation
collision/path/spawn export
visual synchronization
formal LOL map runtime export
```

Recommended next step:

```text
continue_static_decoding
```
