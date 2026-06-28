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


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2j_packed4_code15_context_analysis")
OUTPUT_FILES = (
    "packed4_code15_contexts.json",
    "packed4_code15_distance_buckets.json",
    "packed4_code15_endpoint_classes.json",
    "packed4_code15_path_recovery.json",
    "q2j_code15_interpretation.json",
)
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
        raise SystemExit("Refusing to write Q2j analysis output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(input_path, output_dir, "input")
    for output_path in planned_output_paths(output_dir):
        if output_path == input_path or inspect.paths_are_same_existing_file(output_path, input_path):
            raise SystemExit(f"Refusing to overwrite input through generated output path: {output_path}")
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")


def counter_payload(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def distance_bucket(distance: int) -> str:
    if distance == 0:
        return "0"
    if distance == 1:
        return "1"
    if 2 <= distance <= 3:
        return "2-3"
    if 4 <= distance <= 8:
        return "4-8"
    return "9+"


def load_layers(
    input_path: Path,
    expected_sha256: str | None,
) -> tuple[bytes, rt.MapSettingDocument, list[int], list[int], int]:
    data = input_path.read_bytes()
    input_sha256 = rt.sha256_bytes(data)
    if expected_sha256 and input_sha256.lower() != expected_sha256.lower():
        raise SystemExit(f"Input SHA-256 {input_sha256} does not match expected {expected_sha256}.")
    document = rt.decode_map_setting(data)
    if not document.packed4_layers:
        raise SystemExit("Expected packed4_0 layer for Q2j code15 analysis.")
    chunked_values, width, height = inspect.flatten_chunked_binary_layer(document.chunked_binary_layer)
    if width != height:
        raise SystemExit(f"Expected square chunked relation matrix, got {width}x{height}.")
    packed0_values = inspect.unpack_packed4_layer(document.packed4_layers[0])
    if len(packed0_values) != width * height:
        raise SystemExit("packed4_0 cell count does not match chunked_binary matrix.")
    return data, document, chunked_values, packed0_values, width


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


def code15_context_payload(
    metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
) -> dict[str, Any]:
    counts = Counter()
    by_packed = {"15": Counter(), "non15": Counter()}
    for chunked, code in zip(chunked_values, packed0_values):
        code_group = "15" if code == 15 else "non15"
        counts[f"packed4_{code_group}_chunked_{chunked}"] += 1
        by_packed[code_group][chunked] += 1

    code15_total = by_packed["15"][0] + by_packed["15"][1]
    non15_total = by_packed["non15"][0] + by_packed["non15"][1]
    chunked_zero_total = by_packed["15"][0] + by_packed["non15"][0]
    chunked_one_total = by_packed["15"][1] + by_packed["non15"][1]
    total = code15_total + non15_total
    return {
        "probe": "q2j_packed4_code15_contexts",
        **metadata,
        "matrix_shape": [matrix_size, matrix_size],
        "context_counts": {
            "packed4_0_eq_15_and_chunked_binary_eq_0": by_packed["15"][0],
            "packed4_0_eq_15_and_chunked_binary_eq_1": by_packed["15"][1],
            "packed4_0_ne_15_and_chunked_binary_eq_0": by_packed["non15"][0],
            "packed4_0_ne_15_and_chunked_binary_eq_1": by_packed["non15"][1],
        },
        "totals": {
            "packed4_0_eq_15": code15_total,
            "packed4_0_ne_15": non15_total,
            "chunked_binary_eq_0": chunked_zero_total,
            "chunked_binary_eq_1": chunked_one_total,
            "all_cells": total,
        },
        "probabilities": {
            "p_chunked_binary_0_given_packed4_0_15": by_packed["15"][0] / code15_total
            if code15_total
            else None,
            "p_chunked_binary_1_given_packed4_0_15": by_packed["15"][1] / code15_total
            if code15_total
            else None,
            "p_packed4_0_15_given_chunked_binary_0": by_packed["15"][0] / chunked_zero_total
            if chunked_zero_total
            else None,
            "p_packed4_0_15_given_chunked_binary_1": by_packed["15"][1] / chunked_one_total
            if chunked_one_total
            else None,
            "p_packed4_0_15_overall": code15_total / total if total else None,
        },
        "interpretation_boundary": (
            "This contingency is static evidence only. It does not approve packed4 mutation, "
            "chunked_binary runtime probing, or map edits."
        ),
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
    }


def code15_distance_payload(
    metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    by_bucket: dict[str, Counter[str]] = defaultdict(Counter)
    connected_code15_samples: list[dict[str, Any]] = []
    connected_code15_bucket_count = Counter()
    for source in range(matrix_size):
        for target in range(matrix_size):
            index = source * matrix_size + target
            bucket = distance_bucket(q2i.chebyshev_distance(source, target, logical_size))
            is_code15 = packed0_values[index] == 15
            is_connected = chunked_values[index] == 1
            label = f"{'code15' if is_code15 else 'non15'}_chunked_{chunked_values[index]}"
            by_bucket[bucket][label] += 1
            if is_code15 and is_connected:
                connected_code15_bucket_count[bucket] += 1
                if len(connected_code15_samples) < 40:
                    connected_code15_samples.append(
                        {
                            "source": source,
                            "target": target,
                            "source_xy": q2i.node_xy(source, logical_size),
                            "target_xy": q2i.node_xy(target, logical_size),
                            "distance": q2i.chebyshev_distance(source, target, logical_size),
                            "bucket": bucket,
                            "self_pair": source == target,
                        }
                    )

    return {
        "probe": "q2j_packed4_code15_distance_buckets",
        **metadata,
        "distance_metric": "Chebyshev distance on the unproven 30x30 table coordinate grid",
        "buckets": {
            bucket: {
                "packed4_0_eq_15_and_chunked_binary_eq_0": counter["code15_chunked_0"],
                "packed4_0_eq_15_and_chunked_binary_eq_1": counter["code15_chunked_1"],
                "packed4_0_ne_15_and_chunked_binary_eq_0": counter["non15_chunked_0"],
                "packed4_0_ne_15_and_chunked_binary_eq_1": counter["non15_chunked_1"],
            }
            for bucket, counter in sorted(by_bucket.items())
        },
        "connected_code15_bucket_counts": counter_payload(connected_code15_bucket_count),
        "connected_code15_sample_records": connected_code15_samples,
        "coordinate_boundary": "Distance buckets are table-coordinate diagnostics, not proven game-world distances.",
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
    }


def node_record(
    node: int,
    rows: list[int],
    columns: list[int],
    matrix_size: int,
    source_appearances: int,
    target_appearances: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    return {
        "node": node,
        "xy_30x30_unproven": q2i.node_xy(node, logical_size),
        "row_sum": rows[node],
        "row_class": q2h.classify_sum(rows[node], matrix_size),
        "column_sum": columns[node],
        "column_class": q2h.classify_sum(columns[node], matrix_size),
        "source_appearances": source_appearances,
        "target_appearances": target_appearances,
        "total_endpoint_appearances": source_appearances + target_appearances,
    }


def top_endpoint_records(
    rows: list[int],
    columns: list[int],
    matrix_size: int,
    source_counts: Counter[int],
    target_counts: Counter[int],
    limit: int = 20,
) -> list[dict[str, Any]]:
    nodes = set(source_counts) | set(target_counts)
    ranked = sorted(
        nodes,
        key=lambda node: (source_counts[node] + target_counts[node], source_counts[node], target_counts[node], -node),
        reverse=True,
    )
    return [
        node_record(node, rows, columns, matrix_size, source_counts[node], target_counts[node])
        for node in ranked[:limit]
    ]


def code15_endpoint_payload(
    metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
) -> dict[str, Any]:
    rows = q2h.row_sums(chunked_values, matrix_size)
    columns = q2h.column_sums(chunked_values, matrix_size)
    source_class_counts = Counter()
    target_class_counts = Counter()
    pair_class_counts = Counter()
    all_source_counts: Counter[int] = Counter()
    all_target_counts: Counter[int] = Counter()
    connected_source_counts: Counter[int] = Counter()
    connected_target_counts: Counter[int] = Counter()

    for source in range(matrix_size):
        source_row_class = q2h.classify_sum(rows[source], matrix_size)
        for target in range(matrix_size):
            index = source * matrix_size + target
            if packed0_values[index] != 15:
                continue
            target_row_class = q2h.classify_sum(rows[target], matrix_size)
            source_class_counts[source_row_class] += 1
            target_class_counts[target_row_class] += 1
            pair_class_counts[f"{source_row_class}->{target_row_class}"] += 1
            all_source_counts[source] += 1
            all_target_counts[target] += 1
            if chunked_values[index] == 1:
                connected_source_counts[source] += 1
                connected_target_counts[target] += 1

    special_nodes = sorted(
        {
            node
            for node in range(matrix_size)
            if rows[node] == matrix_size or columns[node] == matrix_size or node == 837
        }
    )
    special_node_payload = [
        node_record(node, rows, columns, matrix_size, connected_source_counts[node], connected_target_counts[node])
        for node in special_nodes
        if node < matrix_size
    ]
    return {
        "probe": "q2j_packed4_code15_endpoint_classes",
        **metadata,
        "class_definitions": {
            "zero": "sum == 0",
            "sparse": "0 < sum <= 5% of matrix width",
            "middle": "between sparse and near_universal",
            "near_universal": "sum >= 95% of matrix width but not equal to matrix width",
            "universal_like": "sum == matrix width",
        },
        "code15_endpoint_row_class_counts": {
            "source": counter_payload(source_class_counts),
            "target": counter_payload(target_class_counts),
            "source_to_target": counter_payload(pair_class_counts),
        },
        "top_connected_code15_endpoint_nodes": top_endpoint_records(
            rows,
            columns,
            matrix_size,
            connected_source_counts,
            connected_target_counts,
        ),
        "top_all_code15_endpoint_nodes": top_endpoint_records(
            rows,
            columns,
            matrix_size,
            all_source_counts,
            all_target_counts,
        ),
        "universal_like_or_tracked_nodes": special_node_payload,
        "node_837_note": (
            "Node 837 is tracked because Q2h identified it as the only row_sum==900 and "
            "column_sum==900 universal-like node, and Q2g touched edge 59-837."
        ),
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
    }


def direction_local_graph(
    packed0_values: list[int],
    matrix_size: int,
    deltas_by_code: dict[int, tuple[int, int]],
) -> list[list[int]]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    graph: list[list[int]] = [[] for _ in range(matrix_size)]
    for source in range(matrix_size):
        sx = source % logical_size
        sy = source // logical_size
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                target_x = sx + dx
                target_y = sy + dy
                if not (0 <= target_x < logical_size and 0 <= target_y < logical_size):
                    continue
                target = target_y * logical_size + target_x
                code = packed0_values[source * matrix_size + target]
                if code in deltas_by_code and deltas_by_code[code] == (dx, dy):
                    graph[source].append(target)
    return graph


def chunked_non15_graph(
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
) -> list[list[int]]:
    graph: list[list[int]] = [[] for _ in range(matrix_size)]
    for source in range(matrix_size):
        base = source * matrix_size
        graph[source] = [
            target
            for target in range(matrix_size)
            if source != target and chunked_values[base + target] == 1 and packed0_values[base + target] != 15
        ]
    return graph


def reachability_cache(graph: list[list[int]]) -> list[set[int]]:
    cache: list[set[int]] = []
    for source in range(len(graph)):
        seen = {source}
        queue: deque[int] = deque([source])
        while queue:
            current = queue.popleft()
            for target in graph[current]:
                if target in seen:
                    continue
                seen.add(target)
                queue.append(target)
        cache.append(seen)
    return cache


def code15_path_recovery_payload(
    metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    direction_payload = q2i.adjacent_direction_distribution(packed0_values, logical_size)
    deltas_by_code = q2i.code_to_delta(direction_payload)
    direction_graph = direction_local_graph(packed0_values, matrix_size, deltas_by_code)
    chunked_graph = chunked_non15_graph(chunked_values, packed0_values, matrix_size)
    direction_reachability = reachability_cache(direction_graph)
    chunked_non15_reachability = reachability_cache(chunked_graph)

    status_counts = Counter()
    sample_records: list[dict[str, Any]] = []
    connected_code15_total = 0
    connected_nonself_code15_total = 0
    for source in range(matrix_size):
        for target in range(matrix_size):
            index = source * matrix_size + target
            if chunked_values[index] != 1 or packed0_values[index] != 15:
                continue
            connected_code15_total += 1
            if source == target:
                status_counts["self_pair"] += 1
                continue
            connected_nonself_code15_total += 1
            direction_reachable = target in direction_reachability[source]
            chunked_reachable = target in chunked_non15_reachability[source]
            if direction_reachable and chunked_reachable:
                status = "both_reachable_without_15"
            elif direction_reachable:
                status = "direction_codes_without_15_only"
            elif chunked_reachable:
                status = "chunked_non15_bfs_only"
            else:
                status = "not_recoverable_without_15"
            status_counts[status] += 1
            if len(sample_records) < 60:
                sample_records.append(
                    {
                        "source": source,
                        "target": target,
                        "source_xy": q2i.node_xy(source, logical_size),
                        "target_xy": q2i.node_xy(target, logical_size),
                        "distance": q2i.chebyshev_distance(source, target, logical_size),
                        "direction_codes_without_15_reachable": direction_reachable,
                        "chunked_non15_bfs_reachable": chunked_reachable,
                        "recovery_status": status,
                    }
                )

    direction_recovered = (
        status_counts["both_reachable_without_15"] + status_counts["direction_codes_without_15_only"]
    )
    chunked_non15_recovered = (
        status_counts["both_reachable_without_15"] + status_counts["chunked_non15_bfs_only"]
    )
    any_recovered = connected_nonself_code15_total - status_counts["not_recoverable_without_15"]
    return {
        "probe": "q2j_packed4_code15_path_recovery",
        **metadata,
        "recovery_policy": {
            "tested_pairs": "chunked_binary == 1, packed4_0 == 15",
            "self_pairs": "counted separately; not treated as path recovery",
            "direction_codes_without_15": (
                "BFS over adjacent table-neighbor edges whose packed4_0 code is 0-7 and matches "
                "the inferred table-coordinate direction."
            ),
            "chunked_non15_bfs": (
                "BFS over chunked_binary == 1 relations after excluding all packed4_0 == 15 edges, "
                "so the direct code15 relation cannot make itself recoverable."
            ),
            "coordinate_boundary": "All graph work uses table coordinates; node/world transform remains unproven.",
        },
        "direction_code_candidates": {
            "code_to_direction": direction_payload["code_to_direction"],
            "purity_by_code": direction_payload["purity_by_code"],
            "unresolved_codes": direction_payload["unresolved_codes"],
        },
        "connected_code15_total": connected_code15_total,
        "connected_nonself_code15_total": connected_nonself_code15_total,
        "status_counts": counter_payload(status_counts),
        "recovery_ratios": {
            "direction_codes_without_15": direction_recovered / connected_nonself_code15_total
            if connected_nonself_code15_total
            else None,
            "chunked_non15_bfs": chunked_non15_recovered / connected_nonself_code15_total
            if connected_nonself_code15_total
            else None,
            "any_without_15": any_recovered / connected_nonself_code15_total
            if connected_nonself_code15_total
            else None,
        },
        "sample_records": sample_records,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
    }


def prior_probe_context(
    probe: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
) -> dict[str, Any]:
    source, target = probe["edge"]
    if source >= matrix_size or target >= matrix_size:
        return {"id": probe["id"], "edge": probe["edge"], "status": "not_applicable_to_matrix_size"}
    forward_index = source * matrix_size + target
    reverse_index = target * matrix_size + source
    logical_size = q2i.logical_size_for_matrix(matrix_size)
    return {
        "id": probe["id"],
        "edge": probe["edge"],
        "runtime_result": probe["runtime_result"],
        "semantic_effect_observed": probe["semantic_effect_observed"],
        "cells": [
            {
                "source_node": source,
                "target_node": target,
                "source_xy_30x30_unproven": q2i.node_xy(source, logical_size),
                "target_xy_30x30_unproven": q2i.node_xy(target, logical_size),
                "chunked_value": chunked_values[forward_index],
                "packed4_0_value": packed0_values[forward_index],
            },
            {
                "source_node": target,
                "target_node": source,
                "source_xy_30x30_unproven": q2i.node_xy(target, logical_size),
                "target_xy_30x30_unproven": q2i.node_xy(source, logical_size),
                "chunked_value": chunked_values[reverse_index],
                "packed4_0_value": packed0_values[reverse_index],
            },
        ],
    }


def interpretation_payload(
    metadata: dict[str, Any],
    contexts: dict[str, Any],
    recovery: dict[str, Any],
    prior_context: list[dict[str, Any]],
) -> dict[str, Any]:
    probabilities = contexts["probabilities"]
    p_chunk0_given_15 = probabilities["p_chunked_binary_0_given_packed4_0_15"]
    p_chunk1_given_15 = probabilities["p_chunked_binary_1_given_packed4_0_15"]
    recovery_ratios = recovery["recovery_ratios"]
    any_recovery = recovery_ratios["any_without_15"]
    connected_nonself_total = recovery["connected_nonself_code15_total"]

    if p_chunk0_given_15 is not None and p_chunk0_given_15 >= 0.95 and connected_nonself_total == 0:
        code15_interpretation = "likely_blocked_sentinel_but_not_clean"
    elif (
        p_chunk1_given_15 is not None
        and p_chunk1_given_15 >= 0.05
        and any_recovery is not None
        and any_recovery >= 0.50
    ):
        code15_interpretation = "likely_special_fallback_or_uncached_relation"
    else:
        code15_interpretation = "ambiguous"

    return {
        "probe": "q2j_code15_interpretation",
        **metadata,
        "code15_interpretation": code15_interpretation,
        "evidence": {
            "p_chunked_binary_0_given_packed4_0_15": p_chunk0_given_15,
            "p_chunked_binary_1_given_packed4_0_15": p_chunk1_given_15,
            "connected_nonself_code15_total": connected_nonself_total,
            "recovery_ratios": recovery_ratios,
            "direction_code15_purity": recovery["direction_code_candidates"]["purity_by_code"].get("15"),
            "direction_code15_unresolved": 15 in recovery["direction_code_candidates"]["unresolved_codes"],
        },
        "prior_probe_context": prior_context,
        "interpretation_boundary": {
            "packed4_0_codes_0_7": "strong table-coordinate direction-code evidence from Q2i",
            "packed4_0_code15": "classified by static context only; not runtime-confirmed",
            "map_setting_node_world_transform": "unproven",
            "semantic_safety": "not proven",
        },
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "third_chunked_binary_runtime_probe_allowed": False,
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


def analyze_packed4_code15_contexts(
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    ensure_paths_are_safe(input_path, output_dir)

    data, _document, chunked_values, packed0_values, matrix_size = load_layers(input_path, expected_sha256)
    metadata = base_metadata(input_path, output_dir, data)
    contexts = code15_context_payload(metadata, chunked_values, packed0_values, matrix_size)
    distances = code15_distance_payload(metadata, chunked_values, packed0_values, matrix_size)
    endpoints = code15_endpoint_payload(metadata, chunked_values, packed0_values, matrix_size)
    recovery = code15_path_recovery_payload(metadata, chunked_values, packed0_values, matrix_size)
    prior_context = [
        prior_probe_context(probe, chunked_values, packed0_values, matrix_size)
        for probe in PRIOR_PROBES
    ]
    interpretation = interpretation_payload(metadata, contexts, recovery, prior_context)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "packed4_code15_contexts": output_dir / "packed4_code15_contexts.json",
        "packed4_code15_distance_buckets": output_dir / "packed4_code15_distance_buckets.json",
        "packed4_code15_endpoint_classes": output_dir / "packed4_code15_endpoint_classes.json",
        "packed4_code15_path_recovery": output_dir / "packed4_code15_path_recovery.json",
        "q2j_code15_interpretation": output_dir / "q2j_code15_interpretation.json",
    }
    payloads = {
        "packed4_code15_contexts": contexts,
        "packed4_code15_distance_buckets": distances,
        "packed4_code15_endpoint_classes": endpoints,
        "packed4_code15_path_recovery": recovery,
        "q2j_code15_interpretation": interpretation,
    }
    for key, path in outputs.items():
        path.write_text(json.dumps(payloads[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    return {
        "probe": "q2j_packed4_code15_context_analysis",
        **metadata,
        "outputs": {
            key: {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": rt.sha256_file(path),
            }
            for key, path in outputs.items()
        },
        "code15_interpretation": interpretation["code15_interpretation"],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "third_chunked_binary_runtime_probe_allowed": False,
        "next_recommended_step": interpretation["next_recommended_step"],
    }


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "input_sha256": manifest["input_sha256"],
        "output_dir": manifest["output_dir"],
        "code15_interpretation": manifest["code15_interpretation"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": manifest["third_chunked_binary_runtime_probe_allowed"],
        "outputs": manifest["outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify packed4_0 code15 contexts without mutation.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = analyze_packed4_code15_contexts(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
