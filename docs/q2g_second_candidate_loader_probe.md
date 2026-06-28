# Q2g Second Candidate Loader Probe

Date: 2026-06-28

This PR runs one risk-accepted A/B/A runtime probe for the second `chunked_binary` candidate `59-837`. The result is **Q2g Second Candidate Loader Probe Pass**. It is not a semantic pass.

## Scope

Allowed mutation:

```text
layer: chunked_binary
candidate: 59-837
offset 66605: 1 -> 0
offset 932331: 1 -> 0
changed_byte_count: 2
changed_cell_count: 2
```

Still unproven:

```text
map_setting_node_world_transform
chunked_binary gameplay semantics
packed4_0 directional-code meaning
AI / vision / pathing effect of this edge
broader map edits
```

## Evidence Directory

All generated evidence is stored outside the repository:

```text
D:\tfm2_q2a_evidence\q2g_second_candidate_probe\
```

No mutated binary, screenshot, ProcMon file, original payload, or exported runtime evidence is committed.

| File | Size | SHA-256 | Notes |
| --- | ---: | --- | --- |
| `map_setting.q2g.59_837.mutated.map_setting` | 1,451,980 | `d633092b25abf6bee3527f51249650ebe91d3912f25040dcff0728164819156a` | Two-byte Q2g B file. |
| `q2g_mutation_manifest.json` | 2,132 | `a78437844fc6387c5422e456b7e9757e37426c06fabe9c69ff1f5f15d14d97f2` | Q2g mutation manifest. |
| `q2g_second_candidate_probe_summary.json` | 14,621 | `ecb0ae7b7d9c631a126409eaaf5bc191dc8864d54f1d82aff5f37fb65dc9faab` | Final A/B/A summary. |
| `q2g_a1_stage_manifest.json` | 2,099 | `877e3acc14a03b329691352cfd5303399011525664d1acfd19e9b44a405cb85c` | A1 baseline staged. |
| `q2g_a1_screenshot_now.png` | 325,122 | `22f41f03602bd32c187fcdea3329d888dd84a90a8ca37a530ec79b9a3d76dee2` | A1 early 5v5 screenshot, actual timer about 00:05. |
| `q2g_a1_screenshot_0030.png` | 266,657 | `a3ed6d58ca8ee594fcbf11ddf6645882a000d2fa8f8b822f9ea5a4a7e9b7127f` | A1 mid observation screenshot, actual timer about 01:20. |
| `q2g_a1_screenshot_0300.png` | 287,979 | `b49fb527aa29b7a8529bd33fb390826898e0562ce923d93a3c4e19a04d9c927e` | A1 final observation screenshot, actual timer about 03:54. |
| `q2g_b_stage_manifest.json` | 2,755 | `a88158d2cf0755584a1eeee871a04e8c989cdb9798caf77752ae7c8b867a7be5` | B mutation staged. |
| `q2g_b_procmon.pml` | 3,317,076,607 | `f045549a1c1fcb4d277dbca7a77738df9d67ec3438e23bd5df2fcf650a82adef` | Full B ProcMon capture. |
| `q2g_b_procmon.csv` | 1,254,396,350 | `2bd97e8732d2e5a52064821a6aa3e956f23b175be1a274a44080b97784a3cce0` | Exported B ProcMon CSV. |
| `q2g_b_procmon_filtered.csv` | 1,773 | `deb1e8fa41588f3658beb38af5d1de635d95f71b201703796709e6f036e0572d` | Filtered B file-read proof. |
| `q2g_b_screenshot_now.png` | 337,766 | `21f1a22f57e414957168a1003d36d12ba1196504edf8edd09ac57b4591e1c170` | B early 5v5 screenshot, actual timer about 00:04. |
| `q2g_b_screenshot_0030.png` | 313,710 | `add160f8b26c4b6c9e16702b145f2e6e9cecd1c13d80b3d7f7ead5b2aa272bec` | B mid observation screenshot, actual timer about 01:06. |
| `q2g_b_screenshot_0300.png` | 271,620 | `fdc79b35e4bcf4e83b35b6b17898cfb44062d05dd4a8b2b59f260a57c85a3b1b` | B final observation screenshot, actual timer about 03:52. |
| `q2g_b_game_log_excerpt.txt` | 257 | `c232ec80a3930c5edcf4e3fd04a8c16a8524391f57987578a81cefcd5be73cdb` | Negative log-availability note; no reliable game log was found. |
| `q2g_a2_stage_manifest.json` | 2,099 | `8116fe473e82ea4d3c0ea1733061b1468f77746e33dd7f05cc47f6dae53e7a86` | A2 rollback staged. |
| `q2g_a2_procmon.pml` | 985,668,285 | `a2dc9babee30b4ce94e9d19adf63c8aaf40709aa725595d89eeabf98494cbe5f` | Full A2 ProcMon capture. |
| `q2g_a2_procmon.csv` | 374,661,082 | `bc24f620c8e9f4650d38ced84e602eef67c813975c5acbe40ef9f45daca1042c` | Exported A2 ProcMon CSV. |
| `q2g_a2_procmon_filtered.csv` | 1,778 | `b0ccfadc60a014e6cfa880d3722be8403a008aa0d1d0234ec7406b60af3fbd35` | Filtered A2 file-read proof. |
| `q2g_a2_screenshot_now.png` | 152,133 | `c78dc5fc985d0874aad89e1ed8aba4dbccbae6682adaee6541dbef3e01c800e0` | A2 pregame tactics screen; not counted as runtime map evidence. |
| `q2g_a2_screenshot_runtime_now.png` | 305,075 | `66ec7b00276c34f522760e45480d94edf0386741915528e78622dfd5b0a24f51` | A2 runtime screenshot, actual timer about 02:20. |
| `q2g_a2_screenshot_0300.png` | 296,716 | `e5c87d8ccbfc2463dac62f8270e6068a90de15bfb8063f8663857d0f6f40015e` | A2 final observation screenshot, actual timer about 03:59. |

## Mutation Manifest Check

`q2g_mutation_manifest.json` records:

```json
{
  "probe": "risk_accepted_second_candidate_symmetric_edge_mutation",
  "candidate": "59-837",
  "input_sha256": "6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0",
  "output_sha256": "d633092b25abf6bee3527f51249650ebe91d3912f25040dcff0728164819156a",
  "changed_offsets": [66605, 932331],
  "changed_cell_count": 2,
  "changed_byte_count": 2,
  "transpose_mismatch_before": 0,
  "transpose_mismatch_after": 0,
  "runtime_installed": false,
  "map_setting_node_world_transform": "unproven",
  "risk_label": "risk-accepted second candidate, not proven safe"
}
```

## A/B/A Result

| Run | map_setting | Target SHA-256 | Runtime result |
| --- | --- | --- | --- |
| A1 | Original byte-equivalent baseline | `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Pass. 5v5 entered and reached about 03:54; visible heroes, minions, towers, UI, and minimap appeared normal. |
| B | Q2g second-candidate two-byte mutation | `d633092b25abf6bee3527f51249650ebe91d3912f25040dcff0728164819156a` | Pass. 5v5 entered and reached about 03:52. ProcMon confirmed `CreateFile SUCCESS` and `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`, for the mutated staged file. No obvious global AI standstill, wall-sticking, path jitter, lane, loader, or runtime abnormality was observed. No clear local reversible gameplay effect was identified. |
| A2 | Original byte-equivalent rollback | `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Pass. Rollback restored the original staged SHA-256; 5v5 entered and reached about 03:59. ProcMon confirmed the restored staged file was read with `ReadFile SUCCESS`, `Offset: 0, Length: 1,451,980`. |

B-stage filtered ProcMon evidence includes:

```text
Process: TeamfightManager2.exe
PID: 3884
Path: D:\steam\steamapps\common\Teamfight Manager2\mods\tfm2_lol_map_spike\setting\map_setting.map_setting
Operation: CreateFile / ReadFile
Result: SUCCESS
ReadFile detail: Offset: 0, Length: 1,451,980
```

A2 rollback filtered ProcMon evidence includes:

```text
Process: TeamfightManager2.exe
PID: 12900
Path: D:\steam\steamapps\common\Teamfight Manager2\mods\tfm2_lol_map_spike\setting\map_setting.map_setting
Operation: CreateFile / ReadFile
Result: SUCCESS
ReadFile detail: Offset: 0, Length: 1,451,980
```

After the run, the local installed mod was reset to background-only:

```text
map_setting_override_installed: false
mods\tfm2_lol_map_spike\setting\map_setting.map_setting exists: false
```

## Conclusion

```text
Q2g Second Candidate Loader Probe Pass
semantic safety: not proven
node/world transform: unproven
broader map edits: not approved
```

This proves the loader can read and run the risk-accepted `59-837` two-byte `map_setting` mutation through a live 5v5 observation and rollback. It does not prove the semantic meaning of `chunked_binary`, the true node/world transform, or the safety of broader map edits.

Do not expand to multi-edge, region, visual-sync, or `packed4` mutation from this result alone.
