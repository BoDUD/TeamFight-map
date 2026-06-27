from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


REFERENCE_Q2E_EDGE = (369, 370)
DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2f_semantic_probe_plan")
OUTPUT_FILES = (
    "q2f_semantic_probe_candidates.json",
    "q2f_candidate_decision.json",
)


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def planned_output_paths(output_dir: Path) -> list[Path]:
    return [output_dir / name for name in OUTPUT_FILES]


def ensure_output_paths_are_safe(input_path: Path, output_dir: Path) -> None:
    inspect.ensure_outside_repo(input_path, "input")
    inspect.ensure_outside_repo(output_dir, "output directory")
    if is_under_mods_tree(output_dir):
        raise SystemExit("Refusing to write Q2f candidate output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(input_path, output_dir, "input")
    for output_path in planned_output_paths(output_dir):
        if output_path == input_path or inspect.paths_are_same_existing_file(output_path, input_path):
            raise SystemExit(f"Refusing to overwrite input through generated output path: {output_path}")
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")


def matrix_hamming_distance(values: list[int], left: int, right: int, size: int) -> int:
    left_row = values[left * size : (left + 1) * size]
    right_row = values[right * size : (right + 1) * size]
    return sum(1 for a, b in zip(left_row, right_row) if a != b)


def matrix_column_hamming_distance(values: list[int], left: int, right: int, size: int) -> int:
    return sum(1 for source in range(size) if values[source * size + left] != values[source * size + right])


def row_sum(values: list[int], row: int, size: int) -> int:
    return sum(values[row * size : (row + 1) * size])


def packed_contrast_class(forward: int, reverse: int) -> str:
    forward_sentinel = forward == 15
    reverse_sentinel = reverse == 15
    if forward_sentinel and reverse_sentinel:
        return "both_packed4_15"
    if forward_sentinel != reverse_sentinel:
        return "mixed_packed4_15_and_non15"
    return "both_packed4_non15"


def packed_contrast_weight(contrast: str) -> int:
    return {
        "mixed_packed4_15_and_non15": 1200,
        "both_packed4_non15": 800,
        "both_packed4_15": 250,
    }[contrast]


def node_xy(node: int, logical_size: int) -> list[int]:
    return [node % logical_size, node // logical_size]


def candidate_record(
    *,
    candidate_id: str,
    source: int,
    target: int,
    chunked_values: list[int],
    packed0_values: list[int],
    chunked_layer: rt.ChunkedBinaryLayer,
    matrix_size: int,
    logical_size: int,
    row_sums: list[int] | None = None,
    reference: bool = False,
) -> dict[str, Any]:
    forward_index = source * matrix_size + target
    reverse_index = target * matrix_size + source
    packed_forward = packed0_values[forward_index]
    packed_reverse = packed0_values[reverse_index]
    contrast = packed_contrast_class(packed_forward, packed_reverse)
    source_row_sum = row_sums[source] if row_sums else row_sum(chunked_values, source, matrix_size)
    target_row_sum = row_sums[target] if row_sums else row_sum(chunked_values, target, matrix_size)
    row_hamming = matrix_hamming_distance(chunked_values, source, target, matrix_size)
    column_hamming = matrix_column_hamming_distance(chunked_values, source, target, matrix_size)
    score = (
        packed_contrast_weight(contrast)
        + row_hamming
        + column_hamming
        + abs(source_row_sum - target_row_sum)
        + abs(packed_forward - packed_reverse)
    )
    cells = [
        {
            "logical_coordinate": [target, source],
            "source_node": source,
            "target_node": target,
            "source_xy_30x30": node_xy(source, logical_size),
            "target_xy_30x30": node_xy(target, logical_size),
            "serialized_byte_offset": inspect.chunked_cell_offset(chunked_layer, target, source),
            "old": 1,
            "new": 0,
            "packed4_0_context_value": packed_forward,
        },
        {
            "logical_coordinate": [source, target],
            "source_node": target,
            "target_node": source,
            "source_xy_30x30": node_xy(target, logical_size),
            "target_xy_30x30": node_xy(source, logical_size),
            "serialized_byte_offset": inspect.chunked_cell_offset(chunked_layer, source, target),
            "old": 1,
            "new": 0,
            "packed4_0_context_value": packed_reverse,
        },
    ]
    return {
        "candidate": candidate_id,
        "reference_q2e_candidate": reference,
        "layer": "chunked_binary",
        "candidate_unit": "undirected_source_target_pair",
        "edge": [source, target],
        "source_xy_30x30": node_xy(source, logical_size),
        "target_xy_30x30": node_xy(target, logical_size),
        "cells": cells,
        "changed_cell_count": 2,
        "changed_byte_count": 2,
        "old_values": [1, 1],
        "planned_new_values": [0, 0],
        "packed4_0_forward": packed_forward,
        "packed4_0_reverse": packed_reverse,
        "packed4_0_contrast": contrast,
        "row_sum_source": source_row_sum,
        "row_sum_target": target_row_sum,
        "row_sum_delta": abs(source_row_sum - target_row_sum),
        "row_signature_hamming_distance": row_hamming,
        "column_signature_hamming_distance": column_hamming,
        "semantic_signal_score": score,
        "selection_reason": (
            "Read-only Q2f candidate scoring favors symmetric chunked_binary pairs with stronger packed4_0 "
            "15/non15 contrast and larger row/column signature differences than the Q2e loader probe."
        ),
        "risk_label": "risk-accepted candidate, not proven safe",
        "map_setting_node_world_transform": "unproven",
        "may_enter_runtime_probe": False,
        "requires_separate_risk_review": True,
        "mutation_generated": False,
    }


def select_symmetric_pair_candidates(
    chunked_values: list[int],
    packed0_values: list[int],
    chunked_layer: rt.ChunkedBinaryLayer,
    matrix_size: int,
    top_n: int,
) -> dict[str, Any]:
    logical_size = math.isqrt(matrix_size)
    if logical_size * logical_size != matrix_size:
        raise SystemExit(f"Expected source-target matrix size to be square logical grid, got {matrix_size}.")
    transpose_before = inspect.matrix_transpose_mismatch_count(chunked_values, matrix_size)
    row_sums = [row_sum(chunked_values, row, matrix_size) for row in range(matrix_size)]
    lightweight_candidates: list[dict[str, Any]] = []
    q2e_reference: dict[str, Any] | None = None
    for source in range(matrix_size):
        for target in range(source + 1, matrix_size):
            if source == target:
                continue
            forward_index = source * matrix_size + target
            reverse_index = target * matrix_size + source
            if chunked_values[forward_index] != 1 or chunked_values[reverse_index] != 1:
                continue
            if (source, target) == REFERENCE_Q2E_EDGE:
                q2e_reference = candidate_record(
                    candidate_id="q2e_reference_369_370",
                    source=source,
                    target=target,
                    chunked_values=chunked_values,
                    packed0_values=packed0_values,
                    chunked_layer=chunked_layer,
                    matrix_size=matrix_size,
                    logical_size=logical_size,
                    row_sums=row_sums,
                    reference=True,
                )
            else:
                packed_forward = packed0_values[forward_index]
                packed_reverse = packed0_values[reverse_index]
                contrast = packed_contrast_class(packed_forward, packed_reverse)
                lightweight_candidates.append(
                    {
                        "source": source,
                        "target": target,
                        "score": (
                            packed_contrast_weight(contrast)
                            + abs(row_sums[source] - row_sums[target])
                            + abs(packed_forward - packed_reverse)
                        ),
                        "contrast": contrast,
                    }
                )

    lightweight_candidates.sort(
        key=lambda item: (
            -item["score"],
            item["contrast"],
            item["source"],
            item["target"],
        )
    )
    shortlist_size = max(top_n * 50, top_n)
    candidates = [
        candidate_record(
            candidate_id="q2f_candidate_pending",
            source=item["source"],
            target=item["target"],
            chunked_values=chunked_values,
            packed0_values=packed0_values,
            chunked_layer=chunked_layer,
            matrix_size=matrix_size,
            logical_size=logical_size,
            row_sums=row_sums,
        )
        for item in lightweight_candidates[:shortlist_size]
    ]
    candidates.sort(
        key=lambda item: (
            -item["semantic_signal_score"],
            item["packed4_0_contrast"],
            item["edge"][0],
            item["edge"][1],
        )
    )
    selected = candidates[:top_n]
    for index, candidate in enumerate(selected, start=1):
        candidate["candidate"] = f"q2f_candidate_{index:02d}"

    return {
        "transpose_mismatch_count_before": transpose_before,
        "candidate_count_considered": len(lightweight_candidates) + (1 if q2e_reference else 0),
        "shortlist_count_scored_with_row_column_hamming": len(candidates),
        "candidate_rules": {
            "layer": "chunked_binary",
            "require_transpose_symmetric_pair": True,
            "require_old_values": [1, 1],
            "planned_new_values": [0, 0],
            "disallow_diagonal_self_edge": True,
            "disallow_packed4_changes": True,
            "disallow_runtime_install": True,
            "disallow_mutated_binary_generation": True,
        },
        "scoring": {
            "primary": "packed4_0 15/non15 contrast",
            "secondary": "row and column signature hamming distance",
            "tertiary": "row-sum delta and packed4 directional code delta",
            "interpretation": "higher score means better semantic contrast, not lower gameplay risk",
        },
        "q2e_reference_candidate": q2e_reference,
        "candidates": selected,
    }


def build_q2f_candidate_plan(
    input_path: Path,
    output_dir: Path,
    top_n: int = 8,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    ensure_output_paths_are_safe(input_path, output_dir)

    data = input_path.read_bytes()
    input_sha256 = rt.sha256_bytes(data)
    if expected_sha256 and input_sha256.lower() != expected_sha256.lower():
        raise SystemExit(f"Input SHA-256 {input_sha256} does not match expected {expected_sha256}.")
    document = rt.decode_map_setting(data)
    if len(document.packed4_layers) < 1:
        raise SystemExit("Expected packed4_0 layer for Q2f candidate selection.")

    chunked_values, width, height = inspect.flatten_chunked_binary_layer(document.chunked_binary_layer)
    if width != height:
        raise SystemExit(f"Expected square chunked relation matrix, got {width}x{height}.")
    packed0_values = inspect.unpack_packed4_layer(document.packed4_layers[0])
    if len(packed0_values) != width * height:
        raise SystemExit("packed4_0 cell count does not match chunked_binary source-target matrix.")

    selection = select_symmetric_pair_candidates(
        chunked_values=chunked_values,
        packed0_values=packed0_values,
        chunked_layer=document.chunked_binary_layer,
        matrix_size=width,
        top_n=top_n,
    )
    decision = {
        "q2f_recommended_next_runtime_option": "A_repeat_q2e_369_370_extended_observation",
        "reason": (
            "Q2e only proved loader tolerance. The next runtime PR should first repeat the same two-byte "
            "mutation with longer observation before approving any second edge."
        ),
        "allowed_next_runtime_scope": {
            "mode": "A/B/A",
            "mutation": "same_q2e_offsets_427536_427573_only",
            "minimum_b_observation": "3:00 or first jungle/objective interaction",
            "result_name": "Q2f Extended Observation Probe",
            "semantic_pass_allowed": False,
        },
        "second_candidate_status": "cataloged_not_selected",
        "second_candidate_may_enter_runtime_probe": False,
        "blocked_actions": [
            "new mutated map_setting binary in PR #12",
            "runtime staging in PR #12",
            "packed4_0 or packed4_1 mutation",
            "region or multi-edge mutation",
            "visual resource synchronization",
            "semantic pass claim",
        ],
    }
    manifest = {
        "probe": "q2f_semantic_probe_candidate_selection",
        "input_path": str(input_path),
        "input_sha256": input_sha256,
        "input_size": len(data),
        "output_dir": str(output_dir),
        "layer": "chunked_binary",
        "matrix_shape": [width, height],
        "semantic_hypotheses_under_review": [
            "visibility_pair_relation",
            "reachability_pair_relation",
            "ai_or_path_query_cache",
        ],
        "selection": selection,
        "decision": decision,
        "safety": {
            "read_only": True,
            "mutated_map_setting_generated": False,
            "runtime_install_modified": False,
            "map_setting_override_installed": False,
            "visual_assets_changed": False,
            "outputs_inside_repository": rt.is_inside_repo(output_dir),
            "outputs_under_mods_tree": is_under_mods_tree(output_dir),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = output_dir / "q2f_semantic_probe_candidates.json"
    decision_path = output_dir / "q2f_candidate_decision.json"
    candidates_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    decision_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    manifest["outputs"] = {
        "candidates": str(candidates_path),
        "decision": str(decision_path),
        "candidates_sha256": "self-referential; compute from the final file on disk",
        "decision_sha256": rt.sha256_file(decision_path),
    }
    candidates_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    candidates = manifest["selection"]["candidates"]
    return {
        "probe": manifest["probe"],
        "input_sha256": manifest["input_sha256"],
        "output_dir": manifest["output_dir"],
        "recommended_next_runtime_option": manifest["decision"]["q2f_recommended_next_runtime_option"],
        "candidate_count_considered": manifest["selection"]["candidate_count_considered"],
        "top_candidate": candidates[0] if candidates else None,
        "second_candidate_may_enter_runtime_probe": manifest["decision"]["second_candidate_may_enter_runtime_probe"],
        "read_only": manifest["safety"]["read_only"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Select read-only Q2f semantic probe candidates.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--top-n", type=int, default=8)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = build_q2f_candidate_plan(
        input_path=args.input,
        output_dir=args.output_dir,
        top_n=args.top_n,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
