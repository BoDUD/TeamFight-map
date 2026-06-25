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
    for item in layout.get("gates", []):
        items[item["id"]] = item
    return items


def polygon_area(points: list[list[float]]) -> float:
    return abs(
        sum(
            points[i][0] * points[i + 1][1] - points[i + 1][0] * points[i][1]
            for i in range(len(points) - 1)
        )
    ) / 2


def ccw(a: list[float], b: list[float], c: list[float]) -> bool:
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def segments_intersect(a: list[float], b: list[float], c: list[float], d: list[float]) -> bool:
    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)


def has_self_intersection(points: list[list[float]]) -> bool:
    segments = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    for i, (a, b) in enumerate(segments):
        for j, (c, d) in enumerate(segments):
            if abs(i - j) <= 1:
                continue
            if {i, j} == {0, len(segments) - 1}:
                continue
            if segments_intersect(a, b, c, d):
                return True
    return False


def point_in_rect(point: list[float], center: list[float], size: list[float]) -> bool:
    return (
        center[0] - size[0] / 2 <= point[0] <= center[0] + size[0] / 2
        and center[1] - size[1] / 2 <= point[1] <= center[1] + size[1] / 2
    )


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
    for shortcut in layout["jungle"].get("invasion_shortcuts", []):
        for idx, point in enumerate(shortcut["centerline"]):
            check_point(f"{shortcut['id']}.centerline[{idx}]", point)


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

    gates = {gate["id"]: gate for gate in layout["gates"]}
    gate_counts = Counter(gate["kind"] for gate in layout["gates"])
    lane_to_river_count = gate_counts["lane_to_river"]
    if not constraints["lane_to_river_gates_min"] <= lane_to_river_count <= constraints["lane_to_river_gates_max"]:
        errors.append(f"lane-to-river gate count must be 6-8, found {lane_to_river_count}")
    if len(layout["river"]["entrances"]) != lane_to_river_count:
        errors.append("river.entrances must list exactly the lane-to-river gates")
    for entrance in layout["river"]["entrances"]:
        gate = gates.get(entrance["id"])
        if not gate:
            errors.append(f"river entrance {entrance['id']} is missing from gates")
            continue
        if gate["kind"] != "lane_to_river" or gate["from"] != entrance["from"] or gate["to"] != entrance["to"]:
            errors.append(f"river entrance {entrance['id']} disagrees with its gate definition")

    for objective in layout["objectives"]:
        entrance_count = len(objective["entrances"])
        if entrance_count != constraints["pit_entrances_per_pit"]:
            errors.append(f"{objective['id']} must have 2 entrances, found {entrance_count}")
        for entrance in objective["entrances"]:
            gate = gates.get(entrance["gate_id"])
            if not gate:
                errors.append(f"{objective['id']} entrance references missing gate {entrance['gate_id']}")
                continue
            if gate["kind"] != "pit_entry" or gate["to"] != objective["id"] or gate["from"] != entrance["from"]:
                errors.append(f"{objective['id']} entrance {entrance['gate_id']} disagrees with gate endpoints")
            if gate["center"] != entrance["center"]:
                errors.append(f"{objective['id']} entrance {entrance['gate_id']} center disagrees with gate")

    half_jungles = layout["jungle"]["half_jungles"]
    if len(half_jungles) != 4:
        errors.append(f"map must have four half jungles, found {len(half_jungles)}")
    for half in half_jungles:
        if len(half["exits"]) != 2:
            errors.append(f"{half['id']} must have exactly two primary exits")
        if not half.get("closed"):
            errors.append(f"{half['id']} must explicitly mark its main loop as closed")
        if half["main_loop"][0] != half["main_loop"][-1]:
            errors.append(f"{half['id']} main loop must repeat the first point as the final point")
        if polygon_area(half["main_loop"]) <= 1:
            errors.append(f"{half['id']} main loop has no meaningful polygon area")
        if has_self_intersection(half["main_loop"]):
            errors.append(f"{half['id']} main loop self-intersects")
        if half.get("min_path_width", 0) <= 0:
            errors.append(f"{half['id']} must define a positive min_path_width")
        river_exit_count = 0
        for exit_info in half["exits"]:
            gate = gates.get(exit_info["gate_id"])
            if not gate:
                errors.append(f"{half['id']} exit references missing gate {exit_info['gate_id']}")
                continue
            if gate["from"] != half["id"] or gate["to"] != exit_info["to"] or gate["center"] != exit_info["center"]:
                errors.append(f"{half['id']} exit {exit_info['gate_id']} disagrees with gate definition")
            if gate["kind"] == "jungle_to_river":
                river_exit_count += 1
        if river_exit_count != constraints["jungle_to_river_gates_per_half_jungle"]:
            errors.append(f"{half['id']} must have exactly one jungle-to-river gate")
        if half.get("dead_ends_allowed", True):
            errors.append(f"{half['id']} must not allow dead ends")
        if len(half["main_loop"]) < 4:
            errors.append(f"{half['id']} main loop is too short to be a loop")

    camps_by_team = Counter(camp["team"] for camp in layout["jungle"]["camps"])
    for team in ("blue", "red"):
        if camps_by_team[team] != layout["jungle"]["camps_per_team"]:
            errors.append(f"{team} must have 4 camps, found {camps_by_team[team]}")

    shortcuts = {shortcut["id"]: shortcut for shortcut in layout["jungle"].get("invasion_shortcuts", [])}
    for half in half_jungles:
        shortcut_id = half.get("invasion_shortcut_id")
        if shortcut_id not in shortcuts:
            errors.append(f"{half['id']} references missing invasion shortcut {shortcut_id}")
    for shortcut_id, shortcut in shortcuts.items():
        pair_id = shortcut.get("pair")
        if pair_id not in shortcuts:
            errors.append(f"{shortcut_id} pairs to missing shortcut {pair_id}")
        if len(shortcut.get("centerline", [])) < 2:
            errors.append(f"{shortcut_id} must define a centerline with at least two points")
        if shortcut.get("width", 0) <= 0:
            errors.append(f"{shortcut_id} must define a positive width")


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

    gate_ids = {gate["id"] for gate in layout["gates"]}
    graph: dict[str, set[str]] = defaultdict(set)
    known_nodes = region_codes | {"BRIDGE_MID"} | gate_ids
    for a, b in layout["topology"]["edges"]:
        if a not in known_nodes:
            errors.append(f"topology edge references unknown node {a}")
        if b not in known_nodes:
            errors.append(f"topology edge references unknown node {b}")
        graph[a].add(b)
        graph[b].add(a)

    gates = {gate["id"]: gate for gate in layout["gates"]}
    for gate_id, gate in gates.items():
        neighbors = graph[gate_id]
        expected_neighbors = {gate["from"], gate["to"]}
        if neighbors != expected_neighbors:
            errors.append(f"{gate_id} topology neighbors {sorted(neighbors)} must equal {sorted(expected_neighbors)}")

    constraints = layout["hard_constraints"]
    for objective in layout["objectives"]:
        pit_neighbors = graph[objective["id"]]
        if len(pit_neighbors) != constraints["pit_entrances_per_pit"]:
            errors.append(f"{objective['id']} topology must expose exactly two entrance gates")
        entrance_ids = {entrance["gate_id"] for entrance in objective["entrances"]}
        if pit_neighbors != entrance_ids:
            errors.append(f"{objective['id']} topology gates must match objective entrances")

    for half in layout["jungle"]["half_jungles"]:
        exit_ids = {exit_info["gate_id"] for exit_info in half["exits"]}
        if not exit_ids.issubset(graph[half["id"]]):
            errors.append(f"{half['id']} topology must include only declared exit gates")
        extra_gate_neighbors = graph[half["id"]] & gate_ids - exit_ids
        if extra_gate_neighbors:
            errors.append(f"{half['id']} has undeclared topology gate exits: {sorted(extra_gate_neighbors)}")

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


def validate_object_overlaps(layout: dict[str, Any], errors: list[str]) -> None:
    for tower in layout["towers"]:
        for brush in layout["functional_brush"]:
            if point_in_rect(tower["center"], brush["center"], brush["size"]):
                errors.append(f"{tower['id']} center overlaps functional brush {brush['id']}")


def validate_layout(layout: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validate_bounds(layout, errors)
    validate_symmetry(layout, errors)
    validate_core_anchors(layout, errors)
    validate_design_counts(layout, errors)
    validate_objective_timelines(layout, errors)
    validate_region_codes_and_topology(layout, errors)
    validate_tower_rules(layout, errors)
    validate_object_overlaps(layout, errors)
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
