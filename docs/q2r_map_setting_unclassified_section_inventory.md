# Q2r MapSetting Unclassified Section Inventory

This PR inventories the original `map_setting` binary for unclassified sections outside the currently known structural layers. It is read-only: it does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not approve a third `chunked_binary` runtime probe, and does not mutate `chunked_binary`, `packed4_0`, or `packed4_1`.

## Boundary

Current project status remains:

```text
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

Q2N and Q2Q both produced ambiguous visual-correlation results. Q2R therefore stops adding visual masks and instead checks whether the binary has residual or unclassified spans that might contain a more direct anchor surface.

## Tool

`tools/analyze_map_setting_unclassified_sections.py` parses the original local `map_setting` through the known structural framing:

```text
chunked_binary
packed4_0
packed4_1
```

It then inventories any residual bytes after those layers and scans residual/unclassified spans as `uint8`, `int8`, `uint16`, `int16`, `uint32`, `int32`, `float32`, `bitset`, and `packed4` candidates. Candidate findings are diagnostic only.

Example command:

```powershell
python .\tools\analyze_map_setting_unclassified_sections.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2r_map_setting_unclassified_sections"
```

The tool rejects repository inputs/outputs, runtime `mods` tree outputs, output paths inside the input tree, and generated-output hardlink/samefile aliases of the input.

## Evidence

The generated diagnostics are repository-external:

```text
D:\tfm2_q2a_evidence\q2r_map_setting_unclassified_sections\
```

Input baseline:

```text
map_setting size: 1,451,980
map_setting sha256: 6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0
```

Core outputs:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `map_setting_section_inventory.json` | 2,310 | `e756a696357c9e566a20a01d4ea2c8fb6814e3305e7e80cf4dd242ad1de19506` |
| `map_setting_residual_span_entropy.json` | 837 | `b918ba6968fc3c110a9cf5abd71848baf644c46bbadde983a7fcda263e1becec` |
| `dimensioned_array_candidates.json` | 836 | `cd0e145b91d6ca239d09384bf6d3d1cabb077a56ccab10d3a49609b0bffd9546` |
| `coordinate_like_value_candidates.json` | 840 | `f349bc0646cd4d403deed1b19cb3c2661a4230d99be7fb02f1ca054ea7d9b41c` |
| `cross_layer_index_reference_candidates.json` | 846 | `72594ed38a887086ddced32b07dd9eb102154646bd21296f30252b265f285f7a` |
| `tracked_node_unclassified_context.json` | 7,303 | `ed249a984b3a67b89606cff2a49cb18edfe76136f1f24db8ad124d5206edde5c` |
| `q2r_unclassified_section_interpretation.json` | 1,758 | `aa83c3a786126837ba1dfb1dc18cbafa513067fd8327722bab017443927bdffc` |

No candidate PNG masks were generated for the real baseline:

```text
candidate_mask_count: 0
```

## Section Inventory

The real baseline is fully consumed by the three known structural layers:

| Section | Kind | Offset | End | Length | Element count | Shape |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `chunked_binary` | `known_chunked_binary` | 0 | 1,033,448 | 1,033,448 | 810,000 | `900x900` |
| `packed4_0` | `known_packed4_0` | 1,033,448 | 1,438,464 | 405,016 | 810,000 | `900x900` |
| `packed4_1` | `known_packed4_1` | 1,438,464 | 1,451,980 | 13,516 | 27,000 | `900x30`, `30x30x30` |

Result:

```text
section_count: 3
known_section_count: 3
residual_span_count: 0
```

## Candidate Scans

Because there are no residual/unclassified spans in the real baseline, Q2R found no additional candidate arrays or direct anchors:

```text
dimensioned_array_candidate_count: 0
coordinate_like_candidate_count: 0
cross_layer_reference_candidate_count: 0
```

Synthetic tests still cover the scanner behavior for appended residual spans, including coordinate-like arrays and `900`-length node-index-like arrays. Those tests are safety and behavior coverage only; they are not evidence that the real baseline contains such spans.

## Tracked Context

The tool records tracked-node context for:

```text
369, 370, 59, 837, 126, 617, 654, 184, 773, 498
```

This context remains diagnostic. Q2R found no unclassified span that references these nodes, the singleton nodes, the large no15 component, the universal-like node, or the high bridge-degree nodes.

## Conclusion

Q2R result:

```json
{
  "unclassified_anchor_candidates_found": false,
  "node_world_transform": "unproven",
  "runtime_mutation_allowed": false,
  "packed4_mutation_allowed": false,
  "third_chunked_binary_runtime_probe_allowed": false,
  "map_editing_allowed": false,
  "next_recommended_step": "continue_static_decoding"
}
```

Q2R closes the "look for residual map_setting anchor spans" route for the current structural framing: the known layers consume the full file. It does not prove gameplay semantics, does not prove node/world transform, does not approve any runtime probe, and does not approve mutation of `chunked_binary`, `packed4_0`, `packed4_1`, regions, collision, pathing, spawns, or visual sync.
