# Q2f Extended Observation Probe

Date: 2026-06-27

This PR repeats the same Q2e risk-accepted `369-370` two-byte `map_setting` mutation and extends live 5v5 observation past 3:00. The result is **Q2f Extended Observation Probe Pass**. It is not a semantic pass.

## Scope

Reused Q2e mutation:

```text
layer: chunked_binary
edge: 369-370
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
second candidate 59-837 runtime safety
broader map edits
```

## Evidence Directory

All generated evidence is stored outside the repository:

```text
D:\tfm2_q2a_evidence\q2f_extended_observation_369_370\
```

No mutated binary, screenshot, ProcMon file, original payload, or exported runtime evidence is committed.

| File | Size | SHA-256 | Notes |
| --- | ---: | --- | --- |
| `q2f_extended_observation_summary.json` | 14,035 | `5d144efd6e24af63c1545442e1596243f122a5b6f9c60acf0a35259ea61d823e` | Final A/B/A summary. |
| `q2f_a1_stage_manifest.json` | 1,949 | `3326359c03abed3c301fb38f19e979c0b6563a4f480e9638fc29b13bdf9e86c4` | A1 baseline staged. |
| `q2f_a1_screenshot_0001.png` | 265,634 | `dcb3861badeed326c73828e72ec4ce928b787140520ec7f233708205d2fabc93` | A1 early 5v5 screenshot. |
| `q2f_a1_screenshot_0030.png` | 331,743 | `abb3bc113cc399a758828699ef74d6fe8ebe6781b935fe5c14f9d1d21d8ecec4` | A1 mid observation screenshot, actual timer about 00:52. |
| `q2f_a1_screenshot_0300.png` | 292,865 | `9df290cf88452b6545c22fe883e6490004f2d2f15c0c635db53d3dae8276e9dc` | A1 final observation screenshot, actual timer about 02:59. |
| `q2f_b_stage_manifest.json` | 2,216 | `41ba775341fd786d6e40544fb1ee90312f9408059a151c40be9402043c1417c3` | B mutation staged. |
| `q2f_b_procmon.pml` | 2,640,179,560 | `fee5ea19f14fba0d5290cdc3cd2c93d6e976dbd381c9bedbf9318b15d7b14783` | Full B ProcMon capture. |
| `q2f_b_procmon.csv` | 612,282,352 | `b2349292fe1bddec9e52f5337de65e84d5e64612e79e90fc20b3ea43a1d5c368` | Exported B ProcMon CSV. |
| `q2f_b_procmon_filtered.csv` | 1,778 | `3e582c795154421e49724970572aacd31dcb3b9ad500462a4eebe7b51592f5b3` | Filtered B file-read proof. |
| `q2f_b_screenshot_0001.png` | 345,437 | `4e9a680bac6ec92f87ef44bfe7663470b448cc647200336b1e4731b4212df00b` | B early 5v5 screenshot, actual timer about 00:04. |
| `q2f_b_screenshot_0030.png` | 247,475 | `92482ea92f71a6c87bbd146e4032a46f2bb970f786b93edc1dfb4dcf960daf57` | B mid observation screenshot, actual timer about 01:06. |
| `q2f_b_screenshot_0300.png` | 317,369 | `d06612e45cf1fb1f6dcf86a8a22e7d687fb1431d87cfc5d262abf2edc4804455` | B final observation screenshot, actual timer about 03:59. |
| `q2f_b_game_log_excerpt.txt` | 285 | `1f70f64a59ddeaa4234d5eadbcef5d3930dd59e623ac36d0b6896c0e2c0084cc` | Negative log-availability note; no reliable game log was found. |
| `q2f_a2_stage_manifest.json` | 1,949 | `323dccacadd3bf8ed232f361325ca1db97d1dcac965bb60f6710493ff89a1ccf` | A2 rollback staged. |
| `q2f_a2_procmon.pml` | 2,201,540,265 | `845e7006a072f1ebe65b4c111e2ca214a872f3345f3a785cad5b68c0a1b88e05` | Full A2 ProcMon capture. |
| `q2f_a2_procmon.csv` | 831,304,688 | `4cd35ca965405999cfe08843f5b5e5aca35f02c0e62bcec11e7e7705788fb323` | Exported A2 ProcMon CSV. |
| `q2f_a2_procmon_filtered.csv` | 1,778 | `9923f3c58b431dfed4e40573de4cb5fb8508b23f9cd7110516b0d0b118610299` | Filtered A2 file-read proof. |
| `q2f_a2_screenshot_now.png` | 338,693 | `5bde71f66ee75716f789bf5ee9ca644c3cf36bb1ba94488516a91fad52d0c8fb` | A2 early 5v5 screenshot, actual timer about 00:03. |
| `q2f_a2_screenshot_0030.png` | 264,237 | `e63c7f74ba75caeb51e5d28d1d1eba9308b788cdeb0a632f8540400a179cb9d4` | A2 mid observation screenshot, actual timer about 00:57. |
| `q2f_a2_screenshot_0300.png` | 257,005 | `fd54db78f63e6cc1e9764c6362aaa0145685d1403871bce351daa43d75454db4` | A2 final observation screenshot, actual timer about 03:23. |

The reused B file remains the Q2e external mutation file:

```text
D:\tfm2_q2a_evidence\minimal_mutation_probe\map_setting.q2e.mutated.map_setting
SHA-256: dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072
```

## A/B/A Result

| Run | map_setting | Target SHA-256 | Runtime result |
| --- | --- | --- | --- |
| A1 | Original byte-equivalent baseline | `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Pass. 5v5 entered and reached approximately 02:59. Heroes, minions, towers, UI, and minimap appeared normal. |
| B | Same Q2e two-byte mutation | `dd499ad3b531f4ba932bba2eecf055a792ac45991da5cabd2f52ac16e2718072` | Pass. 5v5 entered and reached approximately 03:59. Heroes, minions, towers, UI, and minimap remained visibly active; no obvious global AI standstill, wall-sticking, path jitter, loader warning, or runtime abnormality was observed. |
| A2 | Original byte-equivalent rollback | `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0` | Pass. Rollback restored the original staged SHA-256, 5v5 entered, and observation reached approximately 03:23. No B-stage residual abnormality was observed. |

B-stage filtered ProcMon evidence includes:

```text
Process: TeamfightManager2.exe
PID: 18056
Path: D:\steam\steamapps\common\Teamfight Manager2\mods\tfm2_lol_map_spike\setting\map_setting.map_setting
Operation: CreateFile / ReadFile
Result: SUCCESS
ReadFile detail: Offset: 0, Length: 1,451,980
```

A2 rollback filtered ProcMon evidence includes:

```text
Process: TeamfightManager2.exe
PID: 27704
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
Q2f Extended Observation Probe Pass
semantic safety: not proven
node/world transform: unproven
second candidate 59-837: blocked
broader map edits: not approved
```

This extends Q2e from a short loader mutation startup proof to a longer live observation of the same two-byte mutation. It still does not prove the semantic meaning of `chunked_binary`, the true node/world transform, or the safety of broader map edits.

Do not expand to a second candidate, multi-edge mutation, region edit, or `packed4` mutation from this result alone.
