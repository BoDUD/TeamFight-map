# Q2j Packed4 Code15 Context Analysis

Date: 2026-06-28

This PR classifies `packed4_0` code `15` contexts without mutation. It does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not approve a third `chunked_binary` runtime probe, and does not mutate `packed4_0` or `packed4_1`.

## Question

```text
What is packed4_0 code 15 most likely to mean?
```

Candidate interpretations remain:

```text
blocked / unreachable sentinel
same-node / no-op / already-there
fallback / uncached path
special class node relation
path table overflow / unknown direction
cross-layer semantic mismatch
```

## Read-Only Tool

`tools/analyze_packed4_code15_contexts.py` reads the original local `map_setting`, keeps all payloads read-only, and writes JSON diagnostics outside the repository.

Command used locally:

```powershell
python .\tools\analyze_packed4_code15_contexts.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2j_packed4_code15_context_analysis"
```

Output evidence:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\q2j_packed4_code15_context_analysis\packed4_code15_contexts.json` | 1,697 | `c8bcfce986a7c2732ed0150948b84fc8c26f9504ccf496b571a9eaf3f0bd7551` |
| `D:\tfm2_q2a_evidence\q2j_packed4_code15_context_analysis\packed4_code15_distance_buckets.json` | 11,328 | `32c3dab66b2e4651230d3df0a553f32acd06f2ddfe6bd34b4b7096d7254d801e` |
| `D:\tfm2_q2a_evidence\q2j_packed4_code15_context_analysis\packed4_code15_endpoint_classes.json` | 14,723 | `e3d7a1a35cd5dbf72a2ab9f0999f94a9a3bc23821d3af32defa60f9144643d05` |
| `D:\tfm2_q2a_evidence\q2j_packed4_code15_context_analysis\packed4_code15_path_recovery.json` | 21,879 | `c4f516085b07ee61e3a7b9e8339a4a70ddac8e0739e0ace6f1b2012c03f7c23d` |
| `D:\tfm2_q2a_evidence\q2j_packed4_code15_context_analysis\q2j_code15_interpretation.json` | 3,555 | `a89ccbdf7ef88ca53190582db92af43aa9d0e2008b18202ceb31898e47be6cf3` |

Safety:

```text
read_only: true
mutated_map_setting_generated: false
runtime_install_modified: false
map_setting_override_installed: false
outputs_inside_repository: false
outputs_under_mods_tree: false
```

## Code 15 And Chunked Binary

The basic cross-table matches Q2i and confirms that `15` is not a clean blocked sentinel:

```text
packed4_0 == 15 and chunked_binary == 0: 138,476
packed4_0 == 15 and chunked_binary == 1:  16,234
packed4_0 != 15 and chunked_binary == 0: 564,550
packed4_0 != 15 and chunked_binary == 1:  90,740
```

Probabilities:

```text
P(chunked_binary == 0 | packed4_0 == 15): 0.8950681921
P(chunked_binary == 1 | packed4_0 == 15): 0.1049318079
P(packed4_0 == 15 | chunked_binary == 0): 0.1969713780
P(packed4_0 == 15 | chunked_binary == 1): 0.1517565016
P(packed4_0 == 15 overall): 0.191
```

This is associated with blocked or unconnected relations, but not strongly enough to call it a clean sentinel.

## Distance Buckets

For `chunked_binary == 1` and `packed4_0 == 15`, table-coordinate Chebyshev distance buckets are:

```text
distance 0:      304
distance 1:      336
distance 2-3:    654
distance 4-8:  2,364
distance 9+:  12,576
```

The majority of connected code15 contexts are long-distance in the unproven `30x30` table coordinate grid. Distance is still a table diagnostic, not game-world distance; node/world transform remains unproven.

## Endpoint Classes

Code15 endpoint class counts are symmetric, consistent with the previously observed transpose symmetry:

```text
source middle:         142,354
source sparse:          11,810
source near_universal:     455
source universal_like:      91

target middle:         142,354
target sparse:          11,810
target near_universal:     455
target universal_like:      91
```

Tracked node `837`:

```text
row_sum: 900
row_class: universal_like
column_sum: 900
column_class: universal_like
connected code15 source appearances: 91
connected code15 target appearances: 91
```

This supports the Q2h note that node `837` is a special universal-like node, but Q2j still does not prove what that class means.

## Path Recovery

The tool tested connected code15 pairs with two recovery graphs:

```text
direction_codes_without_15:
  BFS over adjacent table-neighbor edges whose packed4_0 code is 0-7 and matches the inferred table-coordinate direction.

chunked_non15_bfs:
  BFS over chunked_binary == 1 relations after excluding all packed4_0 == 15 edges.
```

Results:

```text
connected code15 total:          16,234
connected non-self code15 total: 15,930
self pairs:                         304
not recoverable without 15:      15,930
direction recovery ratio:             0
chunked non15 recovery ratio:         0
any recovery ratio:                   0
```

This argues against a simple "uncached fallback that can be recovered by the current 0-7 direction graph" interpretation. It also argues against treating the current `chunked_binary` non15 graph as enough to bypass code15.

## Prior Probe Context

Q2e/Q2f `369-370`:

```text
chunked values: 1 / 1
packed4_0 values: 15 / 15
runtime result: loader + extended observation pass
semantic effect observed: false
```

Q2g `59-837`:

```text
chunked values: 1 / 1
packed4_0 values: 1 / 3
runtime result: loader pass
semantic effect observed: false
```

Q2j keeps both probe outcomes compatible with the current evidence. Q2e/Q2f touched unresolved code `15` and produced no semantic signal; Q2g touched direction-like codes but also involved universal-like node `837`.

## Conclusion

```json
{
  "code15_interpretation": "ambiguous",
  "runtime_mutation_allowed": false,
  "packed4_mutation_allowed": false
}
```

What improved:

```text
code 15 is not a clean blocked sentinel
code 15 connected contexts are mostly long-distance in table coordinates
connected non-self code15 contexts are not recoverable through the current no-15 graphs
node 837 remains a tracked universal-like special node, not a proven anchor
```

What remains unproven:

```text
whether code 15 means blocked, no-op, special, overflow, or another semantic class
whether packed4_0 is authoritative at runtime
how packed4_0 interacts with chunked_binary
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
