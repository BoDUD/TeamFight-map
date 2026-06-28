# Q2n MapSetting Mask Visual Correlation

This PR correlates current `map_setting` structural masks with original visual map resources. It is read-only: it does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not approve a third `chunked_binary` runtime probe, and does not mutate `packed4_0` or `packed4_1`.

## Boundary

Current project status remains:

```text
runtime_mutation_allowed: false
packed4_mutation_allowed: false
third_chunked_binary_runtime_probe_allowed: false
map_editing_allowed: false
next_recommended_step: continue_static_decoding
```

The analysis uses `30x30` table-coordinate masks and original visual PNG resources. It is a heuristic visual correlation pass only; it is not node/world transform proof.

## Tool

`tools/correlate_map_setting_masks_with_visuals.py` reads the original local `map_setting`, derives structural masks from Q2K/Q2L/Q2M data, reads original visual PNG resources from repository-external paths, and writes diagnostics outside the repository.

Example command:

```powershell
python .\tools\correlate_map_setting_masks_with_visuals.py `
  --map-setting "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --asset-dir "D:\steam\steamapps\common\Teamfight Manager2" `
  --output-dir "D:\tfm2_q2a_evidence\q2n_map_setting_mask_visual_correlation"
```

The tool rejects repository outputs, runtime `mods` tree outputs, output paths inside source trees, and generated-output hardlink/samefile aliases of the `map_setting` or visual asset inputs.

## Evidence

The generated diagnostics are repository-external:

```text
D:\tfm2_q2a_evidence\q2n_map_setting_mask_visual_correlation\
```

Core outputs:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `structural_masks_manifest.json` | 1,664 | `5b71711e6067348e75c124c6a0ce71c73e10b9f8e9c8253cfa8a71e6624a2b4f` |
| `profile_0001_mask_30x30.png` | 2,266 | `4d5d9bdb3e9c40391b7eded01c5ad15a21b8c7d28881ebddcd871f334c331ad3` |
| `no15_large_component_mask_30x30.png` | 2,266 | `6a1b2554ba97288895714979d31639ea74692093629a5f1be17e7fc6313c3298` |
| `code15_bridge_endpoint_heatmap_30x30.png` | 3,601 | `2e9e823f4edce22e3516fe0ff32b31b524435135939b6443fdcc736c4ed7ca4d` |
| `packed4_0_direction_confidence_mask_30x30.png` | 2,898 | `98649544a28fcc8c35386db47a470948a611e25217d2c2f2c1375deafe6f4945` |
| `visual_resource_manifest.json` | 2,817 | `e84f1d119d7242c8ac45c7be67c7eb262ce6fb6aab35160f76230992f3591794` |
| `transform_score_summary.json` | 5,520 | `c0583fdaf068e7e0dbc2cd09ff29501f352a5ee907e5ad36112f9680b02a6c3d` |
| `q2n_visual_correlation_interpretation.json` | 1,561 | `986daf69a616ec33c6d561c055e4e28c52a89114026ad0e8cbdfd5662e922247` |

The tool also generated 24 repository-external overlay PNGs:

```text
overlay_profile0001_<transform>.png
overlay_large_component_<transform>.png
overlay_bridge_heatmap_<transform>.png
```

for all 8 square transforms.

Input baseline:

```text
map_setting size: 1,451,980
map_setting sha256: 6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0
```

## Visual Resources

Original visual resources were read from repository-external evidence extracts:

| Resource | Size | SHA-256 | Path |
| --- | ---: | --- | --- |
| `background_5v5` | 330,596 | `6f263bbfb81a7d869c8514f4407be63cc6d9d1abeb47a619f4d0fa2f8920151c` | `D:\steam\steamapps\common\Teamfight Manager2\stage1b_evidence\layer_probes\native_layer_extracts\background_5v5.png` |
| `bush_5v5` | 50,011 | `7f956914c69d68e14494406f91d93df921205d2322b4b0cc283fe1aa09860267` | `D:\steam\steamapps\common\Teamfight Manager2\stage1b_evidence\layer_probes\native_layer_extracts\bush_5v5.png` |
| `minimap_5v5_bg` | 17,843 | `eed2336e6f6e8f071100600c87681e701ba74e9e1952b53caacfd248bbdbfbe3` | `D:\steam\steamapps\common\Teamfight Manager2\stage1c_evidence\native_actor_reference\minimap_5v5_bg.png` |
| `wall_5v5` | 116,035 | `8c6d1e8411f4033ecc1be7eb06172dc2f91d9490be31e0ea8d7afb76e41e2821` | `D:\steam\steamapps\common\Teamfight Manager2\stage1b_evidence\layer_probes\native_layer_extracts\wall_5v5.png` |
| `wall_5v5_front` | 10,452 | `7f827df955b02ded817c6d602902501821a8272028e58256912bc04660137da6` | `D:\steam\steamapps\common\Teamfight Manager2\stage1b_evidence\layer_probes\native_layer_extracts\wall_5v5_front.png` |

No original visual payloads are committed.

## Structural Masks

Derived structural masks:

```text
profile_0001 node count: 90
large_component node count: 810
code15 bridge heatmap nonzero node count: 819
packed4_0 direction confidence nonzero node count: 810
node837 universal-like node count: 1
component_size_histogram:
  1: 90
  810: 1
```

Mask meanings:

```text
profile_0001: Q2m singleton-only node-major packed4_1 profile mask
large_component: Q2k/Q2l no15 weak component with 810 nodes
bridge_heatmap: normalized code15 endpoint degree heatmap
direction_confidence: adjacent packed4_0 0-7 direction-code presence ratio per source node
node837_universal_like: nodes with row_sum == column_sum == 900
```

## Transform Scoring

The tool evaluates these 8 square transforms:

```text
identity
rotate90
rotate180
rotate270
flip_x
flip_y
transpose
anti_transpose
```

Scores are heuristic and combine:

```text
profile_0001 boundary alignment
profile_0001 feature overlap / soft IoU
large component open-area overlap
bridge heatmap boundary / feature overlap
direction-confidence open-area overlap
node837 feature overlap
```

Observed ranking:

| Rank | Transform | Score |
| ---: | --- | ---: |
| 1 | `transpose` | `0.681203` |
| 2 | `identity` | `0.681138` |
| 3 | `flip_x` | `0.678038` |
| 4 | `rotate90` | `0.677930` |
| 5 | `rotate270` | `0.677567` |
| 6 | `flip_y` | `0.677441` |
| 7 | `anti_transpose` | `0.676902` |
| 8 | `rotate180` | `0.676840` |

Top-two margin:

```text
best: transpose
second: identity
margin: 0.000065
```

This margin is far too small to identify a reliable transform.

## Conclusion

Q2n result:

```json
{
  "visual_correlation_result": "ambiguous",
  "candidate_transform": "transpose",
  "candidate_margin": 0.000065,
  "node_world_transform": "unproven",
  "runtime_mutation_allowed": false,
  "packed4_mutation_allowed": false,
  "third_chunked_binary_runtime_probe_allowed": false,
  "map_editing_allowed": false,
  "next_recommended_step": "continue_static_decoding"
}
```

This PR does not prove `node_world_transform`. It only says the current structural masks do not produce a unique, high-margin visual alignment against the checked original map resources. Static decoding should continue; map editing, packed4 mutation, region editing, third runtime mutation, and visual-sync work remain disallowed.
