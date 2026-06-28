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
from tools import analyze_packed4_next_hop_semantics as q2i  # noqa: E402
from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2l_no15_singleton_components")
OUTPUT_FILES = (
    "no15_singleton_nodes.json",
    "no15_singleton_spatial_pattern.json",
    "code15_singleton_bridge_edges.json",
    "singleton_packed4_1_profiles.json",
    "q2l_singleton_component_interpretation.json",
)
TRACKED_NODES = (369, 370, 59, 837)
PRIOR_PROBES = (
    {
        "id": "q2e_q2f_369_370",
        "edge": [369, 370],
        "runtime_result": "loader_pass_extended_observation_pass",
        "semantic_effect_observed": False,
    },
    {
        "id": "q2g_59_837",
        "edge": [59, 837],
        "runtime_result": "loader_pass",
        "semantic_effect_observed": False,
    },
)


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def planned_output_paths(output_dir: Path) -> list[Path]:
    return [output_dir / name for name in OUTPUT_FILES]


def ensure_paths_are_safe(input_path: Path, output_dir: Path) -> None:
    inspect.ensure_outside_repo(input_path, "input")
    inspect.ensure_outside_repo(output_dir, "output directory")
    if is_under_mods_tree(output_dir):
        raise SystemExit("Refusing to write Q2l analysis output under a runtime mods tree.")
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


def load_graph_inputs(
    input_path: Path,
    expected_sha256: str | None,
) -> tuple[bytes, list[int], list[int], list[int], int, list[int], list[list[int]], list[dict[str, Any]]]:
    data, _document, chunked_values, packed0_values, packed1_values, matrix_size = q2k.load_layers(
        input_path,
        expected_sha256,
    )
    component_by_node, components, _graph_counts = q2k.build_no15_weak_components(
        chunked_values,
        packed0_values,
        matrix_size,
    )
    edge_records = q2k.code15_edge_records(chunked_values, packed0_values, matrix_size, component_by_node)
    return data, chunked_values, packed0_values, packed1_values, matrix_size, component_by_node, components, edge_records


def singleton_nodes(components: list[list[int]]) -> list[int]:
    return sorted(nodes[0] for nodes in components if len(nodes) == 1)


def largest_component_id(components: list[list[int]]) -> int:
    return max(range(len(components)), key=lambda component_id: len(components[component_id]))


def node_xy_record(node: int, logical_size: int) -> dict[str, int]:
    return {"node": node, "x": node % logical_size, "y": node // logical_size}


def row_column_class_payload(
    node: int,
    rows: list[int],
    columns: list[int],
    matrix_size: int,
    component_by_node: list[int],
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    return {
        "node": node,
        "x": node % logical_size,
        "y": node // logical_size,
        "component_id": component_by_node[node],
        "row_sum": rows[node],
        "row_class": q2h.classify_sum(rows[node], matrix_size),
        "column_sum": columns[node],
        "column_class": q2h.classify_sum(columns[node], matrix_size),
    }


def edge_position(node: int, logical_size: int) -> str:
    x = node % logical_size
    y = node // logical_size
    at_left = x == 0
    at_right = x == logical_size - 1
    at_top = y == 0
    at_bottom = y == logical_size - 1
    if (at_left or at_right) and (at_top or at_bottom):
        return "corner"
    if at_left or at_right or at_top or at_bottom:
        return "edge"
    return "interior"


def contiguous_runs(values: list[int]) -> list[list[int]]:
    if not values:
        return []
    runs: list[list[int]] = []
    current = [values[0]]
    for value in values[1:]:
        if value == current[-1] + 1:
            current.append(value)
        else:
            runs.append(current)
            current = [value]
    runs.append(current)
    return runs


def singleton_nodes_payload(
    metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
    component_by_node: list[int],
    components: list[list[int]],
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    singletons = singleton_nodes(components)
    class_counter = Counter()
    edge_counter = Counter()
    records: list[dict[str, Any]] = []
    for node in singletons:
        record = row_column_class_payload(node, rows, columns, matrix_size, component_by_node)
        record["edge_position"] = edge_position(node, logical_size)
        record["packed4_0_row_value_histogram"] = counter_payload(
            Counter(packed0_values[node * matrix_size : (node + 1) * matrix_size])
        )
        records.append(record)
        class_counter[f"{record['row_class']}|{record['column_class']}"] += 1
        edge_counter[record["edge_position"]] += 1
    return {
        "probe": "q2l_no15_singleton_nodes",
        **metadata,
        "singleton_count": len(singletons),
        "large_component_id": largest_component_id(components),
        "large_component_size": len(components[largest_component_id(components)]),
        "node_records": records,
        "row_column_class_pair_counts": counter_payload(class_counter),
        "edge_position_counts": counter_payload(edge_counter),
        "tracked_nodes": {
            str(node): row_column_class_payload(node, rows, columns, matrix_size, component_by_node)
            for node in TRACKED_NODES
            if node < matrix_size
        },
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def spatial_pattern_payload(
    metadata: dict[str, Any],
    components: list[list[int]],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    singletons = singleton_nodes(components)
    x_counter = Counter(node % logical_size for node in singletons)
    y_counter = Counter(node // logical_size for node in singletons)
    complete_rows = [row for row in range(logical_size) if y_counter[row] == logical_size]
    complete_columns = [column for column in range(logical_size) if x_counter[column] == logical_size]
    edge_counter = Counter(edge_position(node, logical_size) for node in singletons)
    diagonal_counts = {
        "main_diagonal": sum(1 for node in singletons if node % logical_size == node // logical_size),
        "anti_diagonal": sum(1 for node in singletons if node % logical_size + node // logical_size == logical_size - 1),
    }
    xs = sorted(x_counter)
    ys = sorted(y_counter)
    row_runs = contiguous_runs(sorted(y_counter))
    column_runs = contiguous_runs(sorted(x_counter))
    if len(complete_rows) == 3 and len(singletons) == 3 * logical_size:
        spatial_pattern = "three_complete_rows_candidate"
    elif len(complete_columns) == 3 and len(singletons) == 3 * logical_size:
        spatial_pattern = "three_complete_columns_candidate"
    elif edge_counter["edge"] + edge_counter["corner"] >= round(len(singletons) * 0.75):
        spatial_pattern = "border_candidate"
    elif len(row_runs) <= 3 or len(column_runs) <= 3:
        spatial_pattern = "band_candidate"
    else:
        spatial_pattern = "ambiguous"

    return {
        "probe": "q2l_no15_singleton_spatial_pattern",
        **metadata,
        "coordinate_boundary": "30x30 table coordinates are unproven game-world coordinates.",
        "singleton_count": len(singletons),
        "row_histogram": counter_payload(y_counter),
        "column_histogram": counter_payload(x_counter),
        "complete_rows": complete_rows,
        "complete_columns": complete_columns,
        "edge_distribution": counter_payload(edge_counter),
        "diagonal_counts": diagonal_counts,
        "bounding_box": {
            "min_x": min(xs) if xs else None,
            "max_x": max(xs) if xs else None,
            "min_y": min(ys) if ys else None,
            "max_y": max(ys) if ys else None,
        },
        "row_runs": row_runs,
        "column_runs": column_runs,
        "spatial_pattern": spatial_pattern,
        "singleton_xy_records": [node_xy_record(node, logical_size) for node in singletons],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def bridge_edges_payload(
    metadata: dict[str, Any],
    edge_records: list[dict[str, Any]],
    components: list[list[int]],
    matrix_size: int,
) -> dict[str, Any]:
    singletons = set(singleton_nodes(components))
    large_component = largest_component_id(components)
    singleton_out = Counter()
    singleton_in = Counter()
    pair_counts = Counter()
    category_counts = Counter()
    for record in edge_records:
        source = record["source"]
        target = record["target"]
        source_singleton = source in singletons
        target_singleton = target in singletons
        source_large = record["source_component"] == large_component
        target_large = record["target_component"] == large_component
        if source_singleton:
            singleton_out[source] += 1
        if target_singleton:
            singleton_in[target] += 1
        if source_singleton and target_singleton:
            category = "singleton_to_singleton"
        elif source_singleton and target_large:
            category = "singleton_to_large_component"
        elif source_large and target_singleton:
            category = "large_component_to_singleton"
        elif source_large or target_large:
            category = "large_component_to_other_non_singleton"
        else:
            category = "other_cross_component"
        category_counts[category] += 1
        pair_counts[f"{source}->{target}"] += 1

    singleton_records: list[dict[str, Any]] = []
    for node in sorted(singletons):
        out_count = singleton_out[node]
        in_count = singleton_in[node]
        singleton_records.append(
            {
                "node": node,
                "x": node % q2i.logical_size_for_matrix(matrix_size),
                "y": node // q2i.logical_size_for_matrix(matrix_size),
                "out_code15_bridge_degree": out_count,
                "in_code15_bridge_degree": in_count,
                "total_code15_bridge_degree": out_count + in_count,
                "symmetric_in_out_degree": out_count == in_count,
                "has_large_component_bridge": out_count > 0 or in_count > 0,
            }
        )
    bridge_nodes = [record for record in singleton_records if record["has_large_component_bridge"]]
    return {
        "probe": "q2l_code15_singleton_bridge_edges",
        **metadata,
        "edge_definition": "chunked_binary == 1 and packed4_0 == 15 and source != target",
        "large_component_id": large_component,
        "large_component_size": len(components[large_component]),
        "singleton_count": len(singletons),
        "category_counts": counter_payload(category_counts),
        "singleton_bridge_node_count": len(bridge_nodes),
        "all_singletons_have_code15_bridge": len(bridge_nodes) == len(singletons),
        "all_singleton_bridge_degrees_symmetric": all(record["symmetric_in_out_degree"] for record in singleton_records),
        "singleton_bridge_degree_histogram": counter_payload(
            Counter(record["total_code15_bridge_degree"] for record in singleton_records)
        ),
        "top_bridge_singletons": sorted(
            singleton_records,
            key=lambda item: (item["total_code15_bridge_degree"], item["out_code15_bridge_degree"], -item["node"]),
            reverse=True,
        )[:30],
        "singleton_bridge_records": singleton_records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def profile_for_assumption(values: list[int], node: int, matrix_size: int, logical_size: int, assumption: str) -> tuple[int, ...]:
    return tuple(q2k.node_profile(values, node, matrix_size, logical_size, assumption))


def profile_histogram(
    values: list[int],
    nodes: list[int],
    matrix_size: int,
    logical_size: int,
    assumption: str,
) -> Counter[tuple[int, ...]]:
    return Counter(profile_for_assumption(values, node, matrix_size, logical_size, assumption) for node in nodes)


def packed4_1_profiles_payload(
    metadata: dict[str, Any],
    packed1_values: list[int],
    components: list[list[int]],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    singletons = singleton_nodes(components)
    large_nodes = sorted(components[largest_component_id(components)])
    assumptions = ("node_major_900x30", "layer_major_30x900", "slices_30x30x30_layer_major")
    expected_count = matrix_size * logical_size
    if len(packed1_values) != expected_count:
        return {
            "probe": "q2l_singleton_packed4_1_profiles",
            **metadata,
            "packed4_1_value_count": len(packed1_values),
            "expected_count_for_900x30_assumptions": expected_count,
            "status": "unsupported_shape_for_profile_comparison",
            "runtime_mutation_allowed": False,
            "packed4_mutation_allowed": False,
            "map_editing_allowed": False,
        }

    assumption_payload: dict[str, Any] = {}
    for assumption in assumptions:
        singleton_profiles = profile_histogram(packed1_values, singletons, matrix_size, logical_size, assumption)
        large_profiles = profile_histogram(packed1_values, large_nodes, matrix_size, logical_size, assumption)
        singleton_profile_set = set(singleton_profiles)
        large_profile_set = set(large_profiles)
        shared_profiles = singleton_profile_set & large_profile_set
        singleton_values: list[int] = []
        large_values: list[int] = []
        for node in singletons:
            singleton_values.extend(profile_for_assumption(packed1_values, node, matrix_size, logical_size, assumption))
        for node in large_nodes:
            large_values.extend(profile_for_assumption(packed1_values, node, matrix_size, logical_size, assumption))
        assumption_payload[assumption] = {
            "singleton_unique_profile_count": len(singleton_profile_set),
            "large_component_unique_profile_count": len(large_profile_set),
            "shared_profile_count": len(shared_profiles),
            "singleton_profiles_disjoint_from_large": len(shared_profiles) == 0,
            "singleton_value_histogram": counter_payload(Counter(singleton_values)),
            "large_component_value_histogram": counter_payload(Counter(large_values)),
            "top_singleton_profiles": [
                {"profile": list(profile), "count": count} for profile, count in singleton_profiles.most_common(20)
            ],
            "top_large_component_profiles": [
                {"profile": list(profile), "count": count} for profile, count in large_profiles.most_common(20)
            ],
            "tracked_node_profiles": {
                str(node): list(profile_for_assumption(packed1_values, node, matrix_size, logical_size, assumption))
                for node in TRACKED_NODES
                if node < matrix_size
            },
            "singleton_distinguishing_signal": (
                "strong_unverified"
                if len(shared_profiles) == 0
                else "weak_or_absent"
            ),
        }

    return {
        "probe": "q2l_singleton_packed4_1_profiles",
        **metadata,
        "packed4_1_value_count": len(packed1_values),
        "reshape_assumptions": {
            "node_major_900x30": "node profile is packed4_1[node * 30 : node * 30 + 30]",
            "layer_major_30x900": "node profile is packed4_1[layer * 900 + node] for 30 layers",
            "slices_30x30x30_layer_major": "same indexing as layer_major, viewed as 30 table-coordinate 30x30 slices",
        },
        "assumptions": assumption_payload,
        "interpretation_boundary": "packed4_1 profile comparison is static only and does not approve packed4_1 mutation.",
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def interpretation_payload(
    metadata: dict[str, Any],
    spatial: dict[str, Any],
    bridges: dict[str, Any],
    profiles: dict[str, Any],
) -> dict[str, Any]:
    singleton_role = "ambiguous"
    if spatial["spatial_pattern"] != "ambiguous" and bridges["all_singletons_have_code15_bridge"]:
        singleton_role = "structured_special_node_set_candidate"
    profile_signals = {
        key: value.get("singleton_distinguishing_signal")
        for key, value in profiles.get("assumptions", {}).items()
    }
    return {
        "probe": "q2l_singleton_component_interpretation",
        **metadata,
        "no15_singleton_role": singleton_role,
        "evidence": {
            "singleton_count": spatial["singleton_count"],
            "spatial_pattern": spatial["spatial_pattern"],
            "complete_rows": spatial["complete_rows"],
            "complete_columns": spatial["complete_columns"],
            "edge_distribution": spatial["edge_distribution"],
            "all_singletons_have_code15_bridge": bridges["all_singletons_have_code15_bridge"],
            "all_singleton_bridge_degrees_symmetric": bridges["all_singleton_bridge_degrees_symmetric"],
            "singleton_bridge_degree_histogram": bridges["singleton_bridge_degree_histogram"],
            "packed4_1_singleton_distinguishing_signals": profile_signals,
        },
        "interpretation_boundary": {
            "no15_singleton_role": "static table-graph role only; not runtime semantics",
            "map_setting_node_world_transform": "unproven",
            "semantic_safety": "not proven",
            "packed4_1": "read-only profile comparison only; not decoded as editable",
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


def analyze_no15_singleton_components(
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
        packed0_values,
        packed1_values,
        matrix_size,
        component_by_node,
        components,
        edge_records,
    ) = load_graph_inputs(input_path, expected_sha256)
    metadata = base_metadata(input_path, output_dir, data)

    nodes = singleton_nodes_payload(metadata, chunked_values, packed0_values, matrix_size, component_by_node, components)
    spatial = spatial_pattern_payload(metadata, components, matrix_size)
    bridges = bridge_edges_payload(metadata, edge_records, components, matrix_size)
    profiles = packed4_1_profiles_payload(metadata, packed1_values, components, matrix_size)
    interpretation = interpretation_payload(metadata, spatial, bridges, profiles)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "no15_singleton_nodes": output_dir / "no15_singleton_nodes.json",
        "no15_singleton_spatial_pattern": output_dir / "no15_singleton_spatial_pattern.json",
        "code15_singleton_bridge_edges": output_dir / "code15_singleton_bridge_edges.json",
        "singleton_packed4_1_profiles": output_dir / "singleton_packed4_1_profiles.json",
        "q2l_singleton_component_interpretation": output_dir / "q2l_singleton_component_interpretation.json",
    }
    payloads = {
        "no15_singleton_nodes": nodes,
        "no15_singleton_spatial_pattern": spatial,
        "code15_singleton_bridge_edges": bridges,
        "singleton_packed4_1_profiles": profiles,
        "q2l_singleton_component_interpretation": interpretation,
    }
    for key, path in outputs.items():
        path.write_text(json.dumps(payloads[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    return {
        "probe": "q2l_no15_singleton_component_classification",
        **metadata,
        "outputs": {
            key: {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": rt.sha256_file(path),
            }
            for key, path in outputs.items()
        },
        "no15_singleton_role": interpretation["no15_singleton_role"],
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
        "no15_singleton_role": manifest["no15_singleton_role"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": manifest["third_chunked_binary_runtime_probe_allowed"],
        "map_editing_allowed": manifest["map_editing_allowed"],
        "outputs": manifest["outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify no15 singleton components without mutation.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = analyze_no15_singleton_components(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
