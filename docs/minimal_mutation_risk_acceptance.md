# Minimal Mutation Risk Acceptance

Date: 2026-06-26

This document is a review gate for deciding whether the project may run one risk-accepted, reversible `map_setting` mutation probe without a proven node/world anchor. It does not claim that the candidate is safe. It does not install, stage, or generate a mutated runtime file by itself.

## Current State

The no-risk proof routes have been exhausted:

```text
public SDK/runtime anchor: not found
offline bundle/setting anchor: not found
visual background grid: background UV only, not node/world proof
```

Current project state remains:

```text
map_setting_node_world_transform: unproven
candidate_369_370: blocked
mutation PR: not allowed by current evidence
```

## Proven

- The loader reads a local `asset/base/setting/map_setting` override when it is staged as `setting/map_setting.map_setting`.
- The known local `map_setting` baseline can decode and re-encode byte-identically.
- `chunked_binary` is not a transitive connected-component closure under the current row-signature check.
- Candidate edge `369-370` has both directions set to `1`.
- Mutating both directed cells together can preserve transpose symmetry.
- The current matrix is not globally constrained by a 180-degree node-rotation invariant.
- The exact candidate bytes are known:

```text
[source=369,target=370] logical coordinate [370,369] -> offset 427536
[source=370,target=369] logical coordinate [369,370] -> offset 427573
```

## Not Proven

- The true game-world position of nodes `369` and `370`.
- The gameplay meaning of `chunked_binary`.
- Whether changing this relation affects AI, vision, pathing, collision, or any other gameplay behavior.
- The complete meaning of `packed4_0` code `15`.
- Whether a two-byte `chunked_binary` change should also update another private table that has not been decoded.
- Whether the changed edge is low traffic or visually located where the background probe label appeared.

## Risk Acceptance Decision

This repository accepts one controlled probe only as a risk-accepted experiment, not as a safety-proven mutation.

```json
{
  "risk_acceptance": "accepted_for_one_controlled_probe",
  "allowed_mutation": {
    "layer": "chunked_binary",
    "candidate": "369-370",
    "cells": [
      {
        "logical_coordinate": [370, 369],
        "source_node": 369,
        "target_node": 370,
        "offset": 427536,
        "old": 1,
        "new": 0
      },
      {
        "logical_coordinate": [369, 370],
        "source_node": 370,
        "target_node": 369,
        "offset": 427573,
        "old": 1,
        "new": 0
      }
    ],
    "changed_cell_count": 2,
    "changed_byte_count": 2,
    "risk_label": "risk-accepted candidate, not proven safe"
  },
  "not_allowed": [
    "any packed4_0 change",
    "any packed4_1 change",
    "any visual map change",
    "any broad region edit",
    "any second candidate edge",
    "any permanent install",
    "any mutation without A/B/A rollback proof"
  ]
}
```

## Tooling Gate

`tools/map_setting_mutate_symmetric_edge.py` may generate one repository-external output file only when all of the following are true:

- The caller passes `--confirm-risk-accepted`.
- The input SHA-256 is exactly `6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0`.
- The input, output, and manifest paths are outside the repository.
- The input, output, and manifest paths are distinct and not hardlink/samefile aliases.
- The bytes at offsets `427536` and `427573` are both `1`.
- The only byte changes are `427536: 1 -> 0` and `427573: 1 -> 0`.
- The output decodes successfully through the existing structural decoder.
- `transpose_mismatch_count` remains `0` after the mutation.
- The manifest records `runtime_installed: false`.

The tool must not install the output into the game.

When this gate is approved, the next PR may generate the repository-external B file with:

```powershell
python .\tools\map_setting_mutate_symmetric_edge.py `
  --input "D:\path\to\original\map_setting.map_setting" `
  --output "D:\tfm2_q2a_evidence\minimal_mutation_probe\map_setting.q2e.mutated.map_setting" `
  --manifest "D:\tfm2_q2a_evidence\minimal_mutation_probe\mutation_manifest.json" `
  --confirm-risk-accepted
```

Do not run this command as part of the risk-acceptance PR unless review explicitly requests a local dry run. Running it creates a mutated binary and therefore belongs with the next A/B/A probe evidence.

## PR #11 Runtime Gate

If this risk acceptance is approved, the next PR may run exactly one A/B/A runtime probe:

```text
A1: original byte-equivalent map_setting
B : two-byte risk-accepted mutation at 427536 and 427573 only
A2: original byte-equivalent map_setting restored
```

B-stage evidence must include:

- Process Monitor proof that `TeamfightManager2.exe` reads the mutated `map_setting`.
- Successful 5v5 entry.
- No loader error.
- No obvious spawn, tower, minion-lane, jungle, objective, or hero-AI abnormality.
- Screenshot or short video.
- Game log.
- Mutated output SHA-256.
- A2 rollback proof restoring the original SHA-256.

The result name must stay conservative:

```text
Q2e Loader Mutation Probe Pass
```

Do not call it `Semantic Mutation Pass` unless a clear, local, reversible, and explainable gameplay effect is observed and disappears after A2 rollback.
