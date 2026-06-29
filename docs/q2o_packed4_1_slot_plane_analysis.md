# Q2o Packed4_1 Slot Plane Analysis

This PR analyzes `packed4_1` under the `900x30 node-major` hypothesis at the individual slot-plane level. It is read-only: it does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not approve a third `chunked_binary` runtime probe, and does not mutate `packed4_0` or `packed4_1`.

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

`tools/analyze_packed4_1_slot_planes.py` reads the original local `map_setting`, reuses the Q2K/Q2L/Q2M no15 component and profile helpers, and writes JSON plus diagnostic PNGs outside the repository.

Example command:

```powershell
python .\tools\analyze_packed4_1_slot_planes.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2o_packed4_1_slot_planes"
```

The tool rejects repository outputs, runtime `mods` tree outputs, output paths inside the input tree, and generated-output hardlink/samefile aliases of the `map_setting` input.

## Evidence

The generated diagnostics are repository-external:

```text
D:\tfm2_q2a_evidence\q2o_packed4_1_slot_planes\
```

Core outputs:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `packed4_1_slot_value_histograms.json` | 153,541 | `ddbfb1c71890f57117f5963a20e4fee13af57327fd86e59fcc800b17789c44fc` |
| `packed4_1_slot_spatial_patterns.json` | 927,705 | `ba81eff1785209fc592340e69c2e9e3b787f645d6c54808547b7424039dbd8f6` |
| `packed4_1_slot_component_correlation.json` | 232,454 | `08d9750cf9945231b70be23b228ca1eb853670b8758ad2ed72dc41feb37583a9` |
| `packed4_1_slot_pair_correlation.json` | 29,374 | `080c38ad463f28c3f5f1ec0eb6f7e7933e97f69c36cd54af5db7e6d0dd9c923d` |
| `profile0001_slot_signature_analysis.json` | 8,975 | `dcf3c76ddbd9908a6f1cbb9e6f3903e2f347e82531626eb31e7cf8fbdd0b57a0` |
| `tracked_node_slot_profiles.json` | 10,422 | `b5b2926a77c7f356ba8cc59b85a9112000e27de6bf04b2e3e53d082e79e45a1f` |
| `q2o_packed4_1_slot_interpretation.json` | 2,109 | `a68459b16c751856ba639f9130b4659002f65a4a985cb08f81f5ba6b8fc44040` |
| `slot_masks\top_slot_value_masks_contact_sheet.png` | 16,673 | `ebfc7b06d6dc4ed788418407c17dcbfe4dc12409f3659c825275d75f18090d89` |

The tool also generated `208` repository-external slot/value mask PNGs under:

```text
D:\tfm2_q2a_evidence\q2o_packed4_1_slot_planes\slot_masks\
```

Input baseline:

```text
map_setting size: 1,451,980
map_setting sha256: 6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0
```

## Slot Profile Definition

Q2O keeps the Q2M node-major hypothesis:

```text
profile = packed4_1[node * 30 : node * 30 + 30]
```

The singleton profile remains:

```text
[8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
 8, 0, 8, 0, 8, 0, 8, 0, 8, 0,
 8, 0, 8, 0, 8, 0, 8, 0, 8, 0]
```

Observed signature:

```text
singleton_profile_node_count: 90
singleton_profile_matches_all_singletons: true
full_profile_singleton_exclusive: true
alternating_even_8_odd_0: true
slot_value_all_singleton_exclusive: false
singleton_only_slot_value_count: 0
```

This distinction matters. The complete 30-slot profile still identifies the no15 singleton set, but no individual slot/value is singleton-exclusive on its own.

## Slot Histograms

Per-slot value histograms show that the singleton values are usually shared with many large-component nodes:

```text
slot 0 value 8:
  total nodes: 754
  singleton nodes: 90
  large-component nodes: 664

slot 1 value 0:
  total nodes: 813
  singleton nodes: 90
  large-component nodes: 723

slot 27 value 0:
  total nodes: 900

slot 28 value 8:
  total nodes: 900

slot 29 value 0:
  total nodes: 900
```

That pattern supports a profile-level class descriptor candidate, not an independently editable slot bit.

## Spatial And Pair Signals

The tool writes table-coordinate masks for each observed slot/value and a contact sheet for the singleton profile values. Many singleton-profile slot values form broad complete-row-or-column-like masks because those individual values are shared with large-component nodes.

Top slot-pair observations:

```text
highest normalized mutual information:
  slots 16 / 23: 0.493071
  slots 10 / 18: 0.465813
  slots 12 / 26: 0.431478

highest same-value ratio:
  slots 27 / 29: 1.0
  slots 1 / 27: 0.903333
  slots 1 / 29: 0.903333
```

These are static table correlations only. They do not prove axis, layer, world transform, or gameplay semantics.

## Tracked Nodes

Tracked nodes include the prior runtime-probe endpoints and Q2L top bridge singleton nodes:

```text
369, 370, 59, 837, 126, 617, 654, 184, 773, 498
```

Key examples:

```text
node 369:
  component_role: singleton_component
  slot_profile: [8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0]
  code15_bridge_total_endpoint_count: 262

node 370:
  component_role: large_component
  slot_profile: [8, 0, 8, 0, 0, 0, 0, 3, 8, 0, 1, 0, 8, 6, 8, 0, 8, 3, 3, 0, 8, 0, 3, 0, 8, 0, 8, 0, 8, 0]

node 59:
  component_role: large_component
  row_class: sparse
  code15_bridge_total_endpoint_count: 0

node 837:
  component_role: large_component
  row_class: universal_like
  column_class: universal_like
  code15_bridge_total_endpoint_count: 180
```

This helps explain prior probes in static terms, but it does not prove why those probes had no visible runtime effect.

## Conclusion

Q2O result:

```json
{
  "packed4_1_slot_role": "slot_level_node_class_descriptor_candidate",
  "runtime_mutation_allowed": false,
  "packed4_mutation_allowed": false,
  "third_chunked_binary_runtime_probe_allowed": false,
  "map_editing_allowed": false,
  "next_recommended_step": "continue_static_decoding"
}
```

Q2O strengthens the static hypothesis that the full node-major `packed4_1` profile encodes or describes membership in the no15 singleton node class. It does not prove that any individual slot is an editable class bit, does not prove gameplay semantics, does not prove node/world transform, and does not approve mutation of `packed4_1`, `packed4_0`, `chunked_binary`, regions, collision, pathing, spawns, or visual sync.
