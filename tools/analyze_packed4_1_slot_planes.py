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
from tools import analyze_packed4_next_hop_semantics as q2i  # noqa: E402
from tools import analyze_packed4_1_node_profiles as q2m  # noqa: E402
from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2o_packed4_1_slot_planes")
JSON_OUTPUT_FILES = (
    "packed4_1_slot_value_histograms.json",
    "packed4_1_slot_spatial_patterns.json",
    "packed4_1_slot_component_correlation.json",
    "packed4_1_slot_pair_correlation.json",
    "profile0001_slot_signature_analysis.json",
    "tracked_node_slot_profiles.json",
    "q2o_packed4_1_slot_interpretation.json",
)
CONTACT_SHEET = "slot_masks/top_slot_value_masks_contact_sheet.png"
TRACKED_NODES = (369, 370, 59, 837, 126, 617, 654, 184, 773, 498)


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def planned_output_paths(output_dir: Path, logical_size: int = 30) -> list[Path]:
    paths = [output_dir / name for name in JSON_OUTPUT_FILES]
    paths.append(output_dir / CONTACT_SHEET)
    for slot in range(logical_size):
        for value in range(16):
            paths.append(output_dir / "slot_masks" / f"slot_{slot:02d}_value_{value}_mask.png")
    return paths


def ensure_paths_are_safe(input_path: Path, output_dir: Path) -> None:
    inspect.ensure_outside_repo(input_path, "input")
    inspect.ensure_outside_repo(output_dir, "output directory")
    if is_under_mods_tree(output_dir):
        raise SystemExit("Refusing to write Q2o analysis output under a runtime mods tree.")
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


def entropy(counter: Counter[int]) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    value = 0.0
    for count in counter.values():
        probability = count / total
        value -= probability * math.log2(probability)
    return value


def mutual_information(left: list[int], right: list[int]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    total = len(left)
    left_counts = Counter(left)
    right_counts = Counter(right)
    joint_counts = Counter(zip(left, right))
    result = 0.0
    for (left_value, right_value), count in joint_counts.items():
        pxy = count / total
        px = left_counts[left_value] / total
        py = right_counts[right_value] / total
        result += pxy * math.log2(pxy / (px * py))
    return result


def normalized_mutual_information(left: list[int], right: list[int]) -> float:
    denominator = max(entropy(Counter(left)), entropy(Counter(right)))
    if denominator <= 0:
        return 0.0
    return mutual_information(left, right) / denominator


def numeric_stats(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"min": None, "max": None, "average": None, "unique_values": []}
    return {
        "min": min(values),
        "max": max(values),
        "average": sum(values) / len(values),
        "unique_values": sorted(set(values)),
    }


def load_slot_inputs(
    input_path: Path,
    expected_sha256: str | None,
) -> tuple[bytes, list[int], list[int], list[int], int, list[int], list[list[int]], list[dict[str, Any]]]:
    return q2l.load_graph_inputs(input_path, expected_sha256)


def slot_values(profiles: list[tuple[int, ...]], slot: int) -> list[int]:
    return [profile[slot] for profile in profiles]


def node_xy_record(node: int, logical_size: int) -> dict[str, int]:
    return {"node": node, "x": node % logical_size, "y": node // logical_size}


def row_column_class_record(
    node: int,
    rows: list[int],
    columns: list[int],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    return {
        "node": node,
        "x": node % logical_size,
        "y": node // logical_size,
        "row_sum": rows[node],
        "row_class": q2h.classify_sum(rows[node], matrix_size),
        "column_sum": columns[node],
        "column_class": q2h.classify_sum(columns[node], matrix_size),
    }


def spatial_pattern_for_nodes(nodes: list[int], logical_size: int, singleton_set: set[int]) -> dict[str, Any]:
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
        pattern = "matches_no15_singleton_band"
    elif complete_rows or complete_columns:
        pattern = "complete_row_or_column_candidate"
    elif edge_counter["edge"] + edge_counter["corner"] >= round(len(nodes) * 0.75):
        pattern = "border_candidate"
    elif len(row_runs) <= 3 or len(column_runs) <= 3:
        pattern = "band_candidate"
    else:
        pattern = "ambiguous"
    return {
        "node_count": len(nodes),
        "spatial_pattern": pattern,
        "singleton_overlap_count": len(node_set & singleton_set),
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
        "node_xy_sample": [node_xy_record(node, logical_size) for node in nodes[:120]],
        "node_xy_sample_truncated": len(nodes) > 120,
    }


def mask_to_image(values: list[int], logical_size: int, path: Path) -> None:
    image = Image.new("RGBA", (logical_size, logical_size), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(logical_size):
        for x in range(logical_size):
            if values[y * logical_size + x]:
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


def slot_value_histograms_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    component_by_node: list[int],
    components: list[list[int]],
    edge_records: list[dict[str, Any]],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    singletons = set(q2l.singleton_nodes(components))
    large_component = q2l.largest_component_id(components)
    large_nodes = set(components[large_component])
    endpoint_nodes = {record["source"] for record in edge_records} | {record["target"] for record in edge_records}
    xs = [node % logical_size for node in range(matrix_size)]
    ys = [node // logical_size for node in range(matrix_size)]
    slot_records: list[dict[str, Any]] = []
    for slot in range(logical_size):
        values = slot_values(profiles, slot)
        value_counter = Counter(values)
        singleton_counter = Counter(values[node] for node in singletons)
        large_counter = Counter(values[node] for node in large_nodes)
        endpoint_counter = Counter(values[node] for node in endpoint_nodes)
        value_records = []
        for value in sorted(value_counter):
            singleton_count = singleton_counter[value]
            large_count = large_counter[value]
            endpoint_count = endpoint_counter[value]
            if singleton_count and not large_count:
                exclusivity = "singleton_only"
            elif large_count and not singleton_count:
                exclusivity = "large_component_only"
            elif singleton_count or large_count:
                exclusivity = "shared_singleton_large"
            else:
                exclusivity = "other_only"
            value_records.append(
                {
                    "value": value,
                    "count": value_counter[value],
                    "singleton_count": singleton_count,
                    "large_component_count": large_count,
                    "code15_endpoint_node_count": endpoint_count,
                    "exclusivity": exclusivity,
                    "singleton_ratio": singleton_count / len(singletons) if singletons else 0.0,
                    "large_component_ratio": large_count / len(large_nodes) if large_nodes else 0.0,
                }
            )
        slot_records.append(
            {
                "slot": slot,
                "value_histogram": counter_payload(value_counter),
                "entropy": round(entropy(value_counter), 6),
                "top_values": sorted(value_records, key=lambda item: (-item["count"], item["value"]))[:8],
                "value_records": value_records,
                "singleton_values": counter_payload(singleton_counter),
                "large_component_values": counter_payload(large_counter),
                "code15_endpoint_values": counter_payload(endpoint_counter),
                "normalized_mutual_information_with_x": round(normalized_mutual_information(values, xs), 6),
                "normalized_mutual_information_with_y": round(normalized_mutual_information(values, ys), 6),
            }
        )
    return {
        "probe": "q2o_packed4_1_slot_value_histograms",
        **metadata,
        "profile_definition": "node-major: packed4_1[node * 30 : node * 30 + 30]",
        "coordinate_boundary": "30x30 table coordinates are unproven game-world coordinates.",
        "slot_count": logical_size,
        "slot_records": slot_records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def slot_spatial_patterns_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    components: list[list[int]],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    singletons = set(q2l.singleton_nodes(components))
    selected_records: list[dict[str, Any]] = []
    all_summary: list[dict[str, Any]] = []
    for slot in range(logical_size):
        values = slot_values(profiles, slot)
        for value, count in sorted(Counter(values).items()):
            nodes = [node for node, node_value in enumerate(values) if node_value == value]
            spatial = spatial_pattern_for_nodes(nodes, logical_size, singletons)
            record = {
                "slot": slot,
                "value": value,
                "count": count,
                **spatial,
            }
            all_summary.append(
                {
                    "slot": slot,
                    "value": value,
                    "count": count,
                    "spatial_pattern": spatial["spatial_pattern"],
                    "singleton_overlap_count": spatial["singleton_overlap_count"],
                }
            )
            if spatial["spatial_pattern"] != "ambiguous" or spatial["singleton_overlap_count"] == len(singletons):
                selected_records.append(record)
    return {
        "probe": "q2o_packed4_1_slot_spatial_patterns",
        **metadata,
        "coordinate_boundary": "30x30 table coordinates are unproven game-world coordinates.",
        "selected_slot_value_patterns": selected_records,
        "slot_value_pattern_summary": all_summary,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def slot_component_correlation_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    chunked_values: list[int],
    component_by_node: list[int],
    components: list[list[int]],
    edge_records: list[dict[str, Any]],
    matrix_size: int,
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    singletons = set(q2l.singleton_nodes(components))
    large_component = q2l.largest_component_id(components)
    large_nodes = set(components[large_component])
    degrees = q2m.bridge_degrees(edge_records, components)
    records: list[dict[str, Any]] = []
    for slot in range(logical_size):
        values = slot_values(profiles, slot)
        for value in sorted(set(values)):
            nodes = [node for node, node_value in enumerate(values) if node_value == value]
            singleton_count = sum(1 for node in nodes if node in singletons)
            large_count = sum(1 for node in nodes if node in large_nodes)
            degree_values = [degrees[node]["total_endpoint_count"] for node in nodes]
            class_counts = Counter(
                f"{q2h.classify_sum(rows[node], matrix_size)}|{q2h.classify_sum(columns[node], matrix_size)}"
                for node in nodes
            )
            component_counts = Counter(component_by_node[node] for node in nodes)
            records.append(
                {
                    "slot": slot,
                    "value": value,
                    "node_count": len(nodes),
                    "singleton_count": singleton_count,
                    "large_component_count": large_count,
                    "other_component_count": len(nodes) - singleton_count - large_count,
                    "singleton_ratio": singleton_count / len(singletons) if singletons else 0.0,
                    "large_component_ratio": large_count / len(large_nodes) if large_nodes else 0.0,
                    "code15_endpoint_degree_stats": numeric_stats(degree_values),
                    "row_column_class_pair_counts": counter_payload(class_counts),
                    "component_id_counts_top": [
                        {
                            "component_id": component_id,
                            "component_size": len(components[component_id]),
                            "count": count,
                        }
                        for component_id, count in component_counts.most_common(10)
                    ],
                }
            )
    strong_records = [
        record
        for record in records
        if record["singleton_ratio"] == 1.0 and record["large_component_count"] == 0
    ]
    return {
        "probe": "q2o_packed4_1_slot_component_correlation",
        **metadata,
        "slot_value_records": records,
        "singleton_only_slot_values": strong_records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def slot_pair_correlation_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    slot_records = []
    for left in range(logical_size):
        left_values = slot_values(profiles, left)
        for right in range(left + 1, logical_size):
            right_values = slot_values(profiles, right)
            equal_count = sum(1 for a, b in zip(left_values, right_values) if a == b)
            slot_records.append(
                {
                    "slot_pair": [left, right],
                    "same_value_count": equal_count,
                    "same_value_ratio": round(equal_count / matrix_size, 6),
                    "normalized_mutual_information": round(normalized_mutual_information(left_values, right_values), 6),
                }
            )
    ranked_by_mi = sorted(slot_records, key=lambda record: record["normalized_mutual_information"], reverse=True)
    return {
        "probe": "q2o_packed4_1_slot_pair_correlation",
        **metadata,
        "top_slot_pairs_by_mutual_information": ranked_by_mi[:80],
        "top_slot_pairs_by_same_value_ratio": sorted(
            slot_records,
            key=lambda record: record["same_value_ratio"],
            reverse=True,
        )[:80],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def profile0001_signature_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
    components: list[list[int]],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    singletons = set(q2l.singleton_nodes(components))
    singleton_profiles = Counter(profiles[node] for node in singletons)
    profile = singleton_profiles.most_common(1)[0][0] if singleton_profiles else tuple()
    per_slot = []
    matching_profile_nodes = [node for node, node_profile in enumerate(profiles) if node_profile == profile]
    for slot, expected_value in enumerate(profile):
        values = slot_values(profiles, slot)
        matching_value_nodes = [node for node, value in enumerate(values) if value == expected_value]
        large_count = sum(1 for node in matching_value_nodes if node not in singletons)
        per_slot.append(
            {
                "slot": slot,
                "expected_value": expected_value,
                "parity": "even" if slot % 2 == 0 else "odd",
                "matches_singleton_nodes": sum(1 for node in singletons if values[node] == expected_value),
                "matching_value_node_count": len(matching_value_nodes),
                "matching_value_large_or_other_count": large_count,
                "slot_value_singleton_exclusive": large_count == 0,
            }
        )
    alternating_8_0 = all((value == 8 if index % 2 == 0 else value == 0) for index, value in enumerate(profile))
    return {
        "probe": "q2o_profile0001_slot_signature_analysis",
        **metadata,
        "profile_definition": "node-major: packed4_1[node * 30 : node * 30 + 30]",
        "singleton_profile": list(profile),
        "singleton_profile_node_count": len(matching_profile_nodes),
        "singleton_profile_matches_all_singletons": set(matching_profile_nodes) == singletons,
        "alternating_even_8_odd_0": alternating_8_0,
        "per_slot_signature": per_slot,
        "slot_value_all_singleton_exclusive": all(record["slot_value_singleton_exclusive"] for record in per_slot),
        "full_profile_singleton_exclusive": set(matching_profile_nodes) == singletons,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def tracked_nodes_payload(
    metadata: dict[str, Any],
    profiles: list[tuple[int, ...]],
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
        component_id = component_by_node[node]
        records[str(node)] = {
            **row_column_class_record(node, rows, columns, matrix_size),
            "component_id": component_id,
            "component_size": len(components[component_id]),
            "component_role": q2m.component_role(node, component_by_node, components, large_component, singletons),
            "slot_profile": list(profiles[node]),
            "slot_value_histogram": counter_payload(Counter(profiles[node])),
            "code15_bridge_degree": {
                "source_count": degrees[node]["source_count"],
                "target_count": degrees[node]["target_count"],
                "total_endpoint_count": degrees[node]["total_endpoint_count"],
                "large_component_bridge_endpoint_count": degrees[node]["large_component_bridge_endpoint_count"],
                "singleton_bridge_endpoint_count": degrees[node]["singleton_bridge_endpoint_count"],
            },
        }
    return {
        "probe": "q2o_tracked_node_slot_profiles",
        **metadata,
        "tracked_nodes": records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def write_slot_masks(
    output_dir: Path,
    profiles: list[tuple[int, ...]],
    logical_size: int,
    profile_signature: tuple[int, ...],
) -> dict[str, Any]:
    slot_mask_dir = output_dir / "slot_masks"
    slot_mask_dir.mkdir(parents=True, exist_ok=True)
    created: list[dict[str, Any]] = []
    contact_sheet_inputs: list[tuple[str, Path]] = []
    for slot in range(logical_size):
        values = slot_values(profiles, slot)
        for value in sorted(set(values)):
            path = slot_mask_dir / f"slot_{slot:02d}_value_{value}_mask.png"
            mask = [1 if node_value == value else 0 for node_value in values]
            mask_to_image(mask, logical_size, path)
            record = {"slot": slot, "value": value, "path": str(path), "size": path.stat().st_size, "sha256": rt.sha256_file(path)}
            created.append(record)
            if slot < len(profile_signature) and value == profile_signature[slot]:
                contact_sheet_inputs.append((f"s{slot:02d}=v{value}", path))
    contact_sheet_path = output_dir / CONTACT_SHEET
    make_contact_sheet(contact_sheet_inputs, contact_sheet_path)
    return {
        "slot_mask_dir": str(slot_mask_dir),
        "slot_value_mask_count": len(created),
        "slot_value_masks_sample": created[:80],
        "contact_sheet": {
            "path": str(contact_sheet_path),
            "size": contact_sheet_path.stat().st_size,
            "sha256": rt.sha256_file(contact_sheet_path),
        }
        if contact_sheet_path.exists()
        else None,
    }


def interpretation_payload(
    metadata: dict[str, Any],
    signature: dict[str, Any],
    component: dict[str, Any],
) -> dict[str, Any]:
    role = "ambiguous"
    if signature["full_profile_singleton_exclusive"] and signature["alternating_even_8_odd_0"]:
        role = "slot_level_node_class_descriptor_candidate"
    return {
        "probe": "q2o_packed4_1_slot_interpretation",
        **metadata,
        "packed4_1_slot_role": role,
        "evidence": {
            "singleton_profile": signature["singleton_profile"],
            "singleton_profile_node_count": signature["singleton_profile_node_count"],
            "full_profile_singleton_exclusive": signature["full_profile_singleton_exclusive"],
            "alternating_even_8_odd_0": signature["alternating_even_8_odd_0"],
            "slot_value_all_singleton_exclusive": signature["slot_value_all_singleton_exclusive"],
            "singleton_only_slot_value_count": len(component["singleton_only_slot_values"]),
        },
        "interpretation_boundary": {
            "packed4_1_slot_role": "static slot-plane role only; not runtime semantics",
            "map_setting_node_world_transform": "unproven",
            "semantic_safety": "not proven",
            "packed4_1": "read-only slot-plane comparison only; not decoded as editable",
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


def analyze_packed4_1_slot_planes(
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    ensure_paths_are_safe(input_path, output_dir)

    data, chunked, _packed0, packed1, matrix_size, component_by_node, components, edge_records = load_slot_inputs(
        input_path,
        expected_sha256,
    )
    metadata = base_metadata(input_path, output_dir, data)
    logical_size, profiles = q2m.node_major_profiles(packed1, matrix_size)

    histograms = slot_value_histograms_payload(metadata, profiles, component_by_node, components, edge_records, matrix_size)
    spatial = slot_spatial_patterns_payload(metadata, profiles, components, matrix_size)
    component = slot_component_correlation_payload(
        metadata,
        profiles,
        chunked,
        component_by_node,
        components,
        edge_records,
        matrix_size,
    )
    pairs = slot_pair_correlation_payload(metadata, profiles, matrix_size)
    signature = profile0001_signature_payload(metadata, profiles, components, matrix_size)
    tracked = tracked_nodes_payload(metadata, profiles, chunked, component_by_node, components, edge_records, matrix_size)
    interpretation = interpretation_payload(metadata, signature, component)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "packed4_1_slot_value_histograms": output_dir / "packed4_1_slot_value_histograms.json",
        "packed4_1_slot_spatial_patterns": output_dir / "packed4_1_slot_spatial_patterns.json",
        "packed4_1_slot_component_correlation": output_dir / "packed4_1_slot_component_correlation.json",
        "packed4_1_slot_pair_correlation": output_dir / "packed4_1_slot_pair_correlation.json",
        "profile0001_slot_signature_analysis": output_dir / "profile0001_slot_signature_analysis.json",
        "tracked_node_slot_profiles": output_dir / "tracked_node_slot_profiles.json",
        "q2o_packed4_1_slot_interpretation": output_dir / "q2o_packed4_1_slot_interpretation.json",
    }
    payloads = {
        "packed4_1_slot_value_histograms": histograms,
        "packed4_1_slot_spatial_patterns": spatial,
        "packed4_1_slot_component_correlation": component,
        "packed4_1_slot_pair_correlation": pairs,
        "profile0001_slot_signature_analysis": signature,
        "tracked_node_slot_profiles": tracked,
        "q2o_packed4_1_slot_interpretation": interpretation,
    }
    for key, path in outputs.items():
        path.write_text(json.dumps(payloads[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    mask_outputs = write_slot_masks(output_dir, profiles, logical_size, tuple(signature["singleton_profile"]))

    return {
        "probe": "q2o_packed4_1_slot_plane_analysis",
        **metadata,
        "outputs": {
            key: {"path": str(path), "size": path.stat().st_size, "sha256": rt.sha256_file(path)}
            for key, path in outputs.items()
        },
        "slot_mask_outputs": mask_outputs,
        "packed4_1_slot_role": interpretation["packed4_1_slot_role"],
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
        "packed4_1_slot_role": manifest["packed4_1_slot_role"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": manifest["third_chunked_binary_runtime_probe_allowed"],
        "map_editing_allowed": manifest["map_editing_allowed"],
        "outputs": manifest["outputs"],
        "slot_mask_outputs": manifest["slot_mask_outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze packed4_1 node-major slot planes without mutation.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = analyze_packed4_1_slot_planes(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
