# Q2g Second Candidate Risk Acceptance

Date: 2026-06-27

This document defines the review gate for a possible second `chunked_binary` runtime probe. It does not generate a mutated `map_setting`, does not install a `map_setting` override, and does not run the game.

## Why Q2e/Q2f Are Not Enough

Q2e and Q2f proved a narrow loader and rollback property:

```text
same B file: Q2e 369-370 two-byte mutation
Q2e: reached 5v5 startup
Q2f: repeated the same B file and observed live 5v5 past 3:00
rollback: original SHA-256 restored in A2
```

They did not prove:

```text
chunked_binary gameplay semantics
map_setting node/world transform
which world location any source-target pair controls
whether a different pair will affect AI, vision, pathing, collision, or cached queries
whether broader map edits are safe
```

The next candidate therefore needs its own risk acceptance. Q2f is not permission to edit regions, add multiple edges, modify `packed4_0` / `packed4_1`, synchronize visual resources, or start a formal map exporter.

## Why 59-837 Is High Signal

`tools/select_q2f_semantic_probe_candidates.py` cataloged `59-837` as the highest-scoring second candidate, but explicitly marked it as not approved for runtime.

Recorded candidate:

```json
{
  "candidate": "59-837",
  "layer": "chunked_binary",
  "cells": [
    {
      "logical_coordinate": [837, 59],
      "serialized_byte_offset": 66605,
      "old": 1,
      "new": 0
    },
    {
      "logical_coordinate": [59, 837],
      "serialized_byte_offset": 932331,
      "old": 1,
      "new": 0
    }
  ],
  "row_sum_source": 27,
  "row_sum_target": 900,
  "row_signature_hamming_distance": 873,
  "column_signature_hamming_distance": 873,
  "packed4_0_forward": 1,
  "packed4_0_reverse": 3
}
```

This is higher signal than `369-370` because its row/column signatures differ sharply and the packed4 codes are non-15 directional-looking values. That may make a semantic effect easier to observe. It also makes the risk harder to reason about because the true world position and gameplay meaning remain unknown.

## Risk Acceptance

Risk acceptance for the next probe is:

```json
{
  "risk_acceptance": "accepted_for_one_controlled_second_candidate_probe",
  "candidate": "59-837",
  "layer": "chunked_binary",
  "cells": [
    {
      "logical_coordinate": [837, 59],
      "serialized_byte_offset": 66605,
      "old": 1,
      "new": 0
    },
    {
      "logical_coordinate": [59, 837],
      "serialized_byte_offset": 932331,
      "old": 1,
      "new": 0
    }
  ],
  "changed_cell_count": 2,
  "changed_byte_count": 2,
  "risk_label": "risk-accepted second candidate, not proven safe",
  "may_generate_mutated_binary_in_this_pr": false,
  "may_stage_runtime_in_this_pr": false
}
```

Allowed only in a later runtime PR:

```text
one repository-external B file
only offsets 66605 and 932331
only old values 1 -> new values 0
strict A/B/A with cold starts
ProcMon proof that B reads the staged mutated file
rollback to original SHA-256
```

Still forbidden:

```text
second runtime candidate without another review
multi-edge mutation
region mutation
packed4_0 mutation
packed4_1 mutation
visual resource synchronization
automatic runtime install from the mutation tool
semantic pass claim without a clear local reversible effect
```

## Dedicated Tool Gate

`tools/map_setting_mutate_q2g_second_candidate.py` is intentionally not a generalized offset mutator. Its CLI accepts input, output, manifest, and `--confirm-risk-accepted`; it does not accept arbitrary coordinates or offsets.

The tool is constrained to:

```text
candidate: 59-837
offset 66605: 1 -> 0
offset 932331: 1 -> 0
input SHA-256: 6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0
output/manifest outside repository
output not under any mods tree
input/output/manifest distinct and not hardlink aliases
diff exactly two bytes
output decodes
transpose_mismatch_count remains 0
runtime_installed: false
```

This PR only adds the tool and synthetic tests. It does not execute the tool against the real baseline and does not write a real Q2g B file.

## PR #15 Runtime Gate

If this risk acceptance is approved, a later PR may run:

```text
[spike] run risk-accepted second candidate map_setting probe
```

Runtime flow:

```text
A1: original byte-equivalent baseline
B : 59-837 two-byte mutation
A2: original byte-equivalent rollback
```

B must run to at least 3:00 unless a stop condition occurs, and it must capture fresh Process Monitor read proof for:

```text
TeamfightManager2.exe
mods\tfm2_lol_map_spike\setting\map_setting.map_setting
CreateFile SUCCESS
ReadFile SUCCESS
Offset: 0, Length: 1,451,980
```

The result name should be:

```text
Q2g Second Candidate Loader Probe
```

Do not call it a semantic pass unless a clear, local, reversible, explainable gameplay effect appears in B and disappears after A2 rollback.

Current conclusion after this PR:

```text
Q2g risk acceptance: accepted for one controlled second-candidate probe
mutated binary generated: false
runtime staged: false
semantic safety: not proven
node/world transform: unproven
broader map edits: not approved
```
