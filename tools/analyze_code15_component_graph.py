from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import analyze_chunked_binary_probe_targets as q2h  # noqa: E402
from tools import analyze_packed4_next_hop_semantics as q2i  # noqa: E402
from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2k_code15_component_graph")
OUTPUT_FILES = (
    "no15_component_summary.json",
    "code15_cross_component_edges.json",
    "code15_component_pair_matrix.json",
    "prior_probe_component_context.json",
    "packed4_1_component_correlation.json",
    "q2k_code15_component_interpretation.json",
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
        raise SystemExit("Refusing to write Q2k analysis output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(input_path, output_dir, "input")
    for output_path in planned_output_paths(output_dir):
        if output_path == input_path or inspect.paths_are_same_existing_file(output_path, input_path):
            raise SystemExit(f"Refusing to overwrite input through generated output path: {output_path}")
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")


def counter_payload(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def load_layers(
    input_path: Path,
    expected_sha256: str | None,
) -> tuple[bytes, rt.MapSettingDocument, list[int], list[int], list[int], int]:
    data = input_path.read_bytes()
    input_sha256 = rt.sha256_bytes(data)
    if expected_sha256 and input_sha256.lower() != expected_sha256.lower():
        raise SystemExit(f"Input SHA-256 {input_sha256} does not match expected {expected_sha256}.")
    document = rt.decode_map_setting(data)
    if len(document.packed4_layers) < 2:
        raise SystemExit("Expected packed4_0 and packed4_1 layers for Q2k component analysis.")
    chunked_values, width, height = inspect.flatten_chunked_binary_layer(document.chunked_binary_layer)
    if width != height:
        raise SystemExit(f"Expected square chunked relation matrix, got {width}x{height}.")
    packed0_values = inspect.unpack_packed4_layer(document.packed4_layers[0])
    if len(packed0_values) != width * height:
        raise SystemExit("packed4_0 cell count does not match chunked_binary matrix.")
    packed1_values = inspect.unpack_packed4_layer(document.packed4_layers[1])
    return data, document, chunked_values, packed0_values, packed1_values, width


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


def build_no15_weak_components(
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
) -> tuple[list[int], list[list[int]], dict[str, int]]:
    adjacency: list[set[int]] = [set() for _ in range(matrix_size)]
    directed_edge_count = 0
    no15_self_count = 0
    for source in range(matrix_size):
        base = source * matrix_size
        for target in range(matrix_size):
            if chunked_values[base + target] != 1 or packed0_values[base + target] == 15:
                continue
            if source == target:
                no15_self_count += 1
                continue
            directed_edge_count += 1
            adjacency[source].add(target)
            adjacency[target].add(source)

    component_by_node = [-1] * matrix_size
    components: list[list[int]] = []
    for node in range(matrix_size):
        if component_by_node[node] != -1:
            continue
        component_id = len(components)
        component_nodes: list[int] = []
        queue: deque[int] = deque([node])
        component_by_node[node] = component_id
        while queue:
            current = queue.popleft()
            component_nodes.append(current)
            for target in sorted(adjacency[current]):
                if component_by_node[target] != -1:
                    continue
                component_by_node[target] = component_id
                queue.append(target)
        components.append(component_nodes)
    undirected_edge_count = sum(len(neighbors) for neighbors in adjacency) // 2
    return (
        component_by_node,
        components,
        {
            "directed_no15_edge_count": directed_edge_count,
            "undirected_no15_edge_count": undirected_edge_count,
            "no15_self_edge_count": no15_self_count,
        },
    )


def node_class_record(
    node: int,
    rows: list[int],
    columns: list[int],
    matrix_size: int,
    component_by_node: list[int],
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    return {
        "node": node,
        "xy_30x30_unproven": q2i.node_xy(node, logical_size),
        "component_id": component_by_node[node],
        "row_sum": rows[node],
        "row_class": q2h.classify_sum(rows[node], matrix_size),
        "column_sum": columns[node],
        "column_class": q2h.classify_sum(columns[node], matrix_size),
    }


def component_record(
    component_id: int,
    nodes: list[int],
    rows: list[int],
    matrix_size: int,
    limit: int = 30,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    class_counts = Counter(q2h.classify_sum(rows[node], matrix_size) for node in nodes)
    return {
        "component_id": component_id,
        "size": len(nodes),
        "node_sample": nodes[:limit],
        "node_xy_sample": [q2i.node_xy(node, logical_size) for node in nodes[: min(limit, len(nodes))]],
        "row_class_counts": counter_payload(class_counts),
        "contains_tracked_nodes": [node for node in TRACKED_NODES if node in nodes],
    }


def no15_component_summary_payload(
    metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
    component_by_node: list[int],
    components: list[list[int]],
    graph_counts: dict[str, int],
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    size_counter = Counter(len(component) for component in components)
    ranked_components = sorted(
        enumerate(components),
        key=lambda item: (len(item[1]), -item[0]),
        reverse=True,
    )
    tiny_components = [
        component_record(component_id, nodes, rows, matrix_size, limit=12)
        for component_id, nodes in ranked_components
        if len(nodes) <= 3
    ]
    return {
        "probe": "q2k_no15_component_summary",
        **metadata,
        "graph_definition": {
            "nodes": matrix_size,
            "component_type": "weak components over no-15 connected relation",
            "edge_condition": "chunked_binary == 1 and packed4_0 != 15 and source != target",
            "coordinate_boundary": "30x30 table coordinates are unproven game-world coordinates.",
        },
        "component_count": len(components),
        "component_size_histogram": counter_payload(size_counter),
        **graph_counts,
        "largest_components": [
            component_record(component_id, nodes, rows, matrix_size)
            for component_id, nodes in ranked_components[:20]
        ],
        "isolated_or_tiny_components": {
            "count": len(tiny_components),
            "sample": tiny_components[:40],
            "truncated": len(tiny_components) > 40,
        },
        "tracked_nodes": {
            str(node): node_class_record(node, rows, columns, matrix_size, component_by_node)
            for node in TRACKED_NODES
            if node < matrix_size
        },
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
    }


def code15_edge_records(
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
    component_by_node: list[int],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source in range(matrix_size):
        base = source * matrix_size
        for target in range(matrix_size):
            index = base + target
            if source == target or chunked_values[index] != 1 or packed0_values[index] != 15:
                continue
            records.append(
                {
                    "source": source,
                    "target": target,
                    "source_component": component_by_node[source],
                    "target_component": component_by_node[target],
                }
            )
    return records


def component_pair_key(source_component: int, target_component: int) -> str:
    return f"{source_component}->{target_component}"


def normalized_pair_key(left: int, right: int) -> str:
    low, high = sorted((left, right))
    return f"{low}<->{high}"


def code15_cross_component_payload(
    metadata: dict[str, Any],
    edge_records: list[dict[str, Any]],
    chunked_values: list[int],
    matrix_size: int,
    component_by_node: list[int],
    components: list[list[int]],
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    same_component_count = 0
    cross_component_count = 0
    directed_pair_counts: Counter[str] = Counter()
    normalized_pair_counts: Counter[str] = Counter()
    source_component_counts: Counter[int] = Counter()
    target_component_counts: Counter[int] = Counter()
    source_node_counts: Counter[int] = Counter()
    target_node_counts: Counter[int] = Counter()
    source_class_counts: Counter[str] = Counter()
    target_class_counts: Counter[str] = Counter()
    class_pair_counts: Counter[str] = Counter()

    for record in edge_records:
        source = record["source"]
        target = record["target"]
        source_component = record["source_component"]
        target_component = record["target_component"]
        if source_component == target_component:
            same_component_count += 1
        else:
            cross_component_count += 1
        directed_pair_counts[component_pair_key(source_component, target_component)] += 1
        normalized_pair_counts[normalized_pair_key(source_component, target_component)] += 1
        source_component_counts[source_component] += 1
        target_component_counts[target_component] += 1
        source_node_counts[source] += 1
        target_node_counts[target] += 1
        source_class = q2h.classify_sum(rows[source], matrix_size)
        target_class = q2h.classify_sum(rows[target], matrix_size)
        source_class_counts[source_class] += 1
        target_class_counts[target_class] += 1
        class_pair_counts[f"{source_class}->{target_class}"] += 1

    total = len(edge_records)

    def component_hub_records(counter: Counter[int], label: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for component_id, count in counter.most_common(20):
            nodes = components[component_id]
            records.append(
                {
                    "component_id": component_id,
                    "role": label,
                    "code15_edge_count": count,
                    "component_size": len(nodes),
                    "contains_tracked_nodes": [node for node in TRACKED_NODES if node in nodes],
                }
            )
        return records

    def node_endpoint_records(counter: Counter[int], label: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for node, count in counter.most_common(20):
            record = node_class_record(node, rows, columns, matrix_size, component_by_node)
            record["role"] = label
            record["code15_edge_count"] = count
            records.append(record)
        return records

    node_837 = (
        {
            **node_class_record(837, rows, columns, matrix_size, component_by_node),
            "code15_source_edges": source_node_counts[837],
            "code15_target_edges": target_node_counts[837],
            "code15_total_endpoint_edges": source_node_counts[837] + target_node_counts[837],
            "non15_component_size": len(components[component_by_node[837]]),
        }
        if 837 < matrix_size
        else None
    )

    return {
        "probe": "q2k_code15_cross_component_edges",
        **metadata,
        "edge_definition": "chunked_binary == 1 and packed4_0 == 15 and source != target",
        "code15_connected_nonself_edge_count": total,
        "same_component_count": same_component_count,
        "cross_component_count": cross_component_count,
        "cross_component_ratio": cross_component_count / total if total else None,
        "same_component_ratio": same_component_count / total if total else None,
        "directed_component_pair_top": [
            {"pair": key, "count": count} for key, count in directed_pair_counts.most_common(30)
        ],
        "normalized_component_pair_top": [
            {"pair": key, "count": count} for key, count in normalized_pair_counts.most_common(30)
        ],
        "hub_components": {
            "source": component_hub_records(source_component_counts, "source"),
            "target": component_hub_records(target_component_counts, "target"),
        },
        "top_endpoint_nodes": {
            "source": node_endpoint_records(source_node_counts, "source"),
            "target": node_endpoint_records(target_node_counts, "target"),
        },
        "endpoint_row_class_counts": {
            "source": counter_payload(source_class_counts),
            "target": counter_payload(target_class_counts),
            "source_to_target": counter_payload(class_pair_counts),
        },
        "node_837": node_837,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
    }


def component_pair_matrix_payload(
    metadata: dict[str, Any],
    edge_records: list[dict[str, Any]],
    components: list[list[int]],
) -> dict[str, Any]:
    pair_counts: Counter[tuple[int, int]] = Counter()
    normalized_pair_counts: Counter[tuple[int, int]] = Counter()
    source_component_counts: Counter[int] = Counter()
    target_component_counts: Counter[int] = Counter()
    for record in edge_records:
        source_component = record["source_component"]
        target_component = record["target_component"]
        pair_counts[(source_component, target_component)] += 1
        normalized_pair_counts[tuple(sorted((source_component, target_component)))] += 1
        source_component_counts[source_component] += 1
        target_component_counts[target_component] += 1

    def matrix_record(pair: tuple[int, int], count: int) -> dict[str, Any]:
        source_component, target_component = pair
        return {
            "source_component": source_component,
            "target_component": target_component,
            "count": count,
            "source_component_size": len(components[source_component]),
            "target_component_size": len(components[target_component]),
            "same_component": source_component == target_component,
        }

    return {
        "probe": "q2k_code15_component_pair_matrix",
        **metadata,
        "component_count": len(components),
        "sparse_matrix_note": "Only nonzero code15 component pairs are emitted; no dense payload is written.",
        "nonzero_directed_pair_count": len(pair_counts),
        "nonzero_normalized_pair_count": len(normalized_pair_counts),
        "top_directed_pairs": [
            matrix_record(pair, count) for pair, count in pair_counts.most_common(80)
        ],
        "top_normalized_pairs": [
            {
                "component_a": pair[0],
                "component_b": pair[1],
                "count": count,
                "component_a_size": len(components[pair[0]]),
                "component_b_size": len(components[pair[1]]),
                "same_component": pair[0] == pair[1],
            }
            for pair, count in normalized_pair_counts.most_common(80)
        ],
        "component_code15_degree_top": [
            {
                "component_id": component_id,
                "source_count": source_component_counts[component_id],
                "target_count": target_component_counts[component_id],
                "total_endpoint_count": source_component_counts[component_id] + target_component_counts[component_id],
                "component_size": len(components[component_id]),
            }
            for component_id, _count in Counter(
                {
                    component_id: source_component_counts[component_id] + target_component_counts[component_id]
                    for component_id in set(source_component_counts) | set(target_component_counts)
                }
            ).most_common(40)
        ],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
    }


def prior_probe_component_payload(
    metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
    component_by_node: list[int],
    components: list[list[int]],
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    probes: list[dict[str, Any]] = []
    for probe in PRIOR_PROBES:
        source, target = probe["edge"]
        if source >= matrix_size or target >= matrix_size:
            probes.append({"id": probe["id"], "edge": probe["edge"], "status": "not_applicable_to_matrix_size"})
            continue
        forward_index = source * matrix_size + target
        reverse_index = target * matrix_size + source
        source_component = component_by_node[source]
        target_component = component_by_node[target]
        probes.append(
            {
                "id": probe["id"],
                "edge": probe["edge"],
                "runtime_result": probe["runtime_result"],
                "semantic_effect_observed": probe["semantic_effect_observed"],
                "source": node_class_record(source, rows, columns, matrix_size, component_by_node),
                "target": node_class_record(target, rows, columns, matrix_size, component_by_node),
                "source_component_size": len(components[source_component]),
                "target_component_size": len(components[target_component]),
                "same_no15_component": source_component == target_component,
                "component_pair": component_pair_key(source_component, target_component),
                "cells": [
                    {
                        "source_node": source,
                        "target_node": target,
                        "source_xy_30x30_unproven": q2i.node_xy(source, logical_size),
                        "target_xy_30x30_unproven": q2i.node_xy(target, logical_size),
                        "chunked_value": chunked_values[forward_index],
                        "packed4_0_value": packed0_values[forward_index],
                        "is_code15_cross_component": (
                            chunked_values[forward_index] == 1
                            and packed0_values[forward_index] == 15
                            and source_component != target_component
                        ),
                    },
                    {
                        "source_node": target,
                        "target_node": source,
                        "source_xy_30x30_unproven": q2i.node_xy(target, logical_size),
                        "target_xy_30x30_unproven": q2i.node_xy(source, logical_size),
                        "chunked_value": chunked_values[reverse_index],
                        "packed4_0_value": packed0_values[reverse_index],
                        "is_code15_cross_component": (
                            chunked_values[reverse_index] == 1
                            and packed0_values[reverse_index] == 15
                            and source_component != target_component
                        ),
                    },
                ],
            }
        )
    return {
        "probe": "q2k_prior_probe_component_context",
        **metadata,
        "prior_probes": probes,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
    }


def value_histogram(values: list[int]) -> dict[str, int]:
    return counter_payload(Counter(values))


def node_profile(values: list[int], node: int, matrix_size: int, logical_size: int, assumption: str) -> list[int]:
    if assumption == "node_major_900x30":
        start = node * logical_size
        return values[start : start + logical_size]
    if assumption == "layer_major_30x900":
        return [values[layer * matrix_size + node] for layer in range(logical_size)]
    if assumption == "slices_30x30x30_layer_major":
        return [values[layer * matrix_size + node] for layer in range(logical_size)]
    raise ValueError(f"Unknown packed4_1 reshape assumption: {assumption}")


def packed4_1_component_correlation_payload(
    metadata: dict[str, Any],
    packed1_values: list[int],
    component_by_node: list[int],
    components: list[list[int]],
    edge_records: list[dict[str, Any]],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    expected_count = matrix_size * logical_size
    if len(packed1_values) != expected_count:
        return {
            "probe": "q2k_packed4_1_component_correlation",
            **metadata,
            "packed4_1_value_count": len(packed1_values),
            "expected_count_for_900x30_assumptions": expected_count,
            "status": "unsupported_shape_for_component_correlation",
            "runtime_mutation_allowed": False,
            "packed4_mutation_allowed": False,
        }

    endpoint_nodes = sorted({record["source"] for record in edge_records} | {record["target"] for record in edge_records})
    top_components = sorted(enumerate(components), key=lambda item: (len(item[1]), -item[0]), reverse=True)[:20]
    assumptions = ("node_major_900x30", "layer_major_30x900", "slices_30x30x30_layer_major")
    assumption_payload: dict[str, Any] = {}
    for assumption in assumptions:
        profiles = [tuple(node_profile(packed1_values, node, matrix_size, logical_size, assumption)) for node in range(matrix_size)]
        unique_profile_count = len(set(profiles))
        component_purity_weighted_total = 0
        single_profile_component_count = 0
        non_singleton_purity_weighted_total = 0
        non_singleton_node_count = 0
        non_singleton_component_count = 0
        non_singleton_single_profile_component_count = 0
        top_component_histograms: list[dict[str, Any]] = []
        for component_id, nodes in enumerate(components):
            profile_counts = Counter(profiles[node] for node in nodes)
            dominant_profile, dominant_count = profile_counts.most_common(1)[0]
            component_purity_weighted_total += dominant_count
            if len(profile_counts) == 1:
                single_profile_component_count += 1
            if len(nodes) > 1:
                non_singleton_component_count += 1
                non_singleton_node_count += len(nodes)
                non_singleton_purity_weighted_total += dominant_count
                if len(profile_counts) == 1:
                    non_singleton_single_profile_component_count += 1
            if any(component_id == top_id for top_id, _nodes in top_components):
                component_values: list[int] = []
                for node in nodes:
                    component_values.extend(profiles[node])
                top_component_histograms.append(
                    {
                        "component_id": component_id,
                        "component_size": len(nodes),
                        "unique_profile_count": len(profile_counts),
                        "dominant_profile": list(dominant_profile),
                        "dominant_profile_ratio": dominant_count / len(nodes) if nodes else None,
                        "value_histogram": value_histogram(component_values),
                    }
                )

        non_singleton_purity = (
            non_singleton_purity_weighted_total / non_singleton_node_count if non_singleton_node_count else None
        )
        component_id_like_pattern = "not_detected"
        if (
            non_singleton_component_count
            and non_singleton_single_profile_component_count / non_singleton_component_count >= 0.80
            and non_singleton_purity is not None
            and non_singleton_purity >= 0.95
        ):
            component_id_like_pattern = "weak_candidate_unverified"
        endpoint_values: list[int] = []
        for node in endpoint_nodes:
            endpoint_values.extend(profiles[node])
        node837_profile = list(profiles[837]) if 837 < len(profiles) else None
        assumption_payload[assumption] = {
            "unique_node_profile_count": unique_profile_count,
            "single_profile_component_count": single_profile_component_count,
            "component_profile_purity_weighted": component_purity_weighted_total / matrix_size
            if matrix_size
            else None,
            "non_singleton_component_count": non_singleton_component_count,
            "non_singleton_single_profile_component_count": non_singleton_single_profile_component_count,
            "non_singleton_component_profile_purity_weighted": non_singleton_purity,
            "component_id_like_pattern": component_id_like_pattern,
            "code15_endpoint_value_histogram": value_histogram(endpoint_values),
            "node_837_profile": node837_profile,
            "node_837_value_histogram": value_histogram(node837_profile or []),
            "top_component_histograms": top_component_histograms,
        }

    return {
        "probe": "q2k_packed4_1_component_correlation",
        **metadata,
        "packed4_1_value_count": len(packed1_values),
        "overall_value_histogram": value_histogram(packed1_values),
        "reshape_assumptions": {
            "node_major_900x30": "node profile is packed4_1[node * 30 : node * 30 + 30]",
            "layer_major_30x900": "node profile is packed4_1[layer * 900 + node] for 30 layers",
            "slices_30x30x30_layer_major": "same indexing as layer_major, viewed as 30 table-coordinate 30x30 slices",
        },
        "assumptions": assumption_payload,
        "interpretation_boundary": "packed4_1 correlation is static only and does not approve packed4_1 mutation.",
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
    }


def interpretation_payload(
    metadata: dict[str, Any],
    component_summary: dict[str, Any],
    cross_edges: dict[str, Any],
    packed4_1: dict[str, Any],
) -> dict[str, Any]:
    cross_ratio = cross_edges["cross_component_ratio"]
    component_count = component_summary["component_count"]
    if cross_ratio is not None and cross_ratio >= 0.95 and component_count > 1:
        role = "cross_component_bridge_candidate"
    else:
        role = "ambiguous"

    return {
        "probe": "q2k_code15_component_interpretation",
        **metadata,
        "code15_component_role": role,
        "evidence": {
            "component_count": component_count,
            "largest_component_size": component_summary["largest_components"][0]["size"]
            if component_summary["largest_components"]
            else None,
            "code15_connected_nonself_edge_count": cross_edges["code15_connected_nonself_edge_count"],
            "same_component_count": cross_edges["same_component_count"],
            "cross_component_count": cross_edges["cross_component_count"],
            "cross_component_ratio": cross_ratio,
            "node_837_component_id": cross_edges["node_837"]["component_id"] if cross_edges["node_837"] else None,
            "packed4_1_component_id_like_findings": {
                key: value.get("component_id_like_pattern")
                for key, value in packed4_1.get("assumptions", {}).items()
            },
        },
        "interpretation_boundary": {
            "code15_component_role": "static graph role only; not runtime semantics",
            "map_setting_node_world_transform": "unproven",
            "semantic_safety": "not proven",
            "packed4_1": "read-only correlation only; not decoded as editable",
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


def analyze_code15_component_graph(
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    ensure_paths_are_safe(input_path, output_dir)

    data, _document, chunked_values, packed0_values, packed1_values, matrix_size = load_layers(
        input_path,
        expected_sha256,
    )
    metadata = base_metadata(input_path, output_dir, data)
    component_by_node, components, graph_counts = build_no15_weak_components(
        chunked_values,
        packed0_values,
        matrix_size,
    )
    edge_records = code15_edge_records(chunked_values, packed0_values, matrix_size, component_by_node)

    component_summary = no15_component_summary_payload(
        metadata,
        chunked_values,
        packed0_values,
        matrix_size,
        component_by_node,
        components,
        graph_counts,
    )
    cross_edges = code15_cross_component_payload(
        metadata,
        edge_records,
        chunked_values,
        matrix_size,
        component_by_node,
        components,
    )
    pair_matrix = component_pair_matrix_payload(metadata, edge_records, components)
    prior_context = prior_probe_component_payload(
        metadata,
        chunked_values,
        packed0_values,
        matrix_size,
        component_by_node,
        components,
    )
    packed4_1 = packed4_1_component_correlation_payload(
        metadata,
        packed1_values,
        component_by_node,
        components,
        edge_records,
        matrix_size,
    )
    interpretation = interpretation_payload(metadata, component_summary, cross_edges, packed4_1)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "no15_component_summary": output_dir / "no15_component_summary.json",
        "code15_cross_component_edges": output_dir / "code15_cross_component_edges.json",
        "code15_component_pair_matrix": output_dir / "code15_component_pair_matrix.json",
        "prior_probe_component_context": output_dir / "prior_probe_component_context.json",
        "packed4_1_component_correlation": output_dir / "packed4_1_component_correlation.json",
        "q2k_code15_component_interpretation": output_dir / "q2k_code15_component_interpretation.json",
    }
    payloads = {
        "no15_component_summary": component_summary,
        "code15_cross_component_edges": cross_edges,
        "code15_component_pair_matrix": pair_matrix,
        "prior_probe_component_context": prior_context,
        "packed4_1_component_correlation": packed4_1,
        "q2k_code15_component_interpretation": interpretation,
    }
    for key, path in outputs.items():
        path.write_text(json.dumps(payloads[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    return {
        "probe": "q2k_code15_component_graph",
        **metadata,
        "outputs": {
            key: {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": rt.sha256_file(path),
            }
            for key, path in outputs.items()
        },
        "code15_component_role": interpretation["code15_component_role"],
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
        "code15_component_role": manifest["code15_component_role"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": manifest["third_chunked_binary_runtime_probe_allowed"],
        "map_editing_allowed": manifest["map_editing_allowed"],
        "outputs": manifest["outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze code15/no15 component graph without mutation.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = analyze_code15_component_graph(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
