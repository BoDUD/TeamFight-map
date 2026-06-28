# Q2h Chunked Binary Probe Synthesis

Date: 2026-06-28

This PR synthesizes the two completed `chunked_binary` runtime probes and refines the next semantic target strategy. It does not generate a new mutated `map_setting`, does not install a runtime override, and does not run the game.

## Current State

```text
Q2e/Q2f 369-370:
  loader pass
  extended observation pass
  no semantic effect observed

Q2g 59-837:
  loader pass
  no semantic effect observed

shared boundary:
  chunked_binary semantics: unknown
  map_setting node/world transform: unproven
  packed4_0: still not decoded as a safe editable layer
  broader map edits: not approved
```

Both runtime probes prove that bounded two-byte `chunked_binary` mutations can be loaded, observed in 5v5, and rolled back. Neither probe produced a clear, local, reversible gameplay effect. Continuing to pick arbitrary third edges is therefore expected to have low information gain.

## Read-Only Analysis Tool

`tools/analyze_chunked_binary_probe_targets.py` reads the original local `map_setting`, classifies row and column sums, analyzes the two prior probe edges, and writes JSON diagnostics outside the repository.

Command used locally:

```powershell
python .\tools\analyze_chunked_binary_probe_targets.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2h_chunked_binary_probe_synthesis"
```

Output evidence:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\q2h_chunked_binary_probe_synthesis\chunked_binary_row_column_classes.json` | 12,955 | `3c9589223712c6cad52b667f4283d0a3f83d086b1076c57178888b95f85a637b` |
| `D:\tfm2_q2a_evidence\q2h_chunked_binary_probe_synthesis\prior_probe_target_analysis.json` | 5,417 | `7b4d9df953fea56df24f32d14180164504e397b9852448cbeefb6f185a2905c7` |
| `D:\tfm2_q2a_evidence\q2h_chunked_binary_probe_synthesis\next_candidate_strategy.json` | 2,105 | `f5a339aa46c3d467dc5923055d8c1b305d60e47ea6d6f7e995a79c14cd2c326f` |

The tool is read-only:

```text
mutated_map_setting_generated: false
runtime_install_modified: false
map_setting_override_installed: false
outputs_inside_repository: false
outputs_under_mods_tree: false
```

## Row And Column Classes

The `chunked_binary` layer remains a `900 x 900` binary relation:

```text
0 count: 703,026
1 count: 106,974
```

Row and column distributions are identical, consistent with the observed transpose symmetry:

```text
middle rows/columns:          782
sparse rows/columns:          112
near_universal rows/columns:    5
universal_like rows/columns:    1
```

The only `row_sum == 900` and `column_sum == 900` node is:

```text
node 837
xy_30x30: [27, 27]
class: universal_like
```

This matters because Q2g selected edge `59-837`. Its high row/column hamming score is real, but one endpoint is the unique universal-like node. That may mean the probe touched a default, sentinel-like, redundant, or otherwise low-observability relation rather than a normal local gameplay relation.

`packed4_0` still does not give a clean permission to mutate:

```text
P(packed4_0 == 15 | chunked_binary == 0): 0.1969713780
P(packed4_0 == 15 | chunked_binary == 1): 0.1517565016
P(chunked_binary == 0 | packed4_0 == 15): 0.8950681921
```

This is suggestive but not decisive. No `packed4` mutation is approved by this analysis.

## Prior Probe Classes

### Q2e/Q2f `369-370`

```text
offsets: 427536 / 427573
chunked values: 1 / 1
packed4_0 values: 15 / 15
row_sum 369: 132, class middle
row_sum 370: 147, class middle
row hamming: 61
column hamming: 61
runtime result: loader + extended observation pass
semantic effect observed: false
```

Possible explanation:

```text
The edit may not have been queried during observation, the node/world transform is unproven, and unchanged packed4_0 or other layers may dominate behavior.
```

### Q2g `59-837`

```text
offsets: 66605 / 932331
chunked values: 1 / 1
packed4_0 values: 1 / 3
row_sum 59: 27, class sparse
row_sum 837: 900, class universal_like
row hamming: 873
column hamming: 873
runtime result: loader pass
semantic effect observed: false
```

Possible explanation:

```text
The edge touches both a sparse node and the only universal-like node. Its contrast score was high, but it may still be low-observability if node 837 is a default, sentinel-like, redundant, or special-case relation row/column.
```

## Decision

The next action is:

```json
{
  "next_action": "continue_static_decoding",
  "reason": "Two runtime probes passed loader and live-observation gates but produced no semantic signal. Q2g also touches a universal-like row/column, so its high row/column contrast may have been less useful than expected."
}
```

Do not run a third runtime probe now.

If a future PR proposes a third candidate, it needs a separate risk review and should start with stricter constraints:

```text
avoid row_sum_900 or column_sum_900 universal-like nodes unless that is the explicit hypothesis
avoid already tested edges 369-370 and 59-837
changed_cell_count remains 2
changed_byte_count remains 2
chunked_binary only
no packed4 mutation
no visual synchronization
requires separate risk acceptance before runtime
```

Preferred static evidence before any new runtime probe:

```text
stronger packed4_0 decode or next-hop interpretation
node/world transform anchor
candidate class comparison against row and column histograms
```

Still rejected:

```text
multi-edge mutation
3x3 or region mutation
packed4_0 or packed4_1 mutation
formal LOL-map collision/path/spawn export
```
