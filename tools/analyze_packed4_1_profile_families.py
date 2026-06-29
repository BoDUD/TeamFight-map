from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import analyze_chunked_binary_probe_targets as q2h  # noqa: E402
from tools import analyze_no15_singleton_components as q2l  # noqa: E402
from tools import analyze_packed4_1_node_profiles as q2m  # noqa: E402
from tools import analyze_packed4_next_hop_semantics as q2i  # noqa: E402
from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2p_packed4_1_profile_families")
JSON_OUTPUT_FILES = (
    "packed4_1_profile_family_catalog.json",
    "packed4_1_profile_hamming_clusters.json",
    "packed4_1_profile_family_spatial_patterns.json",
    "packed4_1_profile_family_component_correlation.json",
    "packed4_1_profile_family_anchor_candidates.json",
    "tracked_profile_family_nodes.json",
    "q2p_profile_family_interpretation.json",
)
CONTACT_SHEET = "profile_family_masks/top_profile_family_contact_sheet.png"
TRACKED_NODES = (369, 370, 59, 837, 126, 617, 654, 184, 773, 498)
TRANSFORMS = (
    "rotate90",
    "rotate180",
    "rotate270",
    "flip_x",
    "flip_y",
    "transpose",
    "anti_transpose",
)


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def planned_output_paths(output_dir: Path, max_family_count: int = 900) -> list[Path]:
    paths = [output_dir / name for name in JSON_OUTPUT_FILES]
    paths.append(output_dir / CONTACT_SHEET)
    for index in range(1, max_family_count + 1):
        paths.append(output_dir / "profile_family_masks" / f"family_{index:04d}_mask_30x30.png")
    return paths


def ensure_paths_are_safe(input_path: Path, output_dir: Path) -> None:
    inspect.ensure_outside_repo(input_path, "input")
    inspect.ensure_outside_repo(output_dir, "output directory")
    if is_under_mods_tree(output_dir):
        raise SystemExit("Refusing to write Q2p analysis output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(input_path, output_dir, "input")
    for output_path in planned_output_paths(output_dir):
        if output_path == input_path or inspect.paths_are_same_existing_file(output_path, input_path):
            raise SystemExit(f"Refusing to overwrite input through generated output path: {output_path}")
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")


def counter_payload(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def numeric_stats(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"min": None, "max": None, "average": None, "unique_values": []}
    return {
        "min": min(values),
        "max": max(values),
        "average": sum(values) / len(values),
        "unique_values": sorted(set(values)),
    }


def base_metadata(input_path: Path, output_dir: Path, data: bytes) -> dict[str, Any]:
    return {
        "input_path": str(input_path),
        "input_sha256": rt.sha256_bytes(data),
        "input_size": len(data),
        "output_dir": str(output_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "safety": {
            "read_only": True,
            "mutated_map_setting_generated": False,
            "runtime_install_modified": False,
            "map_setting_override_installed": False,
            "outputs_inside_repository": rt.is_inside_repo(output_dir),
            "outputs_under_mods_tree": is_under_mods_tree(output_dir),
        },
    }


def hamming_distance(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    return sum(1 for a, b in zip(left, right) if a != b)


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def profile_signature(profile: tuple[int, ...]) -> dict[str, Any]:
    even_values = Counter(value for index, value in enumerate(profile) if index % 2 == 0)
    odd_values = Counter(value for index, value in enumerate(profile) if index % 2 == 1)
    value_counter = Counter(profile)
    return {
        "value_set": sorted(value_counter),
        "value_histogram": counter_payload(value_counter),
        "even_slot_values": counter_payload(even_values),
        "odd_slot_values": counter_payload(odd_values),
        "alternating_even_8_odd_0": all((value == 8 if index % 2 == 0 else value == 0) for index, value in enumerate(profile)),
        "zero_count": value_counter[0],
        "eight_count": value_counter[8],
        "non_zero_non_eight_count": len(profile) - value_counter[0] - value_counter[8],
    }


def transform_node(node: int, logical_size: int, transform: str) -> int:
    x = node % logical_size
    y = node // logical_size
    last = logical_size - 1
    if transform == "rotate90":
        nx, ny = last - y, x
    elif transform == "rotate180":
        nx, ny = last - x, last - y
    elif transform == "rotate270":
        nx, ny = y, last - x
    elif transform == "flip_x":
        nx, ny = last - x, y
    elif transform == "flip_y":
        nx, ny = x, last - y
    elif transform == "transpose":
        nx, ny = y, x
    elif transform == "anti_transpose":
        nx, ny = last - y, last - x
    else:
        raise ValueError(f"Unknown transform: {transform}")
    return ny * logical_size + nx


def asymmetry_payload(nodes: list[int], logical_size: int) -> dict[str, Any]:
    node_set = set(nodes)
    if not node_set:
        return {"asymmetry_score": 0.0, "max_symmetry_jaccard": 1.0, "transform_jaccards": {}}
    transform_jaccards: dict[str, float] = {}
    for transform in TRANSFORMS:
        transformed = {transform_node(node, logical_size, transform) for node in node_set}
        union = node_set | transformed
        intersection = node_set & transformed
        transform_jaccards[transform] = round(len(intersection) / len(union), 6) if union else 1.0
    max_jaccard = max(transform_jaccards.values()) if transform_jaccards else 1.0
    return {
        "asymmetry_score": round(1.0 - max_jaccard, 6),
        "max_symmetry_jaccard": round(max_jaccard, 6),
        "transform_jaccards": transform_jaccards,
    }


def load_family_inputs(
    input_path: Path,
    expected_sha256: str | None,
) -> tuple[bytes, list[int], list[int], list[int], int, list[int], list[list[int]], list[dict[str, Any]]]:
    return q2l.load_graph_inputs(input_path, expected_sha256)


def nodes_by_profile(profiles: list[tuple[int, ...]]) -> dict[tuple[int, ...], list[int]]:
    result: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for node, profile in enumerate(profiles):
        result[profile].append(node)
    return result


def build_hamming_families(
    profile_counts: Counter[tuple[int, ...]],
    hamming_threshold: int,
) -> tuple[list[list[tuple[int, ...]]], list[dict[str, Any]]]:
    unique_profiles = sorted(profile_counts, key=lambda profile: (-profile_counts[profile], profile))
    uf = UnionFind(len(unique_profiles))
    edges: list[dict[str, Any]] = []
    for left_index, left in enumerate(unique_profiles):
        for right_index in range(left_index + 1, len(unique_profiles)):
            right = unique_profiles[right_index]
            distance = hamming_distance(left, right)
            if distance <= hamming_threshold:
                uf.union(left_index, right_index)
                edges.append(
                    {
                        "left_profile_rank": left_index + 1,
                        "right_profile_rank": right_index + 1,
                        "distance": distance,
                    }
                )
    grouped: dict[int, list[tuple[int, ...]]] = defaultdict(list)
    for index, profile in enumerate(unique_profiles):
        grouped[uf.find(index)].append(profile)
    families = list(grouped.values())
    families.sort(key=lambda family: (-sum(profile_counts[profile] for profile in family), -len(family), family[0]))
    return families, edges


def family_nodes(
    family: list[tuple[int, ...]],
    by_profile: dict[tuple[int, ...], list[int]],
) -> list[int]:
    nodes: list[int] = []
    for profile in family:
        nodes.extend(by_profile[profile])
    return sorted(nodes)


def family_record(
    family_id: str,
    family: list[tuple[int, ...]],
    nodes: list[int],
    profile_ids: dict[tuple[int, ...], str],
    profile_counts: Counter[tuple[int, ...]],
    chunked_values: list[int],
    component_by_node: list[int],
    components: list[list[int]],
    edge_records: list[dict[str, Any]],
    matrix_size: int,
    singleton_profile: tuple[int, ...] | None,
    node837_profile: tuple[int, ...] | None,
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    large_component = q2l.largest_component_id(components)
    singletons = set(q2l.singleton_nodes(components))
    degrees = q2m.bridge_degrees(edge_records, components)
    representative_profile = max(family, key=lambda profile: (profile_counts[profile], tuple(-value for value in profile)))
    role_counts = Counter(q2m.component_role(node, component_by_node, components, large_component, singletons) for node in nodes)
    class_counts = Counter(
        f"{q2h.classify_sum(rows[node], matrix_size)}|{q2h.classify_sum(columns[node], matrix_size)}"
        for node in nodes
    )
    endpoint_degrees = [degrees[node]["total_endpoint_count"] for node in nodes]
    large_bridge_degrees = [degrees[node]["large_component_bridge_endpoint_count"] for node in nodes]
    singleton_bridge_degrees = [degrees[node]["singleton_bridge_endpoint_count"] for node in nodes]
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    dominant_role, dominant_role_count = role_counts.most_common(1)[0]
    distances_to_rep = [hamming_distance(representative_profile, profile) for profile in family]
    result = {
        "family_id": family_id,
        "profile_count": len(family),
        "node_count": len(nodes),
        "representative_profile_id": profile_ids[representative_profile],
        "representative_profile": list(representative_profile),
        "representative_profile_signature": profile_signature(representative_profile),
        "profile_ids": [profile_ids[profile] for profile in sorted(family, key=lambda profile: (-profile_counts[profile], profile))],
        "profile_ids_truncated": len(family) > 80,
        "profile_node_counts": [
            {"profile_id": profile_ids[profile], "node_count": profile_counts[profile]}
            for profile in sorted(family, key=lambda profile: (-profile_counts[profile], profile))[:80]
        ],
        "node_sample": nodes[:120],
        "node_sample_truncated": len(nodes) > 120,
        "component_role_counts": counter_payload(role_counts),
        "dominant_role": dominant_role,
        "dominant_role_ratio": dominant_role_count / len(nodes) if nodes else 0.0,
        "row_column_class_pair_counts": counter_payload(class_counts),
        "code15_endpoint_count": sum(endpoint_degrees),
        "code15_endpoint_degree_stats": numeric_stats(endpoint_degrees),
        "large_component_bridge_endpoint_count": sum(large_bridge_degrees),
        "large_component_bridge_degree_stats": numeric_stats(large_bridge_degrees),
        "singleton_bridge_endpoint_count": sum(singleton_bridge_degrees),
        "singleton_bridge_degree_stats": numeric_stats(singleton_bridge_degrees),
        "hamming_distance_to_representative": numeric_stats(distances_to_rep),
        "spatial": q2m.spatial_pattern_for_nodes(nodes, matrix_size, singletons),
        "asymmetry": asymmetry_payload(nodes, logical_size),
    }
    if singleton_profile is not None:
        result["hamming_distance_to_singleton_profile"] = numeric_stats(
            [hamming_distance(profile, singleton_profile) for profile in family]
        )
    if node837_profile is not None:
        result["hamming_distance_to_node837_profile"] = numeric_stats(
            [hamming_distance(profile, node837_profile) for profile in family]
        )
    return result


def profile_family_catalog_payload(
    metadata: dict[str, Any],
    family_records: list[dict[str, Any]],
    profile_counts: Counter[tuple[int, ...]],
) -> dict[str, Any]:
    return {
        "probe": "q2p_packed4_1_profile_family_catalog",
        **metadata,
        "profile_definition": "node-major: packed4_1[node * 30 : node * 30 + 30]",
        "family_definition": "exact node-major profile match; Hamming clusters are reported separately",
        "coordinate_boundary": "30x30 table coordinates are unproven game-world coordinates.",
        "unique_profile_count": len(profile_counts),
        "family_count": len(family_records),
        "profile_frequency_histogram": counter_payload(Counter(profile_counts.values())),
        "family_node_count_histogram": counter_payload(Counter(record["node_count"] for record in family_records)),
        "top_families": family_records[:40],
        "all_family_records": family_records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def hamming_clusters_payload(
    metadata: dict[str, Any],
    cluster_records: list[dict[str, Any]],
    hamming_edges: list[dict[str, Any]],
    hamming_threshold: int,
) -> dict[str, Any]:
    return {
        "probe": "q2p_packed4_1_profile_hamming_clusters",
        **metadata,
        "family_definition": f"Hamming-distance connected components with threshold <= {hamming_threshold}",
        "hamming_threshold": hamming_threshold,
        "cluster_count": len(cluster_records),
        "cluster_size_histogram_by_profiles": counter_payload(Counter(record["profile_count"] for record in cluster_records)),
        "cluster_size_histogram_by_nodes": counter_payload(Counter(record["node_count"] for record in cluster_records)),
        "hamming_edge_count": len(hamming_edges),
        "hamming_edges_sample": hamming_edges[:200],
        "hamming_edges_sample_truncated": len(hamming_edges) > 200,
        "top_clusters": [
            {
                "cluster_id": record["family_id"].replace("family_", "cluster_"),
                "profile_count": record["profile_count"],
                "node_count": record["node_count"],
                "dominant_role": record["dominant_role"],
                "spatial_pattern": record["spatial"]["spatial_pattern"],
                "asymmetry_score": record["asymmetry"]["asymmetry_score"],
            }
            for record in cluster_records[:60]
        ],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def spatial_patterns_payload(metadata: dict[str, Any], family_records: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [
        {
            "family_id": record["family_id"],
            "profile_count": record["profile_count"],
            "node_count": record["node_count"],
            "dominant_role": record["dominant_role"],
            "spatial": record["spatial"],
            "asymmetry": record["asymmetry"],
        }
        for record in family_records
        if record["node_count"] <= 150
        or record["spatial"]["spatial_pattern"] != "ambiguous"
        or record["asymmetry"]["asymmetry_score"] >= 0.5
    ]
    return {
        "probe": "q2p_profile_family_spatial_patterns",
        **metadata,
        "coordinate_boundary": "30x30 table coordinates are unproven game-world coordinates.",
        "selected_family_count": len(selected),
        "family_spatial_patterns": selected,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def component_correlation_payload(metadata: dict[str, Any], family_records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "probe": "q2p_profile_family_component_correlation",
        **metadata,
        "family_component_records": [
            {
                "family_id": record["family_id"],
                "profile_count": record["profile_count"],
                "node_count": record["node_count"],
                "component_role_counts": record["component_role_counts"],
                "dominant_role": record["dominant_role"],
                "dominant_role_ratio": record["dominant_role_ratio"],
                "row_column_class_pair_counts": record["row_column_class_pair_counts"],
                "code15_endpoint_degree_stats": record["code15_endpoint_degree_stats"],
                "large_component_bridge_degree_stats": record["large_component_bridge_degree_stats"],
                "singleton_bridge_degree_stats": record["singleton_bridge_degree_stats"],
            }
            for record in family_records
        ],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def anchor_candidate_score(record: dict[str, Any]) -> tuple[float, list[str]]:
    node_count = record["node_count"]
    role_counts = record["component_role_counts"]
    singleton_count = role_counts.get("singleton_component", 0)
    large_count = role_counts.get("large_component", 0)
    degree_average = record["code15_endpoint_degree_stats"]["average"] or 0.0
    asymmetry_score = record["asymmetry"]["asymmetry_score"]
    if node_count <= 1 or node_count > 120:
        return 0.0, []
    if singleton_count == node_count:
        return 0.0, []
    reasons = ["small asymmetric mask", "not singleton-only"]
    size_score = 1.0 - abs(node_count - 12) / 120
    size_score = max(0.0, min(1.0, size_score))
    bridge_score = min(1.0, degree_average / 120)
    role_score = 0.2 if large_count == node_count else 0.35
    if large_count != node_count:
        reasons.append("not large-component-only")
    if degree_average > 0:
        reasons.append("has code15 bridge-degree signal")
    if record["spatial"]["spatial_pattern"] != "matches_no15_singleton_band":
        reasons.append("not singleton-band mask")
    score = (asymmetry_score * 0.45) + (size_score * 0.2) + (bridge_score * 0.2) + role_score
    return round(score, 6), reasons


def anchor_candidates_payload(metadata: dict[str, Any], family_records: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for record in family_records:
        score, reasons = anchor_candidate_score(record)
        if score <= 0:
            continue
        candidates.append(
            {
                "family_id": record["family_id"],
                "node_count": record["node_count"],
                "profile_count": record["profile_count"],
                "asymmetry_score": record["asymmetry"]["asymmetry_score"],
                "anchor_candidate_score": score,
                "dominant_role": record["dominant_role"],
                "component_role_counts": record["component_role_counts"],
                "spatial_pattern": record["spatial"]["spatial_pattern"],
                "code15_endpoint_degree_stats": record["code15_endpoint_degree_stats"],
                "representative_profile": record["representative_profile"],
                "reason": ", ".join(reasons),
                "may_use_for_visual_correlation": True,
                "runtime_mutation_allowed": False,
            }
        )
    candidates.sort(key=lambda item: (-item["anchor_candidate_score"], -item["asymmetry_score"], item["node_count"], item["family_id"]))
    return {
        "probe": "q2p_profile_family_anchor_candidates",
        **metadata,
        "anchor_candidate_definition": "small, asymmetric, non-singleton-only profile family masks for later read-only visual correlation only",
        "anchor_candidate_profiles": candidates[:40],
        "anchor_candidate_count": len(candidates),
        "asymmetric_anchor_candidates_found": bool(candidates),
        "may_use_for_visual_correlation": bool(candidates),
        "node_world_transform": "unproven",
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def tracked_nodes_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    profile_ids: dict[tuple[int, ...], str],
    family_ids: dict[tuple[int, ...], str],
    family_records_by_id: dict[str, dict[str, Any]],
    chunked_values: list[int],
    component_by_node: list[int],
    components: list[list[int]],
    edge_records: list[dict[str, Any]],
    matrix_size: int,
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    degrees = q2m.bridge_degrees(edge_records, components)
    singletons = set(q2l.singleton_nodes(components))
    large_component = q2l.largest_component_id(components)
    records: dict[str, Any] = {}
    for node in TRACKED_NODES:
        if node >= matrix_size:
            records[str(node)] = {"status": "not_applicable_to_matrix_size"}
            continue
        profile = profiles[node]
        family_id = family_ids[profile]
        component_id = component_by_node[node]
        records[str(node)] = {
            "node": node,
            "x": node % q2i.logical_size_for_matrix(matrix_size),
            "y": node // q2i.logical_size_for_matrix(matrix_size),
            "row_sum": rows[node],
            "row_class": q2h.classify_sum(rows[node], matrix_size),
            "column_sum": columns[node],
            "column_class": q2h.classify_sum(columns[node], matrix_size),
            "component_id": component_id,
            "component_size": len(components[component_id]),
            "component_role": q2m.component_role(node, component_by_node, components, large_component, singletons),
            "profile_id": profile_ids[profile],
            "family_id": family_id,
            "family_node_count": family_records_by_id[family_id]["node_count"],
            "family_profile_count": family_records_by_id[family_id]["profile_count"],
            "slot_profile": list(profile),
            "profile_signature": profile_signature(profile),
            "code15_bridge_degree": {
                "source_count": degrees[node]["source_count"],
                "target_count": degrees[node]["target_count"],
                "total_endpoint_count": degrees[node]["total_endpoint_count"],
                "large_component_bridge_endpoint_count": degrees[node]["large_component_bridge_endpoint_count"],
                "singleton_bridge_endpoint_count": degrees[node]["singleton_bridge_endpoint_count"],
            },
            "history_context": {
                "q2e_q2f_endpoint": node in (369, 370),
                "q2g_endpoint": node in (59, 837),
            },
        }
    return {
        "probe": "q2p_tracked_profile_family_nodes",
        **metadata,
        "tracked_nodes": records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def interpretation_payload(
    metadata: dict[str, Any],
    family_records: list[dict[str, Any]],
    anchors: dict[str, Any],
    singleton_profile_exact_exclusive: bool,
) -> dict[str, Any]:
    singleton_family = next(
        (
            record
            for record in family_records
            if record["component_role_counts"].get("singleton_component", 0) == record["node_count"]
            and record["node_count"] > 0
        ),
        None,
    )
    role = "ambiguous"
    if singleton_family is not None and singleton_profile_exact_exclusive:
        role = "profile_level_node_class_descriptor_candidate"
    return {
        "probe": "q2p_profile_family_interpretation",
        **metadata,
        "packed4_1_profile_family_role": role,
        "singleton_profile_exact_exclusive": singleton_profile_exact_exclusive,
        "asymmetric_anchor_candidates_found": anchors["asymmetric_anchor_candidates_found"],
        "candidate_family_count": anchors["anchor_candidate_count"],
        "may_use_for_visual_correlation": anchors["may_use_for_visual_correlation"],
        "node_world_transform": "unproven",
        "interpretation_boundary": {
            "packed4_1_profile_family_role": "static family-level role only; not runtime semantics",
            "map_setting_node_world_transform": "unproven",
            "semantic_safety": "not proven",
            "asymmetric_anchor_candidates": "may only be used for a later read-only visual-correlation PR",
            "packed4_1": "read-only family comparison only; not decoded as editable",
            "30x30_table_coordinates": "not proven game-world coordinates",
        },
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "third_chunked_binary_runtime_probe_allowed": False,
        "map_editing_allowed": False,
        "next_recommended_step": "continue_static_decoding",
        "blocked_actions": [
            "third runtime mutation",
            "packed4_0 mutation",
            "packed4_1 mutation",
            "multi-edge or region mutation",
            "collision/path/spawn editing",
            "brush gameplay mask editing",
            "formal LOL map runtime export",
        ],
    }


def mask_to_image(nodes: list[int], logical_size: int, path: Path) -> None:
    node_set = set(nodes)
    image = Image.new("RGBA", (logical_size, logical_size), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(logical_size):
        for x in range(logical_size):
            if y * logical_size + x in node_set:
                pixels[x, y] = (0, 220, 255, 255)
    image.resize((logical_size * 16, logical_size * 16), Image.Resampling.NEAREST).save(path)


def make_contact_sheet(mask_paths: list[tuple[str, Path]], output_path: Path) -> None:
    if not mask_paths:
        return
    tile_size = 160
    columns = 5
    rows = math.ceil(len(mask_paths) / columns)
    sheet = Image.new("RGBA", (columns * tile_size, rows * (tile_size + 20)), (20, 20, 20, 255))
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate(mask_paths):
        with Image.open(path) as image:
            tile = image.convert("RGBA").resize((tile_size, tile_size), Image.Resampling.NEAREST)
        x = (index % columns) * tile_size
        y = (index // columns) * (tile_size + 20)
        sheet.alpha_composite(tile, (x, y))
        draw.text((x + 4, y + tile_size + 3), label, fill=(230, 230, 230, 255))
    sheet.save(output_path)


def write_family_masks(
    output_dir: Path,
    family_records: list[dict[str, Any]],
    family_nodes_by_id: dict[str, list[int]],
    logical_size: int,
    max_masks: int = 40,
) -> dict[str, Any]:
    mask_dir = output_dir / "profile_family_masks"
    mask_dir.mkdir(parents=True, exist_ok=True)
    selected = sorted(
        family_records,
        key=lambda record: (
            record["component_role_counts"].get("singleton_component", 0) != record["node_count"],
            -record["asymmetry"]["asymmetry_score"],
            record["node_count"],
            record["family_id"],
        ),
    )[:max_masks]
    created: list[dict[str, Any]] = []
    contact_inputs: list[tuple[str, Path]] = []
    for record in selected:
        path = mask_dir / f"{record['family_id']}_mask_30x30.png"
        mask_to_image(family_nodes_by_id[record["family_id"]], logical_size, path)
        created.append(
            {
                "family_id": record["family_id"],
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": rt.sha256_file(path),
            }
        )
        contact_inputs.append((f"{record['family_id']} n={record['node_count']}", path))
    contact_sheet = output_dir / CONTACT_SHEET
    make_contact_sheet(contact_inputs, contact_sheet)
    return {
        "profile_family_mask_dir": str(mask_dir),
        "profile_family_mask_count": len(created),
        "profile_family_masks": created,
        "contact_sheet": {
            "path": str(contact_sheet),
            "size": contact_sheet.stat().st_size,
            "sha256": rt.sha256_file(contact_sheet),
        }
        if contact_sheet.exists()
        else None,
    }


def analyze_packed4_1_profile_families(
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
    hamming_threshold: int = 2,
) -> dict[str, Any]:
    if hamming_threshold < 0:
        raise SystemExit("--hamming-threshold must be non-negative.")
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    ensure_paths_are_safe(input_path, output_dir)

    data, chunked, _packed0, packed1, matrix_size, component_by_node, components, edge_records = load_family_inputs(
        input_path,
        expected_sha256,
    )
    metadata = base_metadata(input_path, output_dir, data)
    logical_size, profiles = q2m.node_major_profiles(packed1, matrix_size)
    profile_ids, profile_counts = q2m.stable_profile_ids(profiles)
    by_profile = nodes_by_profile(profiles)
    hamming_families, hamming_edges = build_hamming_families(profile_counts, hamming_threshold)

    singletons = q2l.singleton_nodes(components)
    singleton_profiles = {profiles[node] for node in singletons}
    singleton_profile = next(iter(singleton_profiles)) if len(singleton_profiles) == 1 else None
    singleton_profile_exact_exclusive = (
        singleton_profile is not None
        and set(by_profile[singleton_profile]) == set(singletons)
    )
    node837_profile = profiles[837] if len(profiles) > 837 else None
    exact_families = [[profile] for profile in sorted(profile_counts, key=lambda profile: (-profile_counts[profile], profile))]
    family_records: list[dict[str, Any]] = []
    family_nodes_by_id: dict[str, list[int]] = {}
    for index, family in enumerate(exact_families, start=1):
        family_id = f"family_{index:04d}"
        nodes = family_nodes(family, by_profile)
        family_nodes_by_id[family_id] = nodes
        family_records.append(
            family_record(
                family_id,
                family,
                nodes,
                profile_ids,
                profile_counts,
                chunked,
                component_by_node,
                components,
                edge_records,
                matrix_size,
                singleton_profile,
                node837_profile,
            )
        )
    cluster_records: list[dict[str, Any]] = []
    for index, family in enumerate(hamming_families, start=1):
        cluster_records.append(
            family_record(
                f"family_{index:04d}",
                family,
                family_nodes(family, by_profile),
                profile_ids,
                profile_counts,
                chunked,
                component_by_node,
                components,
                edge_records,
                matrix_size,
                singleton_profile,
                node837_profile,
            )
        )
    family_records_by_id = {record["family_id"]: record for record in family_records}
    profile_to_family_id = {
        profile: family_records[index]["family_id"]
        for index, family in enumerate(exact_families)
        for profile in family
    }

    catalog = profile_family_catalog_payload(metadata, family_records, profile_counts)
    clusters = hamming_clusters_payload(metadata, cluster_records, hamming_edges, hamming_threshold)
    spatial = spatial_patterns_payload(metadata, family_records)
    component = component_correlation_payload(metadata, family_records)
    anchors = anchor_candidates_payload(metadata, family_records)
    tracked = tracked_nodes_payload(
        metadata,
        profiles,
        profile_ids,
        profile_to_family_id,
        family_records_by_id,
        chunked,
        component_by_node,
        components,
        edge_records,
        matrix_size,
    )
    interpretation = interpretation_payload(metadata, family_records, anchors, singleton_profile_exact_exclusive)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "packed4_1_profile_family_catalog": output_dir / "packed4_1_profile_family_catalog.json",
        "packed4_1_profile_hamming_clusters": output_dir / "packed4_1_profile_hamming_clusters.json",
        "packed4_1_profile_family_spatial_patterns": output_dir / "packed4_1_profile_family_spatial_patterns.json",
        "packed4_1_profile_family_component_correlation": output_dir / "packed4_1_profile_family_component_correlation.json",
        "packed4_1_profile_family_anchor_candidates": output_dir / "packed4_1_profile_family_anchor_candidates.json",
        "tracked_profile_family_nodes": output_dir / "tracked_profile_family_nodes.json",
        "q2p_profile_family_interpretation": output_dir / "q2p_profile_family_interpretation.json",
    }
    payloads = {
        "packed4_1_profile_family_catalog": catalog,
        "packed4_1_profile_hamming_clusters": clusters,
        "packed4_1_profile_family_spatial_patterns": spatial,
        "packed4_1_profile_family_component_correlation": component,
        "packed4_1_profile_family_anchor_candidates": anchors,
        "tracked_profile_family_nodes": tracked,
        "q2p_profile_family_interpretation": interpretation,
    }
    for key, path in outputs.items():
        path.write_text(json.dumps(payloads[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    mask_outputs = write_family_masks(output_dir, family_records, family_nodes_by_id, logical_size)

    return {
        "probe": "q2p_packed4_1_profile_family_analysis",
        **metadata,
        "outputs": {
            key: {"path": str(path), "size": path.stat().st_size, "sha256": rt.sha256_file(path)}
            for key, path in outputs.items()
        },
        "profile_family_mask_outputs": mask_outputs,
        "packed4_1_profile_family_role": interpretation["packed4_1_profile_family_role"],
        "asymmetric_anchor_candidates_found": interpretation["asymmetric_anchor_candidates_found"],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "third_chunked_binary_runtime_probe_allowed": False,
        "map_editing_allowed": False,
        "next_recommended_step": interpretation["next_recommended_step"],
    }


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "input_sha256": manifest["input_sha256"],
        "output_dir": manifest["output_dir"],
        "packed4_1_profile_family_role": manifest["packed4_1_profile_family_role"],
        "asymmetric_anchor_candidates_found": manifest["asymmetric_anchor_candidates_found"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": manifest["third_chunked_binary_runtime_probe_allowed"],
        "map_editing_allowed": manifest["map_editing_allowed"],
        "outputs": manifest["outputs"],
        "profile_family_mask_outputs": manifest["profile_family_mask_outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze packed4_1 node-major profile families without mutation.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--hamming-threshold", type=int, default=2)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = analyze_packed4_1_profile_families(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_sha256=args.expected_sha256 or None,
        hamming_threshold=args.hamming_threshold,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
