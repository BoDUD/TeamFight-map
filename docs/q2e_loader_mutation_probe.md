# Q2e Loader Mutation Probe

Date: 2026-06-26

This PR runs one risk-accepted A/B/A runtime probe for a two-byte `map_setting` mutation. The result is **Q2e Loader Mutation Probe Pass**. It is not a semantic pass.

## Scope

Allowed mutation:

```text
layer: chunked_binary
offset 427536: 1 -> 0
offset 427573: 1 -> 0
changed_byte_count: 2
changed_cell_count: 2
```

Still unproven:

```text
map_setting_node_world_transform
chunked_binary gameplay semantics
packed4_0 code 15 full meaning
AI / vision / pathing effect of this edge
```

## Evidence Directory

All generated evidence is stored outside the repository:

```text
D:\tfm2_q2a_evidence\minimal_mutation_probe\
```

No mutated binary, screenshot, ProcMon file, or original payload is committed.

| File | Size | SHA-256 | Notes |
| --- | ---: | --- | --- |
| `map_setting.q2e.mutated.map_setting` | 1,451,980 | `dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072` | Two-byte B file. |
| `mutation_manifest.json` | 1,806 | `9129d2c4dcf1b86b602bfd4928f096f4e1e21dc3053a6999c08888d39595d380` | Mutation manifest. |
| `q2e_a1_stage_manifest.json` | 1,877 | `a208a18d900d21c295447028c7dc8eb9edfb3bb5658d4525bbc7276f5ff16445` | A1 baseline staged. |
| `q2e_a1_screenshot.png` | 296,424 | `0af70dce919e03f06efee1c39152949435ccd477970b8f661ee04afa5ed47bd9` | A1 initial 5v5 screenshot. |
| `q2e_a1_screenshot_1min.png` | 297,481 | `b9c2bdead4e29bfe166b70b728ef5cdaefbb36ee6e67c44e26c9aeeb7b5346e4` | A1 reached 01:31. |
| `q2e_b_stage_manifest.json` | 1,994 | `3911498781daf4f6fd3aed7afe3960805d914d57b896730d21358db8199ae2c2` | B mutation staged. |
| `q2e_b_screenshot.png` | 264,254 | `6a96bea6bdbc0522b6016b7a20fb03946e360f2bbe85181b9713a5476fc81cc5` | B initial 5v5 screenshot. |
| `q2e_b_screenshot_1min.png` | 262,768 | `515c3bd797966a393ba37d12f7e80873e08c68fb21760c8261825ae3995d069d` | B reached 01:32. |
| `q2e_b_procmon.pml` | 2,647,285,882 | `96df0a23b3ac22ecf308be3273b8e850bb7017611d865363faf92725338d711e` | Full B ProcMon capture. |
| `q2e_b_procmon.csv` | 939,035,881 | `96b5bfe9053526418a191f5111e140a54ab1f714e416cdd9502de47aa7bef7ba` | Exported B ProcMon CSV. |
| `q2e_b_procmon_filtered.csv` | 3,293 | `2f8ec3aa0cc913b6f5420993c3ce7e229af94594a88724bf362523cc0feeab67` | Filtered B file-read proof. |
| `q2e_b_game_log_excerpt.txt` | 729 | `92bc17cc591405ccc7d64607639f9d145ded2198ea8359a90451ec6f0b6485ce` | B startup log excerpt. |
| `q2e_a2_stage_manifest.json` | 1,877 | `d0dc39b9f987d52421ac10cb64c8402829f3f6a87429c9c3ba8e9e0ca63ea627` | A2 rollback staged. |
| `q2e_a2_screenshot.png` | 263,175 | `0a945c509f067c112e63f1d0913ad7e0c3c206b5fd3506058792586321623c65` | A2 initial 5v5 screenshot. |
| `q2e_a2_screenshot_1min.png` | 306,440 | `92c5e1214a08cda56e6e2a99fb439610325717bf806a32a3ee40033c4ae422c3` | A2 reached 01:31. |
| `q2e_a2_procmon.pml` | 2,594,632,408 | `e72136897e439d72bac9706fdb8838d70bdc0a4c7dfb60ceaaff2b1166900df7` | Full A2 ProcMon capture. |
| `q2e_a2_procmon.csv` | 933,793,829 | `328c8634f95ffbb6290972b1590bb3e263a3587158df500a7d1558e9baf219bb` | Exported A2 ProcMon CSV. |
| `q2e_a2_procmon_filtered.csv` | 3,293 | `dd1eeaaef28dcd85cfa80d2f864927225a61325d1ff25c092d471fa873a32d1f` | Filtered A2 file-read proof. |
| `q2e_a2_game_log_excerpt.txt` | 726 | `98366fcaa27507b97aafe2ae0dbd0a4f1c7be9bc2cd7fd4b55befc75471e32b2` | A2 startup log excerpt. |
| `q2e_loader_mutation_probe_summary.json` | 12,278 | `c84d0bb71deaa3e44997c633cb17cdb8787b3b02ddd5210b1ee6b352eaba9e41` | Final A/B/A summary. |

`q2e_b_stage_manifest.json` is also included in `q2e_loader_mutation_probe_summary.json`. Its staged target SHA-256 is `dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072`.

## Mutation Manifest Check

`mutation_manifest.json` records:

```json
{
  "probe": "risk_accepted_minimal_symmetric_edge_mutation",
  "input_sha256": "6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0",
  "output_sha256": "dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072",
  "changed_offsets": [427536, 427573],
  "changed_cell_count": 2,
  "changed_byte_count": 2,
  "transpose_mismatch_before": 0,
  "transpose_mismatch_after": 0,
  "runtime_installed": false,
  "map_setting_node_world_transform": "unproven",
  "risk_label": "risk-accepted candidate, not proven safe"
}
```

## A/B/A Result

| Run | map_setting | Target SHA-256 | Runtime result |
| --- | --- | --- | --- |
| A1 | Original byte-equivalent baseline | `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Pass. 5v5 entered and reached 01:31; visible heroes, minions, towers, jungle/objective actors, UI, and minimap appeared normal. |
| B | Two-byte risk-accepted mutation | `dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072` | Pass. 5v5 entered and reached 01:32. ProcMon confirmed `CreateFile SUCCESS` and `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`, for the mutated staged file. No obvious global gameplay abnormality was observed. |
| A2 | Original byte-equivalent rollback | `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Pass. Rollback restored the original SHA-256; 5v5 entered and reached 01:31. ProcMon confirmed the restored staged file was read with `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`. |

B-stage filtered ProcMon evidence includes:

```text
Process: TeamfightManager2.exe
PID: 14696
Path: D:\steam\steamapps\common\Teamfight Manager2\mods\tfm2_lol_map_spike\setting\map_setting.map_setting
Operation: CreateFile / ReadFile
Result: SUCCESS
ReadFile detail: Offset: 0, Length: 1,451,980
```

A2 rollback filtered ProcMon evidence includes:

```text
Process: TeamfightManager2.exe
PID: 11120
Path: D:\steam\steamapps\common\Teamfight Manager2\mods\tfm2_lol_map_spike\setting\map_setting.map_setting
Operation: CreateFile / ReadFile
Result: SUCCESS
ReadFile detail: Offset: 0, Length: 1,451,980
```

## Conclusion

```text
Q2e Loader Mutation Probe Pass
semantic safety: not proven
```

This proves the loader can read and run one risk-accepted two-byte `map_setting` mutation through 5v5 startup, and that the staged file can be rolled back to the original SHA-256. It does not prove the semantic meaning of `chunked_binary`, the true node/world transform, or the safety of broader map edits.

Do not expand beyond this two-byte probe in this PR.
