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

from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2i_packed4_next_hop_static_decode")
OUTPUT_FILES = (
    "packed4_value_histogram.json",
    "packed4_direction_code_candidates.json",
    "packed4_path_follow_samples.json",
    "packed4_code15_analysis.json",
    "q2i_next_hop_interpretation.json",
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
DIRECTION_NAMES = {
    (-1, -1): "NW",
    (0, -1): "N",
    (1, -1): "NE",
    (-1, 0): "W",
    (1, 0): "E",
    (-1, 1): "SW",
    (0, 1): "S",
    (1, 1): "SE",
}
DIRECTION_TO_DELTA = {name: delta for delta, name in DIRECTION_NAMES.items()}


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def planned_output_paths(output_dir: Path) -> list[Path]:
    return [output_dir / name for name in OUTPUT_FILES]


def ensure_paths_are_safe(input_path: Path, output_dir: Path) -> None:
    inspect.ensure_outside_repo(input_path, "input")
    inspect.ensure_outside_repo(output_dir, "output directory")
    if is_under_mods_tree(output_dir):
        raise SystemExit("Refusing to write Q2i analysis output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(input_path, output_dir, "input")
    for output_path in planned_output_paths(output_dir):
        if output_path == input_path or inspect.paths_are_same_existing_file(output_path, input_path):
            raise SystemExit(f"Refusing to overwrite input through generated output path: {output_path}")
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")


def histogram(values: list[int]) -> dict[str, int]:
    counter = Counter(values)
    return {str(key): counter[key] for key in sorted(counter)}


def logical_size_for_matrix(matrix_size: int) -> int:
    logical_size = int(matrix_size**0.5)
    if logical_size * logical_size != matrix_size:
        raise SystemExit(f"Expected source-target matrix size to be a square logical grid, got {matrix_size}.")
    return logical_size


def node_xy(node: int, logical_size: int) -> list[int]:
    return [node % logical_size, node // logical_size]


def unpack_layers(input_path: Path, expected_sha256: str | None) -> tuple[bytes, rt.MapSettingDocument, list[int], list[int], int, int]:
    data = input_path.read_bytes()
    input_sha256 = rt.sha256_bytes(data)
    if expected_sha256 and input_sha256.lower() != expected_sha256.lower():
        raise SystemExit(f"Input SHA-256 {input_sha256} does not match expected {expected_sha256}.")
    document = rt.decode_map_setting(data)
    if not document.packed4_layers:
        raise SystemExit("Expected packed4_0 layer for Q2i static decode.")
    chunked_values, width, height = inspect.flatten_chunked_binary_layer(document.chunked_binary_layer)
    if width != height:
        raise SystemExit(f"Expected square chunked relation matrix, got {width}x{height}.")
    packed0_values = inspect.unpack_packed4_layer(document.packed4_layers[0])
    if len(packed0_values) != width * height:
        raise SystemExit("packed4_0 cell count does not match chunked_binary matrix.")
    return data, document, chunked_values, packed0_values, width, height


def packed4_value_histogram_payload(
    input_metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    matrix_size: int,
) -> dict[str, Any]:
    by_chunked = {
        "0": Counter(),
        "1": Counter(),
    }
    for chunked, code in zip(chunked_values, packed0_values):
        by_chunked[str(chunked)][code] += 1
    return {
        "probe": "q2i_packed4_value_histogram",
        **input_metadata,
        "matrix_shape": [matrix_size, matrix_size],
        "packed4_0_value_histogram": histogram(packed0_values),
        "chunked_binary_value_histogram": histogram(chunked_values),
        "packed4_0_by_chunked_binary": {
            key: {str(code): counter[code] for code in sorted(counter)}
            for key, counter in sorted(by_chunked.items())
        },
        "runtime_mutation_allowed": False,
    }


def adjacent_direction_distribution(packed0_values: list[int], logical_size: int) -> dict[str, Any]:
    matrix_size = logical_size * logical_size
    by_displacement: dict[str, Counter[int]] = defaultdict(Counter)
    by_code: dict[int, Counter[str]] = defaultdict(Counter)
    adjacent_pair_count = 0
    for source_y in range(logical_size):
        for source_x in range(logical_size):
            source = source_y * logical_size + source_x
            for (dx, dy), direction in DIRECTION_NAMES.items():
                target_x = source_x + dx
                target_y = source_y + dy
                if not (0 <= target_x < logical_size and 0 <= target_y < logical_size):
                    continue
                target = target_y * logical_size + target_x
                code = packed0_values[source * matrix_size + target]
                adjacent_pair_count += 1
                by_displacement[f"{dx},{dy}:{direction}"][code] += 1
                by_code[code][direction] += 1

    code_to_direction: dict[str, str] = {}
    purity_by_code: dict[str, float] = {}
    support_by_code: dict[str, int] = {}
    unresolved_codes: list[int] = []
    for code in sorted(by_code):
        total = sum(by_code[code].values())
        direction, count = by_code[code].most_common(1)[0]
        purity = count / total if total else 0.0
        code_to_direction[str(code)] = direction
        purity_by_code[str(code)] = round(purity, 6)
        support_by_code[str(code)] = total
        if purity < 0.70:
            unresolved_codes.append(code)

    candidate_delta_by_code = {
        code_text: list(DIRECTION_TO_DELTA[direction])
        for code_text, direction in code_to_direction.items()
        if int(code_text) != 15 and purity_by_code[code_text] >= 0.70
    }
    return {
        "adjacent_pair_count": adjacent_pair_count,
        "displacement_to_code_distribution": {
            key: {str(code): counter[code] for code in sorted(counter)}
            for key, counter in sorted(by_displacement.items())
        },
        "code_to_direction": code_to_direction,
        "candidate_delta_by_code": candidate_delta_by_code,
        "purity_by_code": purity_by_code,
        "support_by_code": support_by_code,
        "unresolved_codes": unresolved_codes,
        "stability": "stable" if not unresolved_codes else "ambiguous",
        "interpretation": "direction candidates are inferred from adjacent source-target pairs only; not confirmed runtime semantics",
    }


def code_to_delta(direction_payload: dict[str, Any], min_purity: float = 0.70) -> dict[int, tuple[int, int]]:
    result: dict[int, tuple[int, int]] = {}
    for code_text, direction in direction_payload["code_to_direction"].items():
        code = int(code_text)
        if code == 15:
            continue
        if direction_payload["purity_by_code"].get(code_text, 0.0) < min_purity:
            continue
        if direction in DIRECTION_TO_DELTA:
            result[code] = DIRECTION_TO_DELTA[direction]
    return result


def move_node(node: int, delta: tuple[int, int], logical_size: int) -> int | None:
    x = node % logical_size
    y = node // logical_size
    nx = x + delta[0]
    ny = y + delta[1]
    if not (0 <= nx < logical_size and 0 <= ny < logical_size):
        return None
    return ny * logical_size + nx


def follow_path(
    packed0_values: list[int],
    source: int,
    target: int,
    deltas_by_code: dict[int, tuple[int, int]],
    logical_size: int,
    max_steps: int = 96,
) -> dict[str, Any]:
    matrix_size = logical_size * logical_size
    current = source
    visited = {current}
    trace: list[dict[str, Any]] = []
    for step in range(max_steps + 1):
        if current == target:
            return {"status": "reached", "steps": step, "trace": trace[:12]}
        code = packed0_values[current * matrix_size + target]
        trace.append({"step": step, "node": current, "code": code})
        if code not in deltas_by_code:
            return {"status": "unresolved_code", "steps": step, "code": code, "trace": trace[:12]}
        next_node = move_node(current, deltas_by_code[code], logical_size)
        if next_node is None:
            return {"status": "out_of_bounds", "steps": step, "code": code, "trace": trace[:12]}
        if next_node in visited:
            return {
                "status": "loop",
                "steps": step + 1,
                "code": code,
                "node": next_node,
                "trace": trace[:12],
            }
        visited.add(next_node)
        current = next_node
    return {"status": "max_steps_exceeded", "steps": max_steps, "trace": trace[:12]}


def chebyshev_distance(source: int, target: int, logical_size: int) -> int:
    source_x, source_y = node_xy(source, logical_size)
    target_x, target_y = node_xy(target, logical_size)
    return max(abs(source_x - target_x), abs(source_y - target_y))


def path_follow_payload(
    input_metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    direction_payload: dict[str, Any],
    matrix_size: int,
    sample_limit: int,
) -> dict[str, Any]:
    logical_size = logical_size_for_matrix(matrix_size)
    deltas_by_code = code_to_delta(direction_payload)
    status_counts: Counter[str] = Counter()
    code_failure_counts: Counter[int] = Counter()
    sample_records: list[dict[str, Any]] = []
    tested = 0
    connected_non_adjacent_total = 0
    for source in range(matrix_size):
        for target in range(matrix_size):
            if source == target or chunked_values[source * matrix_size + target] != 1:
                continue
            if chebyshev_distance(source, target, logical_size) <= 1:
                continue
            connected_non_adjacent_total += 1
            if tested >= sample_limit:
                continue
            tested += 1
            result = follow_path(packed0_values, source, target, deltas_by_code, logical_size)
            status_counts[result["status"]] += 1
            if result["status"] != "reached" and "code" in result:
                code_failure_counts[result["code"]] += 1
            if len(sample_records) < 40:
                sample_records.append(
                    {
                        "source": source,
                        "target": target,
                        "source_xy": node_xy(source, logical_size),
                        "target_xy": node_xy(target, logical_size),
                        **result,
                    }
                )
    reached = status_counts["reached"]
    reached_ratio = reached / tested if tested else 0.0
    return {
        "probe": "q2i_packed4_path_follow_samples",
        **input_metadata,
        "sample_policy": {
            "only_chunked_binary_1_pairs": True,
            "exclude_self_pairs": True,
            "exclude_adjacent_pairs": True,
            "sample_limit": sample_limit,
            "deterministic_order": "source ascending, target ascending",
        },
        "connected_non_adjacent_pair_count": connected_non_adjacent_total,
        "tested_pair_count": tested,
        "status_counts": {key: status_counts[key] for key in sorted(status_counts)},
        "reached_ratio": round(reached_ratio, 6),
        "failure_code_histogram": {str(code): code_failure_counts[code] for code in sorted(code_failure_counts)},
        "sample_records": sample_records,
        "next_hop_hypothesis": "strong_unverified" if reached_ratio >= 0.95 else "weak_or_unresolved",
        "runtime_mutation_allowed": False,
    }


def code15_payload(
    input_metadata: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    direction_payload: dict[str, Any],
    path_payload: dict[str, Any],
) -> dict[str, Any]:
    table = {"0": Counter(), "1": Counter()}
    for chunked, code in zip(chunked_values, packed0_values):
        table[str(chunked)][code] += 1
    chunk0_total = sum(table["0"].values())
    chunk1_total = sum(table["1"].values())
    code15_total = table["0"][15] + table["1"][15]
    adjacent_code15_support = direction_payload["support_by_code"].get("15", 0)
    adjacent_code15_purity = direction_payload["purity_by_code"].get("15")
    failure_code15 = path_payload["failure_code_histogram"].get("15", 0)
    p_chunk0_given_15 = table["0"][15] / code15_total if code15_total else None
    p_15_given_chunk0 = table["0"][15] / chunk0_total if chunk0_total else None
    p_15_given_chunk1 = table["1"][15] / chunk1_total if chunk1_total else None
    if p_chunk0_given_15 is not None and p_chunk0_given_15 >= 0.95:
        interpretation = "strong_blocked_sentinel_candidate"
    elif adjacent_code15_purity is not None and adjacent_code15_purity < 0.70:
        interpretation = "ambiguous_special_case"
    else:
        interpretation = "ambiguous"
    return {
        "probe": "q2i_packed4_code15_analysis",
        **input_metadata,
        "code15_counts": {
            "with_chunked_binary_0": table["0"][15],
            "with_chunked_binary_1": table["1"][15],
            "total": code15_total,
        },
        "probabilities": {
            "p_chunked_binary_0_given_packed4_0_15": p_chunk0_given_15,
            "p_packed4_0_15_given_chunked_binary_0": p_15_given_chunk0,
            "p_packed4_0_15_given_chunked_binary_1": p_15_given_chunk1,
        },
        "adjacent_direction_signal": {
            "support": adjacent_code15_support,
            "dominant_direction": direction_payload["code_to_direction"].get("15"),
            "purity": adjacent_code15_purity,
            "unresolved": 15 in direction_payload["unresolved_codes"],
        },
        "path_follow_signal": {
            "unresolved_code15_failure_count": failure_code15,
            "all_failure_code_histogram": path_payload["failure_code_histogram"],
        },
        "interpretation": interpretation,
        "runtime_mutation_allowed": False,
    }


def prior_probe_context(
    probe: dict[str, Any],
    chunked_values: list[int],
    packed0_values: list[int],
    document: rt.MapSettingDocument,
    matrix_size: int,
) -> dict[str, Any]:
    source, target = probe["edge"]
    if source >= matrix_size or target >= matrix_size:
        return {"id": probe["id"], "edge": probe["edge"], "status": "not_applicable_to_matrix_size"}
    forward_index = source * matrix_size + target
    reverse_index = target * matrix_size + source
    forward_offset = inspect.chunked_cell_offset(document.chunked_binary_layer, target, source)
    reverse_offset = inspect.chunked_cell_offset(document.chunked_binary_layer, source, target)
    logical_size = logical_size_for_matrix(matrix_size)
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
                "source_xy": node_xy(source, logical_size),
                "target_xy": node_xy(target, logical_size),
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
                "source_xy": node_xy(target, logical_size),
                "target_xy": node_xy(source, logical_size),
                "serialized_byte_offset": reverse_offset,
                "recorded_offset": probe["offsets"][1],
                "offset_matches_record": reverse_offset == probe["offsets"][1],
                "chunked_value": chunked_values[reverse_index],
                "packed4_0_value": packed0_values[reverse_index],
            },
        ],
    }


def interpretation_payload(
    input_metadata: dict[str, Any],
    direction_payload: dict[str, Any],
    path_payload: dict[str, Any],
    code15: dict[str, Any],
    prior_context: list[dict[str, Any]],
) -> dict[str, Any]:
    reached_ratio = path_payload["reached_ratio"]
    stable_non15_codes = [
        code
        for code, purity in direction_payload["purity_by_code"].items()
        if code != "15" and purity >= 0.70
    ]
    non15_code_count = len([code for code in direction_payload["code_to_direction"] if code != "15"])
    stable_ratio = len(stable_non15_codes) / non15_code_count if non15_code_count else 0.0
    if reached_ratio >= 0.95 and stable_ratio >= 0.80:
        interpretation = "strong_next_hop_candidate"
    elif reached_ratio < 0.20 and stable_ratio < 0.50:
        interpretation = "unlikely_next_hop"
    else:
        interpretation = "ambiguous"
    return {
        "probe": "q2i_next_hop_interpretation",
        **input_metadata,
        "packed4_0_interpretation": interpretation,
        "evidence": {
            "stable_non15_code_ratio": round(stable_ratio, 6),
            "stable_non15_codes": stable_non15_codes,
            "path_follow_reached_ratio": reached_ratio,
            "path_follow_status_counts": path_payload["status_counts"],
            "code15_interpretation": code15["interpretation"],
        },
        "prior_probe_packed4_context": prior_context,
        "runtime_mutation_allowed": False,
        "third_chunked_binary_runtime_probe_allowed": False,
        "packed4_mutation_allowed": False,
        "next_recommended_step": (
            "continue_static_decoding"
            if interpretation != "strong_next_hop_candidate"
            else "separate_review_gate_before_any_runtime_or_packed4_probe"
        ),
        "blocked_actions": [
            "third chunked_binary edge runtime probe in this PR",
            "packed4_0 mutation",
            "packed4_1 mutation",
            "multi-edge or region mutation",
            "collision/path/spawn export",
            "visual synchronization",
        ],
    }


def analyze_packed4_next_hop_semantics(
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
    sample_limit: int = 50000,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    ensure_paths_are_safe(input_path, output_dir)

    data, document, chunked_values, packed0_values, width, _height = unpack_layers(input_path, expected_sha256)
    input_metadata = {
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
    logical_size = logical_size_for_matrix(width)
    value_payload = packed4_value_histogram_payload(input_metadata, chunked_values, packed0_values, width)
    direction_payload = {
        "probe": "q2i_packed4_direction_code_candidates",
        **input_metadata,
        **adjacent_direction_distribution(packed0_values, logical_size),
        "runtime_mutation_allowed": False,
    }
    path_payload = path_follow_payload(
        input_metadata=input_metadata,
        chunked_values=chunked_values,
        packed0_values=packed0_values,
        direction_payload=direction_payload,
        matrix_size=width,
        sample_limit=sample_limit,
    )
    code15 = code15_payload(input_metadata, chunked_values, packed0_values, direction_payload, path_payload)
    prior_context = [
        prior_probe_context(probe, chunked_values, packed0_values, document, width)
        for probe in PRIOR_PROBES
    ]
    interpretation = interpretation_payload(input_metadata, direction_payload, path_payload, code15, prior_context)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "packed4_value_histogram": output_dir / "packed4_value_histogram.json",
        "packed4_direction_code_candidates": output_dir / "packed4_direction_code_candidates.json",
        "packed4_path_follow_samples": output_dir / "packed4_path_follow_samples.json",
        "packed4_code15_analysis": output_dir / "packed4_code15_analysis.json",
        "q2i_next_hop_interpretation": output_dir / "q2i_next_hop_interpretation.json",
    }
    payloads = {
        "packed4_value_histogram": value_payload,
        "packed4_direction_code_candidates": direction_payload,
        "packed4_path_follow_samples": path_payload,
        "packed4_code15_analysis": code15,
        "q2i_next_hop_interpretation": interpretation,
    }
    for key, path in outputs.items():
        path.write_text(json.dumps(payloads[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    return {
        "probe": "q2i_packed4_next_hop_static_decode",
        **input_metadata,
        "outputs": {
            key: {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": rt.sha256_file(path),
            }
            for key, path in outputs.items()
        },
        "packed4_0_interpretation": interpretation["packed4_0_interpretation"],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "next_recommended_step": interpretation["next_recommended_step"],
    }


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "input_sha256": manifest["input_sha256"],
        "output_dir": manifest["output_dir"],
        "packed4_0_interpretation": manifest["packed4_0_interpretation"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "outputs": manifest["outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze packed4_0 next-hop semantics without mutation.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--sample-limit", type=int, default=50000)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()
    if args.sample_limit <= 0:
        raise SystemExit("--sample-limit must be positive.")

    manifest = analyze_packed4_next_hop_semantics(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_sha256=args.expected_sha256 or None,
        sample_limit=args.sample_limit,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
