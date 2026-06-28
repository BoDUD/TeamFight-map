# Q2k Code15 Component Graph

Date: 2026-06-28

This PR analyzes the `packed4_0 == 15` component graph without mutation. It does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not approve a third `chunked_binary` runtime probe, and does not mutate `packed4_0` or `packed4_1`.

## Question

```text
Does packed4_0 code 15 connect no-15 subgraph components?
```

Q2j showed:

```text
connected non-self code15 contexts: 15,930
recoverable through no-15 direction graph: 0
recoverable through chunked non15 graph: 0
```

Q2k therefore asks whether those code15 contexts are cross-component bridge candidates rather than ordinary recoverable paths.

## Read-Only Tool

`tools/analyze_code15_component_graph.py` reads the original local `map_setting`, keeps all payloads read-only, and writes JSON diagnostics outside the repository.

Command used locally:

```powershell
python .\tools\analyze_code15_component_graph.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2k_code15_component_graph"
```

Output evidence:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\q2k_code15_component_graph\no15_component_summary.json` | 21,881 | `3733aadc1746281bd3908c78a44588bdfbd718215923a79f0485e9456121548a` |
| `D:\tfm2_q2a_evidence\q2k_code15_component_graph\code15_cross_component_edges.json` | 25,002 | `f3a097735f23bc050dd1900912759bfb0b5720b5c23d98b9685912d58f6db213` |
| `D:\tfm2_q2a_evidence\q2k_code15_component_graph\code15_component_pair_matrix.json` | 36,276 | `bd8aea72cfe245ddb5c6f4bc574dcc33abb1a9abe922253734d1cd59504d1de0` |
| `D:\tfm2_q2a_evidence\q2k_code15_component_graph\prior_probe_component_context.json` | 3,934 | `afac523ddf3f51e078f73e4bf9001c6fbf4bb46756a580a7d57558c0955d5ff3` |
| `D:\tfm2_q2a_evidence\q2k_code15_component_graph\packed4_1_component_correlation.json` | 50,482 | `ba80633b6d01dfb232d56ec388348fd6ff959e5c79bf24f5c19e4f3eb553ff78` |
| `D:\tfm2_q2a_evidence\q2k_code15_component_graph\q2k_code15_component_interpretation.json` | 1,953 | `daaa5f23116ee350bd9804fd730a3883bbfb305aef00d42d971e5078681c5f1d` |

Safety:

```text
read_only: true
mutated_map_setting_generated: false
runtime_install_modified: false
map_setting_override_installed: false
outputs_inside_repository: false
outputs_under_mods_tree: false
```

## No-15 Components

The tool builds weak components over this relation:

```text
chunked_binary == 1
packed4_0 != 15
source != target
```

Component result:

```text
component_count: 91
component_size_histogram:
  size 810: 1
  size 1: 90
directed_no15_edge_count: 90,740
undirected_no15_edge_count: 45,370
```

Tracked nodes:

| Node | Component | Component size | Row class | Column class |
| ---: | ---: | ---: | --- | --- |
| `369` | `36` | `1` | `middle` | `middle` |
| `370` | `0` | `810` | `middle` | `middle` |
| `59` | `0` | `810` | `sparse` | `sparse` |
| `837` | `0` | `810` | `universal_like` | `universal_like` |

The unproven table coordinate positions are still diagnostic only. They are not game-world coordinates.

## Code15 Cross-Component Edges

The tool then checks all:

```text
chunked_binary == 1
packed4_0 == 15
source != target
```

Result:

```text
code15 connected non-self edge count: 15,930
same_component_count: 0
cross_component_count: 15,930
cross_component_ratio: 1.0
```

This is the strongest Q2k finding: every connected non-self code15 relation crosses no15 components. That makes code `15` a static cross-component bridge candidate. It does not prove runtime semantics.

Top directed component pairs:

```text
0 -> 7:   189
7 -> 0:   189
0 -> 14:  172
14 -> 0:  172
0 -> 87:  171
87 -> 0:  171
```

The largest component `0` is a hub:

```text
component 0 source code15 edges: 7,609
component 0 target code15 edges: 7,609
component 0 size: 810
```

## Node 837

Node `837` remains special, but it is not a node/world anchor:

```text
component_id: 0
component_size: 810
row_sum: 900
column_sum: 900
row_class: universal_like
column_class: universal_like
code15_source_edges: 90
code15_target_edges: 90
```

This keeps the Q2h/Q2j interpretation plausible: Q2g may have produced no semantic signal because `59` and `837` are both inside the large no15 component, and `837` is a universal-like special node. That is still a hypothesis, not proof.

## Prior Probe Component Context

Q2e/Q2f `369-370`:

```text
369 component: 36, size 1
370 component: 0, size 810
same_no15_component: false
packed4_0 values: 15 / 15
both cells are code15 cross-component relations
runtime result: loader + extended observation pass
semantic effect observed: false
```

Q2g `59-837`:

```text
59 component: 0, size 810
837 component: 0, size 810
same_no15_component: true
packed4_0 values: 1 / 3
not a code15 cross-component relation
runtime result: loader pass
semantic effect observed: false
```

This explains why Q2e/Q2f and Q2g were testing different static contexts. It still does not approve a third runtime mutation.

## Packed4_1 Correlation

Q2k keeps `packed4_1` read-only. It tests three reshape assumptions:

```text
900 x 30 node-major
30 x 900 layer-major
30 x 30 x 30 layer-major slices
```

Observed `packed4_1` value histogram:

```text
0: 12,094
1:    578
2:    753
3:  1,280
4:    321
5:    262
6:    250
7:    278
8: 11,184
```

Component-profile checks:

| Assumption | Unique node profiles | Non-singleton components | Weighted purity on non-singletons | Component-id-like pattern |
| --- | ---: | ---: | ---: | --- |
| `900x30 node-major` | `507` | `1` | `0.017284` | `not_detected` |
| `30x900 layer-major` | `411` | `1` | `0.262963` | `not_detected` |
| `30x30x30 layer-major slices` | `411` | `1` | `0.262963` | `not_detected` |

Node `837` profiles:

```text
node-major: [8, 0, 7, 0, 8, 0, 8, 0, 3, 0, 8, 0, 8, 0, 8, 0, 3, 0, 8, 0, 8, 0, 8, 2, 8, 0, 8, 0, 8, 0]
layer-major: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

No tested `packed4_1` reshape produced a clear component-id-like pattern. This does not decode `packed4_1`, and it does not approve `packed4_1` mutation.

## Conclusion

```json
{
  "code15_component_role": "cross_component_bridge_candidate",
  "runtime_mutation_allowed": false,
  "packed4_mutation_allowed": false,
  "map_editing_allowed": false
}
```

What improved:

```text
code15 connected non-self contexts are all cross-component under the no15 graph
no15 graph has one large 810-node component and ninety 1-node components
Q2e/Q2f touched a code15 cross-component relation
Q2g did not touch a code15 cross-component relation
packed4_1 does not show a clear component-id-like pattern under tested reshapes
```

What remains unproven:

```text
the gameplay meaning of no15 components
whether code15 means bridge, layer transition, special relation, overflow, or cache fallback
whether packed4_0 is authoritative at runtime
how packed4_1 relates to pathing or visibility
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
