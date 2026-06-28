from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import analyze_chunked_binary_probe_targets as q2h  # noqa: E402
from tools import analyze_code15_component_graph as q2k  # noqa: E402
from tools import analyze_no15_singleton_components as q2l  # noqa: E402
from tools import analyze_packed4_next_hop_semantics as q2i  # noqa: E402
from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2m_packed4_1_node_profiles")
OUTPUT_FILES = (
    "packed4_1_node_profile_catalog.json",
    "packed4_1_profile_spatial_patterns.json",
    "packed4_1_profile_component_correlation.json",
    "packed4_1_profile_bridge_correlation.json",
    "packed4_1_profile_tracked_nodes.json",
    "q2m_packed4_1_profile_interpretation.json",
)
TRACKED_NODES = (369, 370, 59, 837, 126, 617, 654, 184, 773, 498)


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def planned_output_paths(output_dir: Path) -> list[Path]:
    return [output_dir / name for name in OUTPUT_FILES]


def ensure_paths_are_safe(input_path: Path, output_dir: Path) -> None:
    inspect.ensure_outside_repo(input_path, "input")
    inspect.ensure_outside_repo(output_dir, "output directory")
    if is_under_mods_tree(output_dir):
        raise SystemExit("Refusing to write Q2m analysis output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(input_path, output_dir, "input")
    for output_path in planned_output_paths(output_dir):
        if output_path == input_path or inspect.paths_are_same_existing_file(output_path, input_path):
            raise SystemExit(f"Refusing to overwrite input through generated output path: {output_path}")
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")


def counter_payload(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


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


def load_profile_inputs(
    input_path: Path,
    expected_sha256: str | None,
) -> tuple[bytes, list[int], list[int], list[int], int, list[int], list[list[int]], list[dict[str, Any]]]:
    return q2l.load_graph_inputs(input_path, expected_sha256)


def logical_size_for_matrix(matrix_size: int) -> int:
    return q2i.logical_size_for_matrix(matrix_size)


def node_xy_record(node: int, logical_size: int) -> dict[str, int]:
    return {"node": node, "x": node % logical_size, "y": node // logical_size}


def node_major_profiles(
    packed1_values: list[int],
    matrix_size: int,
) -> tuple[int, list[tuple[int, ...]]]:
    logical_size = logical_size_for_matrix(matrix_size)
    expected_count = matrix_size * logical_size
    if len(packed1_values) != expected_count:
        raise SystemExit(
            f"packed4_1 has {len(packed1_values)} values; expected {expected_count} for node-major profiles."
        )
    profiles = [
        tuple(packed1_values[node * logical_size : node * logical_size + logical_size])
        for node in range(matrix_size)
    ]
    return logical_size, profiles


def stable_profile_ids(profiles: list[tuple[int, ...]]) -> tuple[dict[tuple[int, ...], str], Counter[tuple[int, ...]]]:
    counts = Counter(profiles)
    ranked_profiles = sorted(counts, key=lambda profile: (-counts[profile], profile))
    return {profile: f"profile_{index:04d}" for index, profile in enumerate(ranked_profiles, start=1)}, counts


def singleton_nodes(components: list[list[int]]) -> list[int]:
    return q2l.singleton_nodes(components)


def largest_component_id(components: list[list[int]]) -> int:
    return q2l.largest_component_id(components)


def component_role(
    node: int,
    component_by_node: list[int],
    components: list[list[int]],
    large_component: int,
    singletons: set[int],
) -> str:
    if node in singletons:
        return "singleton_component"
    if component_by_node[node] == large_component:
        return "large_component"
    if len(components[component_by_node[node]]) == 1:
        return "other_singleton_component"
    return "other_component"


def row_column_class_record(
    node: int,
    rows: list[int],
    columns: list[int],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = logical_size_for_matrix(matrix_size)
    return {
        "node": node,
        "x": node % logical_size,
        "y": node // logical_size,
        "row_sum": rows[node],
        "row_class": q2h.classify_sum(rows[node], matrix_size),
        "column_sum": columns[node],
        "column_class": q2h.classify_sum(columns[node], matrix_size),
    }


def bridge_degrees(
    edge_records: list[dict[str, Any]],
    components: list[list[int]],
) -> dict[int, dict[str, int]]:
    large_component = largest_component_id(components)
    singletons = set(singleton_nodes(components))
    degrees: dict[int, dict[str, int]] = defaultdict(
        lambda: {
            "source_count": 0,
            "target_count": 0,
            "total_endpoint_count": 0,
            "large_component_bridge_endpoint_count": 0,
            "singleton_bridge_endpoint_count": 0,
            "other_code15_endpoint_count": 0,
        }
    )
    for record in edge_records:
        source = record["source"]
        target = record["target"]
        source_singleton = source in singletons
        target_singleton = target in singletons
        source_large = record["source_component"] == large_component
        target_large = record["target_component"] == large_component
        for node, direction in ((source, "source_count"), (target, "target_count")):
            degrees[node][direction] += 1
            degrees[node]["total_endpoint_count"] += 1
        if (source_singleton and target_large) or (source_large and target_singleton):
            degrees[source]["large_component_bridge_endpoint_count"] += 1
            degrees[target]["large_component_bridge_endpoint_count"] += 1
        elif source_singleton and target_singleton:
            degrees[source]["singleton_bridge_endpoint_count"] += 1
            degrees[target]["singleton_bridge_endpoint_count"] += 1
        else:
            degrees[source]["other_code15_endpoint_count"] += 1
            degrees[target]["other_code15_endpoint_count"] += 1
    return degrees


def numeric_stats(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"min": None, "max": None, "average": None, "unique_values": []}
    return {
        "min": min(values),
        "max": max(values),
        "average": sum(values) / len(values),
        "unique_values": sorted(set(values)),
    }


def profile_catalog_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    profile_ids: dict[tuple[int, ...], str],
    profile_counts: Counter[tuple[int, ...]],
    chunked_values: list[int],
    component_by_node: list[int],
    components: list[list[int]],
    edge_records: list[dict[str, Any]],
    matrix_size: int,
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    large_component = largest_component_id(components)
    singletons = set(singleton_nodes(components))
    degrees = bridge_degrees(edge_records, components)
    nodes_by_profile: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for node, profile in enumerate(profiles):
        nodes_by_profile[profile].append(node)

    profile_records: list[dict[str, Any]] = []
    for profile in sorted(profile_counts, key=lambda item: (-profile_counts[item], item)):
        nodes = nodes_by_profile[profile]
        role_counts = Counter(
            component_role(node, component_by_node, components, large_component, singletons) for node in nodes
        )
        class_counts = Counter(
            f"{q2h.classify_sum(rows[node], matrix_size)}|{q2h.classify_sum(columns[node], matrix_size)}"
            for node in nodes
        )
        endpoint_degrees = [degrees[node]["total_endpoint_count"] for node in nodes]
        if role_counts["singleton_component"] == len(nodes):
            exclusive_role = "singleton_only"
        elif role_counts["large_component"] == len(nodes):
            exclusive_role = "large_component_only"
        elif role_counts["singleton_component"] and not role_counts["large_component"]:
            exclusive_role = "non_large_component_only"
        elif role_counts["large_component"] and not role_counts["singleton_component"]:
            exclusive_role = "non_singleton_only"
        else:
            exclusive_role = "mixed"
        profile_records.append(
            {
                "profile_id": profile_ids[profile],
                "profile": list(profile),
                "node_count": len(nodes),
                "node_sample": nodes[:80],
                "component_role_counts": counter_payload(role_counts),
                "exclusive_role": exclusive_role,
                "row_column_class_pair_counts": counter_payload(class_counts),
                "code15_endpoint_count": sum(endpoint_degrees),
                "nodes_with_code15_endpoint": sum(1 for value in endpoint_degrees if value),
                "code15_endpoint_degree_stats": numeric_stats(endpoint_degrees),
            }
        )

    singleton_profiles = Counter(profiles[node] for node in singletons)
    large_profiles = Counter(profiles[node] for node in components[large_component])
    singleton_profile_ids = [profile_ids[profile] for profile in singleton_profiles]
    shared_singleton_large = set(singleton_profiles) & set(large_profiles)
    singleton_profile_id = singleton_profile_ids[0] if len(singleton_profile_ids) == 1 else None
    return {
        "probe": "q2m_packed4_1_node_profile_catalog",
        **metadata,
        "profile_definition": "node-major: packed4_1[node * 30 : node * 30 + 30]",
        "coordinate_boundary": "30x30 table coordinates are unproven game-world coordinates.",
        "matrix_size": matrix_size,
        "logical_size": logical_size_for_matrix(matrix_size),
        "node_count": len(profiles),
        "unique_profile_count": len(profile_counts),
        "profile_frequency_histogram": counter_payload(Counter(profile_counts.values())),
        "top_profiles": profile_records[:30],
        "all_profile_records": profile_records,
        "singleton_profile_summary": {
            "singleton_node_count": len(singletons),
            "singleton_unique_profile_count": len(singleton_profiles),
            "singleton_profile_ids": singleton_profile_ids,
            "singleton_profile_id": singleton_profile_id,
            "shared_profile_count_with_large_component": len(shared_singleton_large),
            "singleton_profiles_disjoint_from_large": len(shared_singleton_large) == 0,
            "singleton_profile": list(next(iter(singleton_profiles))) if len(singleton_profiles) == 1 else None,
        },
        "large_component_profile_summary": {
            "large_component_id": large_component,
            "large_component_node_count": len(components[large_component]),
            "large_component_unique_profile_count": len(large_profiles),
            "top_large_component_profiles": [
                {"profile_id": profile_ids[profile], "profile": list(profile), "count": count}
                for profile, count in large_profiles.most_common(20)
            ],
        },
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def spatial_pattern_for_nodes(
    nodes: list[int],
    matrix_size: int,
    singleton_set: set[int],
) -> dict[str, Any]:
    logical_size = logical_size_for_matrix(matrix_size)
    node_set = set(nodes)
    x_counter = Counter(node % logical_size for node in nodes)
    y_counter = Counter(node // logical_size for node in nodes)
    edge_counter = Counter(q2l.edge_position(node, logical_size) for node in nodes)
    complete_rows = [row for row in range(logical_size) if y_counter[row] == logical_size]
    complete_columns = [column for column in range(logical_size) if x_counter[column] == logical_size]
    xs = sorted(x_counter)
    ys = sorted(y_counter)
    row_runs = q2l.contiguous_runs(sorted(y_counter))
    column_runs = q2l.contiguous_runs(sorted(x_counter))
    if node_set == singleton_set and node_set:
        spatial_pattern = "matches_no15_singleton_band"
    elif complete_rows or complete_columns:
        spatial_pattern = "complete_row_or_column_candidate"
    elif edge_counter["edge"] + edge_counter["corner"] >= round(len(nodes) * 0.75):
        spatial_pattern = "border_candidate"
    elif len(row_runs) <= 3 or len(column_runs) <= 3:
        spatial_pattern = "band_candidate"
    else:
        spatial_pattern = "ambiguous"
    return {
        "node_count": len(nodes),
        "row_histogram": counter_payload(y_counter),
        "column_histogram": counter_payload(x_counter),
        "complete_rows": complete_rows,
        "complete_columns": complete_columns,
        "edge_distribution": counter_payload(edge_counter),
        "bounding_box": {
            "min_x": min(xs) if xs else None,
            "max_x": max(xs) if xs else None,
            "min_y": min(ys) if ys else None,
            "max_y": max(ys) if ys else None,
        },
        "row_runs": row_runs,
        "column_runs": column_runs,
        "spatial_pattern": spatial_pattern,
        "singleton_overlap_count": len(node_set & singleton_set),
        "node_xy_records": [node_xy_record(node, logical_size) for node in nodes[:120]],
        "node_xy_records_truncated": len(nodes) > 120,
    }


def profile_spatial_patterns_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    profile_ids: dict[tuple[int, ...], str],
    profile_counts: Counter[tuple[int, ...]],
    components: list[list[int]],
    matrix_size: int,
) -> dict[str, Any]:
    nodes_by_profile: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for node, profile in enumerate(profiles):
        nodes_by_profile[profile].append(node)
    singleton_set = set(singleton_nodes(components))
    ranked_profiles = sorted(profile_counts, key=lambda profile: (-profile_counts[profile], profile))
    selected_profiles = ranked_profiles[:20]
    singleton_profiles = list({profiles[node] for node in singleton_set})
    for profile in singleton_profiles:
        if profile not in selected_profiles:
            selected_profiles.append(profile)
    records = []
    for profile in selected_profiles:
        nodes = nodes_by_profile[profile]
        records.append(
            {
                "profile_id": profile_ids[profile],
                "profile": list(profile),
                "rank_by_frequency": ranked_profiles.index(profile) + 1,
                **spatial_pattern_for_nodes(nodes, matrix_size, singleton_set),
            }
        )
    return {
        "probe": "q2m_packed4_1_profile_spatial_patterns",
        **metadata,
        "profile_definition": "node-major: packed4_1[node * 30 : node * 30 + 30]",
        "coordinate_boundary": "30x30 table coordinates are unproven game-world coordinates.",
        "selected_profile_count": len(records),
        "profile_spatial_patterns": records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def profile_component_correlation_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    profile_ids: dict[tuple[int, ...], str],
    component_by_node: list[int],
    components: list[list[int]],
    chunked_values: list[int],
    matrix_size: int,
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    large_component = largest_component_id(components)
    singletons = set(singleton_nodes(components))
    nodes_by_profile: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for node, profile in enumerate(profiles):
        nodes_by_profile[profile].append(node)
    profile_records: list[dict[str, Any]] = []
    for profile, nodes in sorted(nodes_by_profile.items(), key=lambda item: (-len(item[1]), item[0])):
        component_counts = Counter(component_by_node[node] for node in nodes)
        role_counts = Counter(
            component_role(node, component_by_node, components, large_component, singletons) for node in nodes
        )
        class_counts = Counter(
            f"{q2h.classify_sum(rows[node], matrix_size)}|{q2h.classify_sum(columns[node], matrix_size)}"
            for node in nodes
        )
        profile_records.append(
            {
                "profile_id": profile_ids[profile],
                "profile": list(profile),
                "node_count": len(nodes),
                "component_role_counts": counter_payload(role_counts),
                "component_id_counts_top": [
                    {
                        "component_id": component_id,
                        "component_size": len(components[component_id]),
                        "count": count,
                    }
                    for component_id, count in component_counts.most_common(20)
                ],
                "row_column_class_pair_counts": counter_payload(class_counts),
            }
        )

    component_records: list[dict[str, Any]] = []
    for component_id, nodes in sorted(enumerate(components), key=lambda item: (len(item[1]), -item[0]), reverse=True)[:30]:
        component_profiles = Counter(profiles[node] for node in nodes)
        component_records.append(
            {
                "component_id": component_id,
                "component_size": len(nodes),
                "unique_profile_count": len(component_profiles),
                "dominant_profile_id": profile_ids[component_profiles.most_common(1)[0][0]],
                "dominant_profile_ratio": component_profiles.most_common(1)[0][1] / len(nodes),
                "top_profiles": [
                    {"profile_id": profile_ids[profile], "count": count}
                    for profile, count in component_profiles.most_common(15)
                ],
            }
        )

    return {
        "probe": "q2m_packed4_1_profile_component_correlation",
        **metadata,
        "profile_definition": "node-major: packed4_1[node * 30 : node * 30 + 30]",
        "large_component_id": large_component,
        "large_component_size": len(components[large_component]),
        "singleton_component_count": len(singletons),
        "profile_component_records": profile_records,
        "component_profile_records_top": component_records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def profile_bridge_correlation_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    profile_ids: dict[tuple[int, ...], str],
    components: list[list[int]],
    edge_records: list[dict[str, Any]],
) -> dict[str, Any]:
    degrees = bridge_degrees(edge_records, components)
    singletons = set(singleton_nodes(components))
    large_component = largest_component_id(components)
    nodes_by_profile: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for node, profile in enumerate(profiles):
        nodes_by_profile[profile].append(node)

    profile_records: list[dict[str, Any]] = []
    for profile, nodes in sorted(nodes_by_profile.items(), key=lambda item: (-len(item[1]), item[0])):
        endpoint_degrees = [degrees[node]["total_endpoint_count"] for node in nodes]
        large_bridge = [degrees[node]["large_component_bridge_endpoint_count"] for node in nodes]
        singleton_bridge = [degrees[node]["singleton_bridge_endpoint_count"] for node in nodes]
        top_nodes = sorted(
            nodes,
            key=lambda node: (degrees[node]["total_endpoint_count"], degrees[node]["large_component_bridge_endpoint_count"], -node),
            reverse=True,
        )[:20]
        profile_records.append(
            {
                "profile_id": profile_ids[profile],
                "profile": list(profile),
                "node_count": len(nodes),
                "singleton_node_count": sum(1 for node in nodes if node in singletons),
                "large_component_node_count": sum(1 for node in nodes if node in components[large_component]),
                "total_code15_endpoint_count": sum(endpoint_degrees),
                "code15_endpoint_degree_stats": numeric_stats(endpoint_degrees),
                "large_component_bridge_endpoint_count": sum(large_bridge),
                "large_component_bridge_degree_stats": numeric_stats(large_bridge),
                "singleton_bridge_endpoint_count": sum(singleton_bridge),
                "singleton_bridge_degree_stats": numeric_stats(singleton_bridge),
                "top_bridge_nodes": [
                    {
                        "node": node,
                        "source_count": degrees[node]["source_count"],
                        "target_count": degrees[node]["target_count"],
                        "total_endpoint_count": degrees[node]["total_endpoint_count"],
                        "large_component_bridge_endpoint_count": degrees[node]["large_component_bridge_endpoint_count"],
                        "singleton_bridge_endpoint_count": degrees[node]["singleton_bridge_endpoint_count"],
                        "has_large_component_bridge": degrees[node]["large_component_bridge_endpoint_count"] > 0,
                        "has_singleton_bridge": degrees[node]["singleton_bridge_endpoint_count"] > 0,
                        "has_any_code15_bridge": degrees[node]["total_endpoint_count"] > 0,
                    }
                    for node in top_nodes
                ],
            }
        )

    singleton_profiles = Counter(profiles[node] for node in singletons)
    singleton_profile = next(iter(singleton_profiles)) if len(singleton_profiles) == 1 else None
    singleton_profile_id = profile_ids[singleton_profile] if singleton_profile is not None else None
    singleton_nodes_list = sorted(singletons)
    singleton_degrees = [degrees[node]["total_endpoint_count"] for node in singleton_nodes_list]
    return {
        "probe": "q2m_packed4_1_profile_bridge_correlation",
        **metadata,
        "edge_definition": "code15 bridge means chunked_binary == 1 and packed4_0 == 15 and source != target",
        "profile_definition": "node-major: packed4_1[node * 30 : node * 30 + 30]",
        "singleton_profile_id": singleton_profile_id,
        "singleton_profile_bridge_degree_stats": numeric_stats(singleton_degrees),
        "singleton_profile_bridge_degree_variation_note": (
            "same profile has varied bridge degrees; profile may be a class marker rather than a bridge-strength descriptor"
            if len(set(singleton_degrees)) > 1
            else "same profile has uniform observed bridge degree in this static graph"
        ),
        "profile_bridge_records": profile_records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def tracked_nodes_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    profile_ids: dict[tuple[int, ...], str],
    chunked_values: list[int],
    component_by_node: list[int],
    components: list[list[int]],
    edge_records: list[dict[str, Any]],
    matrix_size: int,
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    degrees = bridge_degrees(edge_records, components)
    singletons = set(singleton_nodes(components))
    large_component = largest_component_id(components)
    records: dict[str, Any] = {}
    for node in TRACKED_NODES:
        if node >= matrix_size:
            records[str(node)] = {"status": "not_applicable_to_matrix_size"}
            continue
        component_id = component_by_node[node]
        records[str(node)] = {
            **row_column_class_record(node, rows, columns, matrix_size),
            "component_id": component_id,
            "component_size": len(components[component_id]),
            "component_role": component_role(node, component_by_node, components, large_component, singletons),
            "profile_id": profile_ids[profiles[node]],
            "profile": list(profiles[node]),
            "code15_bridge_degree": {
                "source_count": degrees[node]["source_count"],
                "target_count": degrees[node]["target_count"],
                "total_endpoint_count": degrees[node]["total_endpoint_count"],
                "large_component_bridge_endpoint_count": degrees[node]["large_component_bridge_endpoint_count"],
                "singleton_bridge_endpoint_count": degrees[node]["singleton_bridge_endpoint_count"],
                "has_large_component_bridge": degrees[node]["large_component_bridge_endpoint_count"] > 0,
                "has_singleton_bridge": degrees[node]["singleton_bridge_endpoint_count"] > 0,
                "has_any_code15_bridge": degrees[node]["total_endpoint_count"] > 0,
            },
        }
    return {
        "probe": "q2m_packed4_1_profile_tracked_nodes",
        **metadata,
        "tracked_node_note": "Tracked nodes include prior probes and top Q2l bridge singleton nodes.",
        "tracked_nodes": records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def interpretation_payload(
    metadata: dict[str, Any],
    catalog: dict[str, Any],
    bridge: dict[str, Any],
) -> dict[str, Any]:
    singleton_summary = catalog["singleton_profile_summary"]
    role = "ambiguous"
    if (
        singleton_summary["singleton_unique_profile_count"] == 1
        and singleton_summary["singleton_profiles_disjoint_from_large"]
        and singleton_summary["singleton_node_count"] > 0
    ):
        role = "node_class_descriptor_candidate"
    return {
        "probe": "q2m_packed4_1_profile_interpretation",
        **metadata,
        "packed4_1_node_major_role": role,
        "evidence": {
            "unique_profile_count": catalog["unique_profile_count"],
            "singleton_node_count": singleton_summary["singleton_node_count"],
            "singleton_unique_profile_count": singleton_summary["singleton_unique_profile_count"],
            "singleton_profile_id": singleton_summary["singleton_profile_id"],
            "singleton_profiles_disjoint_from_large": singleton_summary["singleton_profiles_disjoint_from_large"],
            "large_component_unique_profile_count": catalog["large_component_profile_summary"][
                "large_component_unique_profile_count"
            ],
            "singleton_profile_bridge_degree_stats": bridge["singleton_profile_bridge_degree_stats"],
            "singleton_profile_bridge_degree_variation_note": bridge["singleton_profile_bridge_degree_variation_note"],
        },
        "interpretation_boundary": {
            "packed4_1_node_major_role": "static node-profile role only; not runtime semantics",
            "map_setting_node_world_transform": "unproven",
            "semantic_safety": "not proven",
            "packed4_1": "read-only profile comparison only; not decoded as editable",
            "30x30_table_coordinates": "not proven game-world coordinates",
        },
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "third_chunked_binary_runtime_probe_allowed": False,
        "map_editing_allowed": False,
        "next_recommended_step": "continue_static_decoding",
        "blocked_actions": [
            "third chunked_binary edge runtime probe",
            "packed4_0 mutation",
            "packed4_1 mutation",
            "multi-edge or region mutation",
            "collision/path/spawn export",
            "visual synchronization",
            "formal LOL map runtime export",
        ],
    }


def analyze_packed4_1_node_profiles(
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    ensure_paths_are_safe(input_path, output_dir)

    (
        data,
        chunked_values,
        _packed0_values,
        packed1_values,
        matrix_size,
        component_by_node,
        components,
        edge_records,
    ) = load_profile_inputs(input_path, expected_sha256)
    metadata = base_metadata(input_path, output_dir, data)
    _logical_size, profiles = node_major_profiles(packed1_values, matrix_size)
    profile_ids, profile_counts = stable_profile_ids(profiles)

    catalog = profile_catalog_payload(
        metadata,
        profiles,
        profile_ids,
        profile_counts,
        chunked_values,
        component_by_node,
        components,
        edge_records,
        matrix_size,
    )
    spatial = profile_spatial_patterns_payload(metadata, profiles, profile_ids, profile_counts, components, matrix_size)
    component = profile_component_correlation_payload(
        metadata,
        profiles,
        profile_ids,
        component_by_node,
        components,
        chunked_values,
        matrix_size,
    )
    bridge = profile_bridge_correlation_payload(metadata, profiles, profile_ids, components, edge_records)
    tracked = tracked_nodes_payload(
        metadata,
        profiles,
        profile_ids,
        chunked_values,
        component_by_node,
        components,
        edge_records,
        matrix_size,
    )
    interpretation = interpretation_payload(metadata, catalog, bridge)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "packed4_1_node_profile_catalog": output_dir / "packed4_1_node_profile_catalog.json",
        "packed4_1_profile_spatial_patterns": output_dir / "packed4_1_profile_spatial_patterns.json",
        "packed4_1_profile_component_correlation": output_dir / "packed4_1_profile_component_correlation.json",
        "packed4_1_profile_bridge_correlation": output_dir / "packed4_1_profile_bridge_correlation.json",
        "packed4_1_profile_tracked_nodes": output_dir / "packed4_1_profile_tracked_nodes.json",
        "q2m_packed4_1_profile_interpretation": output_dir / "q2m_packed4_1_profile_interpretation.json",
    }
    payloads = {
        "packed4_1_node_profile_catalog": catalog,
        "packed4_1_profile_spatial_patterns": spatial,
        "packed4_1_profile_component_correlation": component,
        "packed4_1_profile_bridge_correlation": bridge,
        "packed4_1_profile_tracked_nodes": tracked,
        "q2m_packed4_1_profile_interpretation": interpretation,
    }
    for key, path in outputs.items():
        path.write_text(json.dumps(payloads[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    return {
        "probe": "q2m_packed4_1_node_profile_analysis",
        **metadata,
        "outputs": {
            key: {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": rt.sha256_file(path),
            }
            for key, path in outputs.items()
        },
        "packed4_1_node_major_role": interpretation["packed4_1_node_major_role"],
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
        "packed4_1_node_major_role": manifest["packed4_1_node_major_role"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": manifest["third_chunked_binary_runtime_probe_allowed"],
        "map_editing_allowed": manifest["map_editing_allowed"],
        "outputs": manifest["outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze packed4_1 node-major profiles without mutation.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = analyze_packed4_1_node_profiles(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
