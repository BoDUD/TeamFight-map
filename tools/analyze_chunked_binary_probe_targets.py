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

from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2h_chunked_binary_probe_synthesis")
OUTPUT_FILES = (
    "chunked_binary_row_column_classes.json",
    "prior_probe_target_analysis.json",
    "next_candidate_strategy.json",
)
PRIOR_PROBES = (
    {
        "id": "q2e_q2f_369_370",
        "edge": [369, 370],
        "offsets": [427536, 427573],
        "runtime_result": "loader_pass_extended_observation_pass",
        "semantic_effect_observed": False,
    },
    {
        "id": "q2g_59_837",
        "edge": [59, 837],
        "offsets": [66605, 932331],
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
        raise SystemExit("Refusing to write Q2h analysis output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(input_path, output_dir, "input")
    for output_path in planned_output_paths(output_dir):
        if output_path == input_path or inspect.paths_are_same_existing_file(output_path, input_path):
            raise SystemExit(f"Refusing to overwrite input through generated output path: {output_path}")
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")


def histogram(values: list[int]) -> dict[str, int]:
    counter = Counter(values)
    return {str(key): counter[key] for key in sorted(counter)}


def classify_sum(value: int, matrix_size: int) -> str:
    if value == 0:
        return "zero"
    if value == matrix_size:
        return "universal_like"
    sparse_threshold = max(1, round(matrix_size * 0.05))
    dense_threshold = round(matrix_size * 0.95)
    if value <= sparse_threshold:
        return "sparse"
    if value >= dense_threshold:
        return "near_universal"
    return "middle"


def node_xy(node: int, logical_size: int) -> list[int] | None:
    if logical_size * logical_size <= node:
        return None
    return [node % logical_size, node // logical_size]


def class_counts(sums: list[int], matrix_size: int) -> dict[str, int]:
    counter = Counter(classify_sum(value, matrix_size) for value in sums)
    return {key: counter[key] for key in sorted(counter)}


def sample_nodes(nodes: list[int], limit: int = 40) -> dict[str, Any]:
    return {
        "count": len(nodes),
        "sample": nodes[:limit],
        "truncated": len(nodes) > limit,
    }


def grouped_node_samples(sums: list[int], matrix_size: int) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[int]] = {}
    for node, value in enumerate(sums):
        groups.setdefault(classify_sum(value, matrix_size), []).append(node)
    return {name: sample_nodes(nodes) for name, nodes in sorted(groups.items())}


def row_sums(values: list[int], matrix_size: int) -> list[int]:
    return [sum(values[row * matrix_size : (row + 1) * matrix_size]) for row in range(matrix_size)]


def column_sums(values: list[int], matrix_size: int) -> list[int]:
    return [sum(values[row * matrix_size + column] for row in range(matrix_size)) for column in range(matrix_size)]


def row_hamming(values: list[int], left: int, right: int, matrix_size: int) -> int:
    left_row = values[left * matrix_size : (left + 1) * matrix_size]
    right_row = values[right * matrix_size : (right + 1) * matrix_size]
    return sum(1 for a, b in zip(left_row, right_row) if a != b)


def column_hamming(values: list[int], left: int, right: int, matrix_size: int) -> int:
    return sum(1 for row in range(matrix_size) if values[row * matrix_size + left] != values[row * matrix_size + right])


def packed4_chunked_contingency(chunked_values: list[int], packed_values: list[int]) -> dict[str, Any]:
    table: dict[str, dict[str, int]] = {"0": {}, "1": {}}
    for chunked, packed in zip(chunked_values, packed_values):
        chunked_key = str(chunked)
        packed_key = str(packed)
        table[chunked_key][packed_key] = table[chunked_key].get(packed_key, 0) + 1

    chunked_zero_total = sum(table["0"].values())
    chunked_one_total = sum(table["1"].values())
    packed15_total = table["0"].get("15", 0) + table["1"].get("15", 0)
    total = chunked_zero_total + chunked_one_total
    return {
        "table": table,
        "totals": {
            "chunked_0": chunked_zero_total,
            "chunked_1": chunked_one_total,
            "packed4_15": packed15_total,
            "all": total,
        },
        "probabilities": {
            "p_packed4_15_given_chunked_0": table["0"].get("15", 0) / chunked_zero_total
            if chunked_zero_total
            else None,
            "p_packed4_15_given_chunked_1": table["1"].get("15", 0) / chunked_one_total
            if chunked_one_total
            else None,
            "p_chunked_0_given_packed4_15": table["0"].get("15", 0) / packed15_total
            if packed15_total
            else None,
            "p_packed4_15_overall": packed15_total / total if total else None,
        },
        "interpretation": "Cross-distribution only; no packed4 mutation is approved by this analysis.",
    }


def build_row_column_classes(
    values: list[int],
    matrix_size: int,
    packed0_values: list[int],
) -> dict[str, Any]:
    rows = row_sums(values, matrix_size)
    columns = column_sums(values, matrix_size)
    return {
        "matrix_shape": [matrix_size, matrix_size],
        "value_histogram": histogram(values),
        "row_sum_histogram": histogram(rows),
        "column_sum_histogram": histogram(columns),
        "row_class_counts": class_counts(rows, matrix_size),
        "column_class_counts": class_counts(columns, matrix_size),
        "row_class_node_samples": grouped_node_samples(rows, matrix_size),
        "column_class_node_samples": grouped_node_samples(columns, matrix_size),
        "universal_like_rows": sample_nodes([node for node, value in enumerate(rows) if value == matrix_size]),
        "universal_like_columns": sample_nodes([node for node, value in enumerate(columns) if value == matrix_size]),
        "sparse_rows": sample_nodes([node for node, value in enumerate(rows) if classify_sum(value, matrix_size) == "sparse"]),
        "sparse_columns": sample_nodes(
            [node for node, value in enumerate(columns) if classify_sum(value, matrix_size) == "sparse"]
        ),
        "packed4_0_cross_distribution": packed4_chunked_contingency(values, packed0_values),
        "class_definitions": {
            "zero": "sum == 0",
            "sparse": "0 < sum <= 5% of matrix width",
            "middle": "between sparse and near_universal",
            "near_universal": "sum >= 95% of matrix width but not equal to matrix width",
            "universal_like": "sum == matrix width",
        },
    }


def analyze_prior_probe(
    probe: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    chunked_layer: rt.ChunkedBinaryLayer,
    row_sum_values: list[int],
    column_sum_values: list[int],
    matrix_size: int,
    logical_size: int,
) -> dict[str, Any]:
    source, target = probe["edge"]
    if source >= matrix_size or target >= matrix_size:
        return {
            "id": probe["id"],
            "edge": probe["edge"],
            "status": "not_applicable_to_matrix_size",
            "matrix_size": matrix_size,
        }

    forward_index = source * matrix_size + target
    reverse_index = target * matrix_size + source
    forward_offset = inspect.chunked_cell_offset(chunked_layer, target, source)
    reverse_offset = inspect.chunked_cell_offset(chunked_layer, source, target)
    source_row_class = classify_sum(row_sum_values[source], matrix_size)
    target_row_class = classify_sum(row_sum_values[target], matrix_size)
    source_column_class = classify_sum(column_sum_values[source], matrix_size)
    target_column_class = classify_sum(column_sum_values[target], matrix_size)
    involves_universal_like = "universal_like" in {
        source_row_class,
        target_row_class,
        source_column_class,
        target_column_class,
    }
    involves_sparse = "sparse" in {
        source_row_class,
        target_row_class,
        source_column_class,
        target_column_class,
    }
    low_observability_hypotheses = [
        "Single-edge chunked_binary edits may not be queried during the observed match window.",
        "Node/world transform remains unproven, so the runtime actors may not exercise the edited relation.",
        "packed4_0 and other tables were intentionally left unchanged, so runtime behavior may be dominated by another layer.",
    ]
    if involves_universal_like:
        low_observability_hypotheses.append(
            "The probe touches a universal-like row or column, which may be default, sentinel-like, redundant, or otherwise low signal."
        )
    if involves_sparse:
        low_observability_hypotheses.append(
            "The probe also touches a sparse row or column, so the edited pair may be rare or situational."
        )

    return {
        "id": probe["id"],
        "edge": probe["edge"],
        "runtime_result": probe["runtime_result"],
        "semantic_effect_observed": probe["semantic_effect_observed"],
        "cells": [
            {
                "logical_coordinate": [target, source],
                "source_node": source,
                "target_node": target,
                "serialized_byte_offset": forward_offset,
                "recorded_offset": probe["offsets"][0],
                "offset_matches_record": forward_offset == probe["offsets"][0],
                "chunked_value": chunked_values[forward_index],
                "packed4_0_value": packed0_values[forward_index],
            },
            {
                "logical_coordinate": [source, target],
                "source_node": target,
                "target_node": source,
                "serialized_byte_offset": reverse_offset,
                "recorded_offset": probe["offsets"][1],
                "offset_matches_record": reverse_offset == probe["offsets"][1],
                "chunked_value": chunked_values[reverse_index],
                "packed4_0_value": packed0_values[reverse_index],
            },
        ],
        "source": {
            "node": source,
            "xy_30x30": node_xy(source, logical_size),
            "row_sum": row_sum_values[source],
            "row_class": source_row_class,
            "column_sum": column_sum_values[source],
            "column_class": source_column_class,
        },
        "target": {
            "node": target,
            "xy_30x30": node_xy(target, logical_size),
            "row_sum": row_sum_values[target],
            "row_class": target_row_class,
            "column_sum": column_sum_values[target],
            "column_class": target_column_class,
        },
        "row_signature_hamming_distance": row_hamming(chunked_values, source, target, matrix_size),
        "column_signature_hamming_distance": column_hamming(chunked_values, source, target, matrix_size),
        "involves_universal_like_node": involves_universal_like,
        "involves_sparse_node": involves_sparse,
        "low_observability_hypotheses": low_observability_hypotheses,
    }


def build_prior_probe_analysis(
    chunked_values: list[int],
    packed0_values: list[int],
    chunked_layer: rt.ChunkedBinaryLayer,
    matrix_size: int,
) -> dict[str, Any]:
    logical_size = int(matrix_size**0.5)
    if logical_size * logical_size != matrix_size:
        logical_size = matrix_size
    rows = row_sums(chunked_values, matrix_size)
    columns = column_sums(chunked_values, matrix_size)
    probes = [
        analyze_prior_probe(
            probe,
            chunked_values,
            packed0_values,
            chunked_layer,
            rows,
            columns,
            matrix_size,
            logical_size,
        )
        for probe in PRIOR_PROBES
    ]
    return {
        "probes": probes,
        "shared_result": {
            "loader_accepts_two_byte_chunked_binary_mutations": True,
            "semantic_effect_observed": False,
            "chunked_binary_semantics": "unproven",
            "map_setting_node_world_transform": "unproven",
            "broader_map_edits": "not_approved",
        },
        "synthesis": [
            "Both tested two-byte symmetric edge removals loaded, entered 5v5, and rolled back.",
            "Neither test produced a clear local reversible gameplay effect.",
            "Repeating arbitrary single-edge probes is now expected to have low information gain.",
            "The next useful step should either decode more static structure or select a candidate by class constraints before a new risk gate.",
        ],
    }


def build_next_candidate_strategy(row_column_classes: dict[str, Any], prior_analysis: dict[str, Any]) -> dict[str, Any]:
    q2g = next((probe for probe in prior_analysis["probes"] if probe["id"] == "q2g_59_837"), None)
    q2g_universal = bool(q2g and q2g.get("involves_universal_like_node"))
    reason = (
        "Two runtime probes passed loader and live-observation gates but produced no semantic signal. "
        "Q2g also touches a universal-like row/column, so its high row/column contrast may have been less useful "
        "than expected."
        if q2g_universal
        else "Two runtime probes passed loader and live-observation gates but produced no semantic signal."
    )
    return {
        "next_action": "continue_static_decoding",
        "reason": reason,
        "do_not_run_third_runtime_probe_now": True,
        "third_candidate_requires_separate_risk_review": True,
        "if_a_future_third_candidate_is_reviewed": {
            "constraints": [
                "avoid row_sum_900 or column_sum_900 universal-like nodes unless the hypothesis specifically targets them",
                "avoid previously tested edges 369-370 and 59-837",
                "changed_cell_count remains 2",
                "changed_byte_count remains 2",
                "chunked_binary only",
                "no packed4 mutation",
                "no visual synchronization",
                "requires separate risk acceptance before runtime",
            ],
            "preferred_static_evidence_before_runtime": [
                "stronger packed4_0 decode or next-hop interpretation",
                "node/world transform anchor",
                "candidate class comparison against row and column histograms",
            ],
        },
        "rejected_paths_for_now": [
            "multi-edge mutation",
            "3x3 or region mutation",
            "packed4_0 or packed4_1 mutation",
            "formal LOL-map collision/path/spawn export",
        ],
        "row_column_class_summary": {
            "universal_like_row_count": row_column_classes["universal_like_rows"]["count"],
            "universal_like_column_count": row_column_classes["universal_like_columns"]["count"],
            "sparse_row_count": row_column_classes["sparse_rows"]["count"],
            "sparse_column_count": row_column_classes["sparse_columns"]["count"],
        },
    }


def analyze_chunked_binary_probe_targets(
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    ensure_paths_are_safe(input_path, output_dir)

    data = input_path.read_bytes()
    input_sha256 = rt.sha256_bytes(data)
    if expected_sha256 and input_sha256.lower() != expected_sha256.lower():
        raise SystemExit(f"Input SHA-256 {input_sha256} does not match expected {expected_sha256}.")
    document = rt.decode_map_setting(data)
    if not document.packed4_layers:
        raise SystemExit("Expected packed4_0 layer for Q2h probe-target synthesis.")
    chunked_values, width, height = inspect.flatten_chunked_binary_layer(document.chunked_binary_layer)
    if width != height:
        raise SystemExit(f"Expected square chunked relation matrix, got {width}x{height}.")
    packed0_values = inspect.unpack_packed4_layer(document.packed4_layers[0])
    if len(packed0_values) != width * height:
        raise SystemExit("packed4_0 cell count does not match chunked_binary matrix.")

    row_column_classes = build_row_column_classes(chunked_values, width, packed0_values)
    prior_analysis = build_prior_probe_analysis(chunked_values, packed0_values, document.chunked_binary_layer, width)
    next_strategy = build_next_candidate_strategy(row_column_classes, prior_analysis)

    output_dir.mkdir(parents=True, exist_ok=True)
    row_classes_path = output_dir / "chunked_binary_row_column_classes.json"
    prior_path = output_dir / "prior_probe_target_analysis.json"
    strategy_path = output_dir / "next_candidate_strategy.json"
    shared_metadata = {
        "input_path": str(input_path),
        "input_sha256": input_sha256,
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
    row_payload = {"probe": "q2h_chunked_binary_row_column_classes", **shared_metadata, **row_column_classes}
    prior_payload = {"probe": "q2h_prior_probe_target_analysis", **shared_metadata, **prior_analysis}
    strategy_payload = {"probe": "q2h_next_candidate_strategy", **shared_metadata, **next_strategy}
    row_classes_path.write_text(json.dumps(row_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    prior_path.write_text(json.dumps(prior_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    strategy_path.write_text(json.dumps(strategy_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    return {
        "probe": "q2h_chunked_binary_probe_synthesis",
        **shared_metadata,
        "outputs": {
            "row_column_classes": {
                "path": str(row_classes_path),
                "size": row_classes_path.stat().st_size,
                "sha256": rt.sha256_file(row_classes_path),
            },
            "prior_probe_target_analysis": {
                "path": str(prior_path),
                "size": prior_path.stat().st_size,
                "sha256": rt.sha256_file(prior_path),
            },
            "next_candidate_strategy": {
                "path": str(strategy_path),
                "size": strategy_path.stat().st_size,
                "sha256": rt.sha256_file(strategy_path),
            },
        },
        "prior_probe_summary": prior_analysis["shared_result"],
        "next_action": next_strategy["next_action"],
        "reason": next_strategy["reason"],
        "do_not_run_third_runtime_probe_now": next_strategy["do_not_run_third_runtime_probe_now"],
    }


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "input_sha256": manifest["input_sha256"],
        "output_dir": manifest["output_dir"],
        "next_action": manifest["next_action"],
        "do_not_run_third_runtime_probe_now": manifest["do_not_run_third_runtime_probe_now"],
        "outputs": manifest["outputs"],
        "read_only": manifest["safety"]["read_only"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize chunked_binary probe target classes without mutation.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = analyze_chunked_binary_probe_targets(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
