# Runtime Node Anchor Probe Plan

Date: 2026-06-26

This note follows the Q2c-1 grid-background captures. It defines the next read-only gate before any `map_setting` bit mutation.

## Current Evidence

Repository-external evidence lives at:

```text
D:\tfm2_q2a_evidence\map_setting_transform_validation\
  runtime_grid_probe_screenshot_blue_candidate.png
  runtime_grid_probe_screenshot_red_base.png
  runtime_anchor_measurements.json
```

Local evidence hashes:

```text
runtime_grid_probe_screenshot_blue_candidate.png:
  7f8f4b1907f56e2077ffba7924850fa7fc0e19a53d1abb8c165e5b2ca8eca2c6

runtime_grid_probe_screenshot_red_base.png:
  97c996833a5559fbd4c07bfb883b22f5d47413ee6c48b627b826e20b8ef6ee7c

runtime_anchor_measurements.json:
  91c3b7211fa3f8179f0d39623efd231dbc09f6676130a2206772b50fe3131056
```

The captures prove that the visual `background_5v5` probe loads, remains square in the observed camera view, and renders under gameplay actors, walls, towers, and UI. They also show the pre-rendered `rotate180` candidate labels.

The captures do not prove that binary nodes `369` and `370` control that world location. The labels are pixels in the background PNG.

Current conclusions:

```text
runtime_background_uv_calibration: pass_partial_two_captures
probe_transform_rendered: rotate180
map_setting_node_world_transform: unproven
candidate_mutation_approved: false
```

## Required Next Gate

The next PR must be read-only and should prove at least one independent node/world anchor. Acceptable evidence includes one of:

- A runtime SDK or debug overlay that draws a point derived from `map_setting.visible_view` or `map_setting.path` directly in world/UI space.
- A logged runtime value mapping a known world entity or camera bound to the same coordinate system used by `map_setting`.
- A decoded original data field that maps a known entity position, wall edge, base center, or path cell to a specific `30x30` node.

The probe may use a DLL only if it remains read-only and does not modify `scene`, `map_setting`, pathing, actors, AI, or assets. If the public SDK does not expose a draw/log API for these anchors, record that as the result instead of guessing.

## SDK Observations

The local SDK template exposes:

```rust
impl ModExtension for MyModExtension {
    fn post_update(&self, scene: &mut Scene, ui: &mut GameUI, assets: &mut Assets, dt: f32) {
        // Pattern-match on `scene` to react to specific game scenes.
    }
}
```

No public example in the installed SDK or adjacent local `rift_manager` source demonstrates a supported world-space drawing API. The older `rift_manager` DLL source is a no-op extension and does not prove runtime anchor drawing.

Therefore the next implementation step is API discovery:

1. Build a minimal read-only extension from the SDK template.
2. Determine whether `Scene`, `GameUI`, or `Assets` exposes a safe text/draw/log surface.
3. If a surface exists, render or log a few independent anchors without modifying gameplay.
4. If no surface exists, document the blocker and continue with offline decoded anchors instead.

## Mutation Is Still Blocked

Do not create a mutated `map_setting` until all are true:

- `map_setting_node_world_transform` is proven by an independent anchor.
- Candidate `369-370` is re-evaluated against the proven world location.
- The candidate is away from major lanes, towers, base entrances, objective pits, jungle camps, functional brush, and high-traffic AI paths.
- The mutation manifest includes exact byte offsets and rollback SHA-256.
- A/B/A runtime validation is planned before any broader edit.

The latest preflight also checks 180-degree node rotation:

```text
rotation180_relation_mismatch_count: 44116
rotation180_relation_symmetric: false
candidate rotated edge: 530-529
```

This means 180-degree rotation is not a global hard invariant for `chunked_binary`, though the rotated counterpart should still be considered during candidate review.
