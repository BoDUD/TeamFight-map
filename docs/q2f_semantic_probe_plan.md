# Q2f Semantic Probe Plan

Date: 2026-06-27

Q2e proved one narrow loader property: Teamfight Manager 2 can read and run a risk-accepted two-byte `map_setting` mutation through 5v5 startup, and the installed file can be rolled back through A/B/A. Q2e did not prove the gameplay meaning of `chunked_binary`, the node/world transform, or broader map-edit safety.

This PR defines the next semantic probe gate. It does not generate a new mutated `map_setting`, does not install any `map_setting` override, and does not run the game.

## Current State

```text
Q2e Loader Mutation Probe: Pass
semantic safety: not proven
node/world transform: unproven
broader map edits: not approved
```

Possible `chunked_binary` interpretations remain:

```text
visibility / pairwise visible relation
reachability / pairwise reachable relation
AI or path query cache
```

## Guardrails

Allowed only after separate review:

```text
controlled A/B/A probes
minimum changed set for each approved probe
repository-external evidence files
strict rollback to the original SHA-256
```

Still forbidden:

```text
region edits
multi-edge edits
packed4_0 or packed4_1 edits
visual resource synchronization
new mutated binary in this PR
runtime staging in this PR
semantic pass claims
```

## Option A: Repeat Q2e With Longer Observation

This is the recommended next runtime PR because it does not introduce a second mutation target.

```text
A1: original byte-equivalent map_setting
B : same Q2e two-byte mutation at offsets 427536 and 427573
A2: original byte-equivalent map_setting
```

B should run longer than Q2e, at least to `3:00` or the first visible jungle/objective interaction. Record:

```text
lane behavior
hero AI return, chase, and retreat behavior
jungle and objective actors
path jitter, detours, wall-sticking, or idle behavior
loader/game logs
ProcMon read proof for B and A2
rollback SHA-256
```

Expected result name:

```text
Q2f Extended Observation Probe
```

Do not call it a semantic pass unless a clear, local, reversible, explainable gameplay effect appears and disappears again after A2.

## Option B: Catalog A Higher-Signal Second Candidate

`tools/select_q2f_semantic_probe_candidates.py` implements read-only candidate selection. It only writes JSON diagnostics outside the repository.

Command used locally:

```powershell
python .\tools\select_q2f_semantic_probe_candidates.py `
  --input "D:\steam\steamapps\common\Teamfight Manager2\stage_runtime_spike_evidence\runtime_map_loading_spike\source\map_setting" `
  --output-dir "D:\tfm2_q2a_evidence\q2f_semantic_probe_plan" `
  --top-n 8
```

Output evidence:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `D:\tfm2_q2a_evidence\q2f_semantic_probe_plan\q2f_semantic_probe_candidates.json` | 24,231 | `3ef16f633a42993a98a55b46aa9b7c6b9826e169d47896ce6c27fae459c78254` |
| `D:\tfm2_q2a_evidence\q2f_semantic_probe_plan\q2f_candidate_decision.json` | 899 | `6d1b847e64b98edba064e7aba588496e7b4a8bfffca60272cb273cb808db78f5` |

The selector rules are:

```text
layer: chunked_binary only
candidate unit: undirected source-target pair
old values: [1, 1]
planned new values: [0, 0]
changed_cell_count: 2
changed_byte_count: 2
preserve transpose symmetry
no diagonal self-edge
no packed4 mutation
no runtime install
no mutated binary generation
```

Scoring favors packed4 contrast and row/column signature differences:

```text
primary: packed4_0 15/non15 contrast
secondary: row and column signature hamming distance
tertiary: row-sum delta and packed4 directional code delta
```

Top cataloged candidate in the local run:

```json
{
  "candidate": "q2f_candidate_01",
  "edge": [59, 837],
  "cells": [
    {"logical_coordinate": [837, 59], "serialized_byte_offset": 66605, "old": 1, "new": 0},
    {"logical_coordinate": [59, 837], "serialized_byte_offset": 932331, "old": 1, "new": 0}
  ],
  "packed4_0_forward": 1,
  "packed4_0_reverse": 3,
  "packed4_0_contrast": "both_packed4_non15",
  "row_sum_source": 27,
  "row_sum_target": 900,
  "row_signature_hamming_distance": 873,
  "column_signature_hamming_distance": 873,
  "semantic_signal_score": 3421,
  "may_enter_runtime_probe": false
}
```

This candidate is not approved for runtime. It is cataloged only.

## Decision

```json
{
  "q2f_recommended_next_runtime_option": "A_repeat_q2e_369_370_extended_observation",
  "second_candidate_status": "cataloged_not_selected",
  "second_candidate_may_enter_runtime_probe": false
}
```

PR #13 should use Option A if the project continues immediately. Option B requires a separate risk-acceptance review before any second candidate can be mutated.

## Stop Conditions

Stop before widening scope if any future A/B/A probe shows:

```text
loader error
crash
failed 5v5 startup
unit, lane, tower, jungle, or objective spawn abnormality
AI wall-sticking, global detour, idle, or jitter
failed rollback to original SHA-256
ProcMon does not prove the intended staged file was read
```

This plan does not approve formal map geometry editing.
