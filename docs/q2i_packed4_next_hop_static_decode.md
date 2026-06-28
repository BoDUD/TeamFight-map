# Q2i Packed4 Next-Hop Static Decode

Date: 2026-06-28

This PR refines the static interpretation of `packed4_0`. It does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not select a third runtime candidate, and does not mutate `packed4`.

## Question

```text
Is packed4_0 likely to be a next-hop / direction / path-query table?
```

## Read-Only Tool

`tools/analyze_packed4_next_hop_semantics.py` reads the original local `map_setting`, keeps all payloads read-only, and writes JSON diagnostics outside the repository.

Command used locally:

```powershell
python .\tools\analyze_packed4_next_hop_semantics.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2i_packed4_next_hop_static_decode"
```

Output evidence:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\q2i_packed4_next_hop_static_decode\packed4_value_histogram.json` | 1,416 | `ebf8110b6314a43637fc377974db95e32dfc77f1f550acb82dacd1ea7337912e` |
| `D:\tfm2_q2a_evidence\q2i_packed4_next_hop_static_decode\packed4_direction_code_candidates.json` | 2,371 | `aaf6fdf3b832b0586b6b2a94163994fa6faf2e0e791b4065add4b2f52d1288a7` |
| `D:\tfm2_q2a_evidence\q2i_packed4_next_hop_static_decode\packed4_path_follow_samples.json` | 36,504 | `6101fc77ce23768ec3a3b2e3452e2a9a618a7a632d7ada6a8ea4aea742c3ea92` |
| `D:\tfm2_q2a_evidence\q2i_packed4_next_hop_static_decode\packed4_code15_analysis.json` | 1,375 | `6b7610ba2fcd6bd3e3cbea15a43b88330865fea3a177c1b4f5162df2517ca015` |
| `D:\tfm2_q2a_evidence\q2i_packed4_next_hop_static_decode\q2i_next_hop_interpretation.json` | 3,890 | `53128ceaf217c23f41ad9cc3cd3fb7fe9017fcceb621e53e050779d152ffb1cc` |

Safety:

```text
read_only: true
mutated_map_setting_generated: false
runtime_install_modified: false
map_setting_override_installed: false
outputs_inside_repository: false
outputs_under_mods_tree: false
```

## Value Distribution

`packed4_0` is a `900 x 900` 4-bit table. Observed values:

```text
0: 102,437
1:  97,875
2: 100,737
3:  99,689
4:  64,638
5:  62,108
6:  64,280
7:  63,526
15: 154,710
```

Values `8-14` do not appear in the observed `packed4_0` table.

## Direction Code Candidates

For adjacent source-target pairs, codes `0-7` show strong direction behavior:

```json
{
  "0": "E",
  "1": "S",
  "2": "W",
  "3": "N",
  "4": "SE",
  "5": "SW",
  "6": "NE",
  "7": "NW"
}
```

Purity:

```text
0: 0.908976
1: 0.908976
2: 0.908976
3: 0.908976
4: 1.0
5: 1.0
6: 1.0
7: 1.0
15: 0.136223
```

This is good evidence that `0-7` are direction-like. It is not enough to approve mutation because code `15` is unresolved and appears in both `chunked_binary == 0` and `chunked_binary == 1` contexts.

## Path-Follow Check

The tool used the inferred direction codes to walk non-adjacent connected pairs:

```text
connected_non_adjacent_pair_count: 104,302
tested_pair_count: 50,000
reached: 42,803
unresolved_code: 7,197
reached_ratio: 0.856060
```

Every sampled failure was caused by code `15`:

```json
{
  "15": 7197
}
```

This supports a partial next-hop interpretation:

```text
packed4_0 codes 0-7 are likely direction-like next-hop candidates
code 15 remains unresolved
```

It does not reach the threshold for a strong next-hop conclusion because path-follow does not reach `0.95`, and code `15` blocks a meaningful fraction of connected pairs.

## Code 15

Code `15` counts:

```text
chunked_binary == 0: 138,476
chunked_binary == 1:  16,234
total:                154,710
```

Probabilities:

```text
P(chunked_binary == 0 | packed4_0 == 15): 0.8950681921
P(packed4_0 == 15 | chunked_binary == 0): 0.1969713780
P(packed4_0 == 15 | chunked_binary == 1): 0.1517565016
```

Interpretation:

```text
code15: ambiguous_special_case
```

`15` is associated with blocked/unconnected relations often enough to be suspicious, but it is not a clean sentinel: it also appears for `chunked_binary == 1` and has very low adjacent-direction purity.

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

This keeps both earlier outcomes compatible with the current interpretation. Q2e/Q2f touched unresolved code `15` in both directions; Q2g touched direction-like codes but also involved the universal-like node `837` identified in Q2h.

## Conclusion

```json
{
  "packed4_0_interpretation": "ambiguous",
  "runtime_mutation_allowed": false
}
```

What improved:

```text
codes 0-7 now have strong static direction-code evidence
path-follow works for 85.606% of sampled non-adjacent connected pairs
code 15 is isolated as the major unresolved obstacle
```

What remains unproven:

```text
code 15 semantics
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
```

Recommended next step:

```text
continue_static_decoding
```
