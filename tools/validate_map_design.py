from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAYOUT = REPO_ROOT / "data" / "map" / "tfm2_lol_like_map.json"


class ValidationError(Exception):
    """Raised when the graybox map violates the design-book contract."""


def load_layout(path: Path | str = DEFAULT_LAYOUT) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rotate_180(point: list[float] | tuple[float, float]) -> tuple[float, float]:
    return (100 - float(point[0]), 100 - float(point[1]))


def distance(a: list[float] | tuple[float, float], b: list[float] | tuple[float, float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def collect_centered_items(layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for item_id, item in layout.get("anchors", {}).items():
        if "center" in item:
            items[item_id] = item
    for section in ("towers", "functional_brush", "vision_slots", "objectives"):
        for item in layout.get(section, []):
            if "id" in item and "center" in item:
                items[item["id"]] = item
    for item in layout.get("river", {}).get("zones", []):
        items[item["id"]] = item
    for item in layout.get("river", {}).get("entrances", []):
        items[item["id"]] = item
    for item in layout.get("jungle", {}).get("half_jungles", []):
        items[item["id"]] = item
    for item in layout.get("jungle", {}).get("camps", []):
        items[item["id"]] = item
    return items


def validate_bounds(layout: dict[str, Any], errors: list[str]) -> None:
    bounds = layout["coordinate_system"]["bounds"]
    min_x, min_y = bounds["min"]
    max_x, max_y = bounds["max"]

    def check_point(label: str, point: list[float]) -> None:
        x, y = point
        if not (min_x <= x <= max_x and min_y <= y <= max_y):
            errors.append(f"{label} point {point} is outside normalized map bounds")

    for item_id, item in collect_centered_items(layout).items():
        check_point(item_id, item["center"])
    for lane in layout["lanes"]:
        for idx, point in enumerate(lane["centerline"]):
            check_point(f"{lane['id']}.centerline[{idx}]", point)
    for idx, point in enumerate(layout["river"]["main_axis"]):
        check_point(f"river.main_axis[{idx}]", point)
    for half in layout["jungle"]["half_jungles"]:
        for idx, point in enumerate(half["main_loop"]):
            check_point(f"{half['id']}.main_loop[{idx}]", point)


def validate_symmetry(layout: dict[str, Any], errors: list[str], tolerance: float = 0.75) -> None:
    items = collect_centered_items(layout)
    for item_id, item in items.items():
        pair_id = item.get("pair")
        if not pair_id:
            continue
        pair = items.get(pair_id)
        if not pair:
            errors.append(f"{item_id} pairs to missing item {pair_id}")
            continue
        expected = rotate_180(item["center"])
        if distance(expected, pair["center"]) > tolerance:
            errors.append(
                f"{item_id} center {item['center']} is not 180-degree paired with "
                f"{pair_id} center {pair['center']} (expected {expected})"
            )


def validate_core_anchors(layout: dict[str, Any], errors: list[str]) -> None:
    anchors = layout["anchors"]
    expected = {
        "BASE_BLUE": [8, 92],
        "BASE_RED": [92, 8],
        "PIT_MORGARD": [28, 28],
        "PIT_SERPEN": [72, 72],
        "BRIDGE_MID": [50, 50]
    }
    for item_id, point in expected.items():
        if anchors[item_id]["center"] != point:
            errors.append(f"{item_id} must stay at {point}, found {anchors[item_id]['center']}")

    lanes = {lane["id"]: lane for lane in layout["lanes"]}
    expected_lanes = {
        "LANE_TOP": [[8, 92], [8, 8], [92, 8]],
        "LANE_MID": [[8, 92], [50, 50], [92, 8]],
        "LANE_BOTTOM": [[8, 92], [92, 92], [92, 8]]
    }
    for lane_id, centerline in expected_lanes.items():
        if lanes[lane_id]["centerline"] != centerline:
            errors.append(f"{lane_id} centerline changed from design anchor")


def validate_design_counts(layout: dict[str, Any], errors: list[str]) -> None:
    constraints = layout["hard_constraints"]
    brush_count = len(layout["functional_brush"])
    if not constraints["functional_brush_groups_min"] <= brush_count <= constraints["functional_brush_groups_max"]:
        errors.append(f"functional brush count must be 10-12, found {brush_count}")

    river_entry_count = len(layout["river"]["entrances"])
    if not constraints["river_entrances_min"] <= river_entry_count <= constraints["river_entrances_max"]:
        errors.append(f"river entrance count must be 6-8, found {river_entry_count}")

    for objective in layout["objectives"]:
        entrance_count = len(objective["entrances"])
        if entrance_count != constraints["pit_entrances_per_pit"]:
            errors.append(f"{objective['id']} must have 2 entrances, found {entrance_count}")

    half_jungles = layout["jungle"]["half_jungles"]
    if len(half_jungles) != 4:
        errors.append(f"map must have four half jungles, found {len(half_jungles)}")
    for half in half_jungles:
        if len(half["exits"]) != 2:
            errors.append(f"{half['id']} must have exactly two primary exits")
        if half.get("dead_ends_allowed", True):
            errors.append(f"{half['id']} must not allow dead ends")
        if len(half["main_loop"]) < 4:
            errors.append(f"{half['id']} main loop is too short to be a loop")

    camps_by_team = Counter(camp["team"] for camp in layout["jungle"]["camps"])
    for team in ("blue", "red"):
        if camps_by_team[team] != layout["jungle"]["camps_per_team"]:
            errors.append(f"{team} must have 4 camps, found {camps_by_team[team]}")


def validate_objective_timelines(layout: dict[str, Any], errors: list[str]) -> None:
    objectives = {objective["id"]: objective for objective in layout["objectives"]}
    morgard = objectives["PIT_MORGARD"]["timeline"]
    expected_morgard = {
        "vanguard_spawn_seconds": 150,
        "vanguard_end_seconds": 320,
        "morgard_spawn_seconds": 330,
        "morgard_respawn_seconds": 180,
        "push_buff_seconds": 60
    }
    for key, expected in expected_morgard.items():
        if morgard.get(key) != expected:
            errors.append(f"Morgard timeline {key} must be {expected}, found {morgard.get(key)}")

    serpen = objectives["PIT_SERPEN"]["timeline"]
    if serpen.get("first_spawn_seconds") != 120:
        errors.append("Serpen first spawn must be 120 seconds")
    if serpen.get("respawn_seconds") != 150:
        errors.append("Serpen respawn must be 150 seconds")
    if objectives["PIT_SERPEN"]["reward"].get("stack_cap") != 3:
        errors.append("Serpen permanent growth must cap base stacks at 3")


def validate_region_codes_and_topology(layout: dict[str, Any], errors: list[str]) -> None:
    required_codes = {
        "LANE_TOP",
        "LANE_MID",
        "LANE_BOTTOM",
        "RIVER_TOP",
        "RIVER_BOTTOM",
        "PIT_MORGARD",
        "PIT_SERPEN",
        "JUNGLE_BLUE_TOP",
        "JUNGLE_BLUE_BOT",
        "JUNGLE_RED_TOP",
        "JUNGLE_RED_BOT",
        "BASE_BLUE",
        "BASE_RED"
    }
    region_codes = set(layout["region_codes"])
    missing = sorted(required_codes - region_codes)
    if missing:
        errors.append(f"missing required region codes: {', '.join(missing)}")

    graph: dict[str, set[str]] = defaultdict(set)
    known_nodes = region_codes | {"BRIDGE_MID"}
    for a, b in layout["topology"]["edges"]:
        if a not in known_nodes:
            errors.append(f"topology edge references unknown node {a}")
        if b not in known_nodes:
            errors.append(f"topology edge references unknown node {b}")
        graph[a].add(b)
        graph[b].add(a)

    for pit in ("PIT_MORGARD", "PIT_SERPEN"):
        if len(graph[pit]) != 1:
            errors.append(f"{pit} should connect through one river node in region topology")
    if "BRIDGE_MID" not in graph["RIVER_TOP"] or "BRIDGE_MID" not in graph["RIVER_BOTTOM"]:
        errors.append("river must be continuous through BRIDGE_MID")


def validate_tower_rules(layout: dict[str, Any], errors: list[str]) -> None:
    by_lane_tier: Counter[tuple[str, int]] = Counter()
    base_guards = 0
    for tower in layout["towers"]:
        if tower["tier"] == "base_guard":
            base_guards += 1
        else:
            by_lane_tier[(tower["lane"], tower["tier"])] += 1
    for lane in ("top", "mid", "bottom"):
        for tier in (1, 2):
            if by_lane_tier[(lane, tier)] != 2:
                errors.append(f"{lane} lane must have one T{tier} per team")
    if base_guards != 4:
        errors.append(f"base guard towers must total 4, found {base_guards}")

    plating = layout["tower_rules"]["t1_plating"]
    if plating["active_until_seconds"] != 240 or plating["plates"] != 3:
        errors.append("T1 plating must be 3 plates through 4:00")
    seal = layout["tower_rules"]["t2_lane_seal"]
    if seal["enhanced_minion_seconds"] != 90:
        errors.append("T2 lane seal must enhance minions for 90 seconds")


def validate_layout(layout: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validate_bounds(layout, errors)
    validate_symmetry(layout, errors)
    validate_core_anchors(layout, errors)
    validate_design_counts(layout, errors)
    validate_objective_timelines(layout, errors)
    validate_region_codes_and_topology(layout, errors)
    validate_tower_rules(layout, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Teamfight Manager 2 LOL-like map graybox data.")
    parser.add_argument("layout", nargs="?", default=DEFAULT_LAYOUT, type=Path)
    args = parser.parse_args()

    layout = load_layout(args.layout)
    errors = validate_layout(layout)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: {args.layout} satisfies the map design constraints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
