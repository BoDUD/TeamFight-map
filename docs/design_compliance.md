# Design Compliance Notes

This graybox is implemented from `teamfight_manager2_lol_map_design.md` dated 2026-06-25.

## Implemented MVP

| Design requirement | Implementation |
|---|---|
| Keep the square frame, base positions, three lane identity, and dual pit anchors | `data/map/tfm2_lol_like_map.json` keeps blue base `(8,92)`, red base `(92,8)`, top/mid/bottom lane centerlines, Morgard pit `(28,28)`, and Serpen pit `(72,72)` |
| Use a continuous northwest to southeast river axis | `river.main_axis` uses a normalized continuous axis through the mid bridge and all river entrances classify as `River` |
| Use generated raster concept art rather than a code-only line drawing | `docs/concept/tfm2_lol_like_map_imagegen_v1.png` is the image-gen visual concept; `assets/graybox/*.svg` remains validation/debug only |
| Each objective pit has only two entrances | `PIT_MORGARD.entrances` and `PIT_SERPEN.entrances` each contain exactly two entries |
| Four half jungles are loops, not mazes | `jungle.half_jungles` contains four regions, each with one `main_loop`, two exits, and `dead_ends_allowed: false` |
| Functional brush count is 10-12 groups | `functional_brush` contains 12 groups with explicit tactical roles and 180-degree pairs |
| Serpen is permanent growth and Morgard is pushing pressure | `objectives` marks `PIT_SERPEN` as `permanent_growth` and `PIT_MORGARD` as `timed_push_pressure` |
| Keep short match pacing | `pace.target_average_match_minutes` is `[9,12]`, with 2:00 Serpen, 2:30 vanguard, and 5:30 Morgard timings |

## Validation Gates

`tools/validate_map_design.py` checks:

- normalized coordinates stay inside the square map;
- 180-degree paired anchors, towers, brushes, camps, river zones, and vision slots;
- fixed base, bridge, lane, and pit anchors;
- 10-12 functional brush groups and no tower center inside functional brush;
- 6-8 public lane-to-river gates, with jungle-to-river gates counted separately;
- two explicit gate nodes per major pit, matching `objectives[*].entrances`;
- four half jungles with two declared exit gates and no direct mid-lane gate;
- explicit closed half-jungle loops with area, width, and self-intersection checks;
- no dangling invasion shortcut IDs;
- four camps per team;
- Serpen and Morgard prototype timelines;
- T1 plating and T2 lane-seal prototype rules;
- required region codes and river continuity through the mid bridge.

## Intentional Graybox Choices

The design appendix suggests the river axis as `(16,15) -> (50,50) -> (86,87)`. The implemented data snaps the final point to `(84,85)` so the river axis obeys the stronger 180-degree symmetry requirement while staying within graybox tolerance.

The current repository had no existing game integration layer, so this PR adds a non-runtime data specification, image-gen concept art, and validation harness. Runtime hooks, `mod.mod_info`, `mod.override_info`, asset packing, collision/walkable masks, and in-game path probes should build on this validated layout in the next implementation stage.

The `runtime_requirements` block records the original-map baseline needed before this can claim the design-book passable-area target. Until the original collision mask, walkable area, wall polygons, brush gameplay mask, and world-to-texture transform exist, this repository should be reviewed as a specification and concept package, not as a playable game map.
