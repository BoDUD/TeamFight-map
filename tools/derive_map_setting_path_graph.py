from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import bundle_utils  # noqa: E402
from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402
from tools import map_setting_validate_semantics as semantics  # noqa: E402

MAP_SETTING_KEY = "asset/base/setting/map_setting"
LOGICAL_GRID_SIZE = semantics.LOGICAL_GRID_SIZE
MATRIX_SIZE = semantics.MATRIX_SIZE
TRANSFORMS = semantics.TRANSFORMS
OUTPUT_NAMES = (
    "packed4_path_follow_validation.json",
    "derived_local_adjacency_graph.json",
    "transform_scores_path_graph.json",
    "best_transform_path_graph_overlay.png",
)
DIRECTION_TO_DELTA = {
    "NW": (-1, -1),
    "N": (0, -1),
    "NE": (1, -1),
    "W": (-1, 0),
    "E": (1, 0),
    "SW": (-1, 1),
    "S": (0, 1),
    "SE": (1, 1),
}


def paths_are_same_existing_file(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    try:
        return left.samefile(right)
    except OSError:
        return False


def planned_output_paths(output_dir: Path) -> list[Path]:
    paths = [output_dir / name for name in OUTPUT_NAMES]
    for name in semantics.RESOURCE_KEYS:
        paths.append(output_dir / "original_assets" / f"{name}.png")
    return paths


def ensure_output_dir_is_safe(bundle_path: Path, output_dir: Path, map_setting_path: Path | None) -> None:
    if rt.is_inside_repo(output_dir):
        raise SystemExit(f"Refusing to write path-graph evidence inside the repository: {output_dir}")
    sources = {"bundle": bundle_path}
    if map_setting_path:
        sources["map_setting"] = map_setting_path
    for label, source in sources.items():
        if source == output_dir or output_dir in source.parents:
            raise SystemExit(f"Refusing to derive path graph with {label} inside the output directory: {source}")
        if paths_are_same_existing_file(source, output_dir):
            raise SystemExit(f"Refusing to derive path graph with {label} aliased to the output directory: {source}")
    for output_path in planned_output_paths(output_dir):
        for label, source in sources.items():
            if output_path == source or paths_are_same_existing_file(output_path, source):
                raise SystemExit(f"Refusing to overwrite {label} through path-graph output path: {output_path}")


def load_map_setting_data(bundle_path: Path, map_setting_path: Path | None) -> tuple[bytes, dict[str, Any]]:
    if map_setting_path:
        data = map_setting_path.read_bytes()
        return data, {
            "source": "file",
            "path": str(map_setting_path),
            "sha256": rt.sha256_bytes(data),
            "size": len(data),
        }
    asset_type, data = bundle_utils.read_bundle_entry(bundle_path, MAP_SETTING_KEY)
    return data, {
        "source": "bundle_asset",
        "asset_key": MAP_SETTING_KEY,
        "asset_type": asset_type,
        "sha256": rt.sha256_bytes(data),
        "size": len(data),
    }


def code_to_delta_from_mapping(mapping: dict[str, Any], min_purity: float = 0.70) -> dict[int, tuple[int, int]]:
    code_to_delta: dict[int, tuple[int, int]] = {}
    for code_text, direction in mapping["code_to_direction"].items():
        code = int(code_text)
        if code == 15:
            continue
        purity = mapping["purity_by_code"].get(code_text, 0.0)
        if purity < min_purity:
            continue
        if direction in DIRECTION_TO_DELTA:
            code_to_delta[code] = DIRECTION_TO_DELTA[direction]
    return code_to_delta


def move_node(node: int, delta: tuple[int, int], logical_size: int) -> int | None:
    x = node % logical_size
    y = node // logical_size
    nx = x + delta[0]
    ny = y + delta[1]
    if not (0 <= nx < logical_size and 0 <= ny < logical_size):
        return None
    return ny * logical_size + nx


def follow_path(
    packed: list[int],
    source: int,
    target: int,
    code_to_delta: dict[int, tuple[int, int]],
    logical_size: int = LOGICAL_GRID_SIZE,
    max_steps: int = 96,
) -> dict[str, Any]:
    matrix_size = logical_size * logical_size
    current = source
    visited = {current}
    for step in range(max_steps + 1):
        if current == target:
            return {"status": "reached", "steps": step}
        code = packed[current * matrix_size + target]
        if code not in code_to_delta:
            return {"status": "unresolved_code", "steps": step, "code": code}
        next_node = move_node(current, code_to_delta[code], logical_size)
        if next_node is None:
            return {"status": "out_of_bounds", "steps": step, "code": code}
        if next_node in visited:
            return {"status": "loop", "steps": step + 1, "code": code, "node": next_node}
        visited.add(next_node)
        current = next_node
    return {"status": "max_steps_exceeded", "steps": max_steps}


def validate_next_hop_paths(
    chunked: list[int],
    packed: list[int],
    code_to_delta: dict[int, tuple[int, int]],
    logical_size: int = LOGICAL_GRID_SIZE,
    sample_limit: int = 20000,
) -> dict[str, Any]:
    matrix_size = logical_size * logical_size
    status_counts: Counter[str] = Counter()
    sample_failures: list[dict[str, Any]] = []
    tested = 0
    for source in range(matrix_size):
        for target in range(matrix_size):
            if source == target or chunked[source * matrix_size + target] != 1:
                continue
            if tested >= sample_limit:
                break
            tested += 1
            result = follow_path(packed, source, target, code_to_delta, logical_size)
            status_counts[result["status"]] += 1
            if result["status"] != "reached" and len(sample_failures) < 20:
                sample_failures.append({"source": source, "target": target, **result})
        if tested >= sample_limit:
            break
    reached = status_counts["reached"]
    reached_ratio = reached / tested if tested else 0.0
    return {
        "tested_connected_pairs": tested,
        "sample_limit": sample_limit,
        "status_counts": {key: status_counts[key] for key in sorted(status_counts)},
        "reached_ratio": round(reached_ratio, 6),
        "sample_failures": sample_failures,
        "next_hop_hypothesis": (
            "strong_unverified" if reached_ratio >= 0.95 else "weak_or_unresolved"
        ),
    }


def derive_local_adjacency(
    chunked: list[int],
    packed: list[int],
    code_to_delta: dict[int, tuple[int, int]],
    logical_size: int = LOGICAL_GRID_SIZE,
) -> dict[str, Any]:
    matrix_size = logical_size * logical_size
    edges: list[dict[str, Any]] = []
    direction_consistency_counts: Counter[str] = Counter()
    for source_y in range(logical_size):
        for source_x in range(logical_size):
            source = source_y * logical_size + source_x
            for dx, dy, kind in ((1, 0, "horizontal"), (0, 1, "vertical"), (1, 1, "diagonal"), (-1, 1, "diagonal")):
                target_x = source_x + dx
                target_y = source_y + dy
                if not (0 <= target_x < logical_size and 0 <= target_y < logical_size):
                    continue
                target = target_y * logical_size + target_x
                forward = chunked[source * matrix_size + target]
                reverse = chunked[target * matrix_size + source]
                forward_code = packed[source * matrix_size + target]
                reverse_code = packed[target * matrix_size + source]
                expected_forward = (dx, dy)
                expected_reverse = (-dx, -dy)
                forward_consistent = code_to_delta.get(forward_code) == expected_forward
                reverse_consistent = code_to_delta.get(reverse_code) == expected_reverse
                if forward_consistent and reverse_consistent:
                    direction_consistency_counts["both_consistent"] += 1
                elif forward_consistent or reverse_consistent:
                    direction_consistency_counts["one_consistent"] += 1
                else:
                    direction_consistency_counts["not_consistent_or_unresolved"] += 1
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "source_xy": [source_x, source_y],
                        "target_xy": [target_x, target_y],
                        "kind": kind,
                        "open": forward == 1 and reverse == 1,
                        "chunked_forward": forward,
                        "chunked_reverse": reverse,
                        "packed4_forward": forward_code,
                        "packed4_reverse": reverse_code,
                        "forward_code_matches_neighbor_delta": forward_consistent,
                        "reverse_code_matches_neighbor_delta": reverse_consistent,
                    }
                )
    return {
        "logical_size": logical_size,
        "edge_count": len(edges),
        "open_edge_count": sum(1 for edge in edges if edge["open"]),
        "blocked_edge_count": sum(1 for edge in edges if not edge["open"]),
        "direction_consistency_counts": {
            key: direction_consistency_counts[key] for key in sorted(direction_consistency_counts)
        },
        "edges": edges,
        "hypothesis": "unverified_local_adjacency_from_chunked_binary_and_packed4_0",
    }


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def score_transform_path_graph(transform: str, edges: list[dict[str, Any]], wall_union, minimap) -> dict[str, Any]:
    blocked_wall: list[float] = []
    open_wall: list[float] = []
    blocked_road: list[float] = []
    open_road: list[float] = []
    open_crossing_penalties = 0
    blocked_wall_hits = 0
    for edge in edges:
        wall_start = semantics.node_pixel(edge["source"], transform, wall_union.size)
        wall_end = semantics.node_pixel(edge["target"], transform, wall_union.size)
        wall_points = semantics.sample_points_between(wall_start, wall_end, steps=9)
        mini_start = semantics.node_pixel(edge["source"], transform, minimap.size)
        mini_end = semantics.node_pixel(edge["target"], transform, minimap.size)
        mini_points = semantics.sample_points_between(mini_start, mini_end, steps=9)
        wall_alpha = semantics.sample_alpha(wall_union, wall_points, radius=2)
        minimap_dark = semantics.sample_darkness(minimap, mini_points, radius=1)
        road_likelihood = 1.0 - minimap_dark
        if edge["open"]:
            open_wall.append(wall_alpha)
            open_road.append(road_likelihood)
            if wall_alpha >= 0.35:
                open_crossing_penalties += 1
        else:
            blocked_wall.append(wall_alpha)
            blocked_road.append(road_likelihood)
            if wall_alpha >= 0.35:
                blocked_wall_hits += 1
    blocked_wall_mean = mean(blocked_wall)
    open_wall_mean = mean(open_wall)
    blocked_road_mean = mean(blocked_road)
    open_road_mean = mean(open_road)
    wall_separation = blocked_wall_mean - open_wall_mean
    road_separation = open_road_mean - blocked_road_mean
    crossing_penalty_rate = open_crossing_penalties / len(open_wall) if open_wall else 0.0
    blocked_wall_hit_rate = blocked_wall_hits / len(blocked_wall) if blocked_wall else 0.0
    score = wall_separation * 0.5 + road_separation * 0.35 + blocked_wall_hit_rate * 0.1 - crossing_penalty_rate * 0.25
    return {
        "transform": transform,
        "score": round(score, 6),
        "wall_blocked_mean": round(blocked_wall_mean, 6),
        "wall_open_mean": round(open_wall_mean, 6),
        "wall_separation": round(wall_separation, 6),
        "road_open_mean": round(open_road_mean, 6),
        "road_blocked_mean": round(blocked_road_mean, 6),
        "road_separation": round(road_separation, 6),
        "open_edge_wall_crossing_penalty_rate": round(crossing_penalty_rate, 6),
        "blocked_edge_wall_hit_rate": round(blocked_wall_hit_rate, 6),
        "blocked_edge_count": len(blocked_wall),
        "open_edge_count": len(open_wall),
    }


def draw_path_graph_overlay(base_path: Path, edges: list[dict[str, Any]], transform: str, output_path: Path) -> dict[str, Any]:
    return semantics.draw_best_transform_overlay(base_path, edges, transform, output_path)


def transform_scores_path_graph(edges: list[dict[str, Any]], output_dir: Path, assets: dict[str, Any], direction_mapping: dict[str, Any]) -> dict[str, Any]:
    from PIL import Image

    wall_union = semantics.load_wall_union(Path(assets["wall_5v5"]["path"]), Path(assets["wall_5v5_front"]["path"]))
    minimap_path = Path(assets["minimap_5v5_bg"]["path"])
    minimap = Image.open(minimap_path).convert("RGBA")
    scores = [score_transform_path_graph(transform, edges, wall_union, minimap) for transform in TRANSFORMS]
    scores.sort(key=lambda item: item["score"], reverse=True)
    best = scores[0]
    second = scores[1] if len(scores) > 1 else None
    margin = best["score"] - second["score"] if second else 0.0
    conclusion = "single_best" if margin >= 0.05 else "ambiguous"
    overlay = draw_path_graph_overlay(minimap_path, edges, best["transform"], output_dir / "best_transform_path_graph_overlay.png")
    return {
        "scores": scores,
        "best_transform": best["transform"],
        "second_transform": second["transform"] if second else None,
        "score_margin": round(margin, 6),
        "conclusion": conclusion,
        "best_transform_path_graph_overlay": overlay,
        "direction_code_stability": direction_mapping["stability"],
        "scoring": {
            "reward": [
                "blocked local edges sampling wall alpha",
                "open local edges sampling minimap road-like pixels",
                "blocked edges with wall-hit samples",
            ],
            "penalty": [
                "open local edges crossing wall alpha",
                "blocked edges sampling road-like minimap pixels",
            ],
            "ambiguous_margin_threshold": 0.05,
            "entity_anchor_scoring": "not_applied_no_decoded_entity_anchor_table",
        },
    }


def derive_path_graph(
    bundle_path: Path,
    output_dir: Path,
    map_setting_path: Path | None = None,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    bundle_path = bundle_path.resolve()
    output_dir = output_dir.resolve()
    map_setting_path = map_setting_path.resolve() if map_setting_path else None
    ensure_output_dir_is_safe(bundle_path, output_dir, map_setting_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    data, source = load_map_setting_data(bundle_path, map_setting_path)
    if expected_sha256 and rt.sha256_bytes(data).lower() != expected_sha256.lower():
        raise SystemExit(f"map_setting SHA-256 {rt.sha256_bytes(data)} does not match expected {expected_sha256}.")
    document = rt.decode_map_setting(data)
    if len(document.packed4_layers) < 1:
        raise SystemExit("Expected at least one packed4 layer for path graph derivation.")
    chunked, width, height = inspect.flatten_chunked_binary_layer(document.chunked_binary_layer)
    if (width, height) != (MATRIX_SIZE, MATRIX_SIZE):
        raise SystemExit(f"Expected chunked_binary {MATRIX_SIZE}x{MATRIX_SIZE}, got {width}x{height}.")
    packed0 = inspect.unpack_packed4_layer(document.packed4_layers[0])
    if len(packed0) != MATRIX_SIZE * MATRIX_SIZE:
        raise SystemExit("Expected packed4_0 to contain 810,000 cells.")

    direction_mapping = semantics.adjacent_direction_distributions(packed0, LOGICAL_GRID_SIZE)
    code_to_delta = code_to_delta_from_mapping(direction_mapping)
    path_validation = validate_next_hop_paths(chunked, packed0, code_to_delta)
    adjacency = derive_local_adjacency(chunked, packed0, code_to_delta)
    assets = semantics.extract_reference_assets(bundle_path, output_dir)
    scores = transform_scores_path_graph(adjacency["edges"], output_dir, assets, direction_mapping)
    offline_anchor_result = "ambiguous" if scores["conclusion"] == "ambiguous" else "no_sufficient_anchor_found"

    path_validation_path = output_dir / "packed4_path_follow_validation.json"
    adjacency_path = output_dir / "derived_local_adjacency_graph.json"
    scores_path = output_dir / "transform_scores_path_graph.json"
    path_validation_path.write_text(
        json.dumps(path_validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    adjacency_path.write_text(
        json.dumps(adjacency, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    scores_path.write_text(json.dumps(scores, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    report = {
        "probe": "map_setting_path_graph_derivation",
        "bundle_path": str(bundle_path),
        "map_setting_source": source,
        "outputs": {
            "packed4_path_follow_validation": str(path_validation_path),
            "derived_local_adjacency_graph": str(adjacency_path),
            "transform_scores_path_graph": str(scores_path),
            "best_transform_path_graph_overlay": scores["best_transform_path_graph_overlay"]["path"],
        },
        "next_hop_hypothesis": path_validation["next_hop_hypothesis"],
        "transform_summary": {
            "best_transform": scores["best_transform"],
            "second_transform": scores["second_transform"],
            "score_margin": scores["score_margin"],
            "conclusion": scores["conclusion"],
        },
        "offline_anchor_result": offline_anchor_result,
        "map_setting_node_world_transform": "unproven",
        "candidate_369_370": "blocked",
        "may_enter_mutation_pr": False,
        "safety": {
            "read_only": True,
            "map_setting_mutated": False,
            "map_setting_override_installed": False,
            "asset_override_installed": False,
            "original_resources_committed": False,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return report


def stdout_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": report["probe"],
        "next_hop_hypothesis": report["next_hop_hypothesis"],
        "best_transform": report["transform_summary"]["best_transform"],
        "second_transform": report["transform_summary"]["second_transform"],
        "score_margin": report["transform_summary"]["score_margin"],
        "offline_anchor_result": report["offline_anchor_result"],
        "candidate_369_370": report["candidate_369_370"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Derive a read-only local path graph from map_setting packed4_0.")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--map-setting", type=Path, default=None, help="Optional local map_setting file; otherwise read from bundle.")
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    args = parser.parse_args()
    report = derive_path_graph(
        bundle_path=args.bundle,
        output_dir=args.output_dir,
        map_setting_path=args.map_setting,
        expected_sha256=args.expected_sha256,
    )
    print(json.dumps(stdout_summary(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
