# Q2q Profile Family Visual Correlation

This PR correlates Q2P asymmetric exact `packed4_1` profile-family masks with original map visuals. It is read-only: it does not generate a mutated `map_setting`, does not install a runtime override, does not run the game, does not approve a third `chunked_binary` runtime probe, and does not mutate `packed4_0` or `packed4_1`.

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

`tools/correlate_profile_family_masks_with_visuals.py` re-derives Q2P exact profile families from the original local `map_setting`, selects asymmetric exact-family masks, and scores them against original visual resources across the eight square transforms.

Example command:

```powershell
python .\tools\correlate_profile_family_masks_with_visuals.py `
  --map-setting "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --asset-dir "D:\steam\steamapps\common\Teamfight Manager2" `
  --output-dir "D:\tfm2_q2a_evidence\q2q_profile_family_mask_visual_correlation"
```

The tool rejects repository outputs, runtime `mods` tree outputs, repository-internal visual assets, visual assets under runtime `mods` trees, output paths inside the input tree, and generated-output hardlink/samefile aliases of the `map_setting` or visual inputs.

## Evidence

The generated diagnostics are repository-external:

```text
D:\tfm2_q2a_evidence\q2q_profile_family_mask_visual_correlation\
```

Core outputs:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `profile_family_visual_resource_manifest.json` | 2,835 | `d05a80aaf990c5354d4d751511015c1988d5a83f2a2160fb4d021ec7d8b0a047` |
| `profile_family_anchor_candidate_manifest.json` | 155,942 | `fd0643366335700377d05e205d5ea16ba8ba92d11bc806e2f634cad58e42a473` |
| `profile_family_transform_score_summary.json` | 186,797 | `1fc7f19d51dd5fa89c7b392f2ababbbdd13e1b0041517a34fb09e0cfdb57ef0e` |
| `per_family_transform_rankings.json` | 397,222 | `54a2b05f36d4ea974332af7cbd419fc2acf9020dbae515c52a5751713f68fa6f` |
| `aggregate_transform_vote_summary.json` | 184,830 | `8626e8eb26f7c6825c565174dc5e8f8d7009eee20574d3652939b7d8a95c9e0f` |
| `q2q_profile_family_visual_correlation_interpretation.json` | 2,139 | `13bca932166394c1a6d6894e169e3876384397a435b353e979e83ef089e6f289` |

The tool also generated `80` repository-external overlay PNGs for the top `10` profile families:

```text
D:\tfm2_q2a_evidence\q2q_profile_family_mask_visual_correlation\family_mask_overlays\
```

Input baseline:

```text
map_setting size: 1,451,980
map_setting sha256: 6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0
```

## Candidate Masks

Q2Q reuses Q2P's asymmetric exact-family candidate definition:

```text
small asymmetric exact packed4_1 profile-family masks
not singleton-only
may be useful only for read-only visual correlation
```

Real input candidate count:

```text
candidate_count: 134
```

These masks are not runtime anchors and are not mutation targets.

## Per-Family Transform Rankings

Each candidate family is scored across:

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

Top candidate examples from the Q2P ordering:

| Family | Nodes | Best transform | Second transform | Margin | Best score | Second score |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| `family_0120` | 2 | `rotate90` | `rotate270` | `0.006399` | `0.222494` | `0.216095` |
| `family_0112` | 2 | `anti_transpose` | `rotate270` | `0.006907` | `0.347870` | `0.340963` |
| `family_0023` | 5 | `rotate180` | `flip_y` | `0.002787` | `0.377417` | `0.374630` |
| `family_0042` | 4 | `rotate270` | `anti_transpose` | `0.000000` | `0.604246` | `0.604246` |
| `family_0049` | 3 | `transpose` | `rotate90` | `0.004615` | `0.387907` | `0.383292` |

No top family has a strong individual transform margin.

## Aggregate Vote

Weighted aggregate votes:

```json
{
  "anti_transpose": 0.033502,
  "flip_x": 0.032973,
  "flip_y": 0.024869,
  "identity": 0.005239,
  "rotate180": 0.016575,
  "rotate270": 0.014356,
  "rotate90": 0.048683,
  "transpose": 0.013787
}
```

Aggregate result:

```text
best_transform: rotate90
second_transform: anti_transpose
aggregate_margin: 0.015180
best_vote_share: 0.256246
```

This fails the Q2Q single-transform threshold:

```text
required aggregate_margin >= 0.03
required best_vote_share >= 0.60
```

## Robustness

Subset results:

| Subset | Result | Best | Second | Margin | Best vote share |
| --- | --- | --- | --- | ---: | ---: |
| `all_resources` | `ambiguous` | `rotate90` | `anti_transpose` | `0.015180` | `0.256246` |
| `wall_only` | `ambiguous` | `anti_transpose` | `rotate180` | `0.012206` | `0.252490` |
| `bush_only` | `ambiguous` | `rotate90` | `rotate180` | `0.001959` | `0.170526` |
| `minimap_only` | `ambiguous` | `rotate270` | `flip_y` | `0.000153` | `0.246140` |
| `background_only` | `ambiguous` | `rotate270` | `rotate180` | `0.002249` | `0.203832` |
| `without_top_5_high_degree_families` | `ambiguous` | `rotate90` | `flip_x` | `0.008188` | `0.235539` |
| `without_singleton_family` | `ambiguous` | `rotate90` | `anti_transpose` | `0.015180` | `0.256246` |

The subsets do not converge on one transform. Q2Q therefore does not promote any transform to a reliable node/world candidate.

## Conclusion

Q2Q result:

```json
{
  "q2q_result": "ambiguous",
  "candidate_transform": "none",
  "node_world_transform": "unproven",
  "runtime_mutation_allowed": false,
  "packed4_mutation_allowed": false,
  "third_chunked_binary_runtime_probe_allowed": false,
  "map_editing_allowed": false,
  "next_recommended_step": "continue_static_decoding"
}
```

Q2Q shows that Q2P's asymmetric exact-family masks are sharper than Q2N's coarse structural masks, but they still do not produce a robust visual transform. It does not prove gameplay semantics, does not prove node/world transform, does not approve any runtime probe, and does not approve mutation of `packed4_1`, `packed4_0`, `chunked_binary`, regions, collision, pathing, spawns, or visual sync.
