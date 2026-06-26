from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


@dataclass(frozen=True)
class MutationCell:
    logical_coordinate: tuple[int, int]
    source_node: int
    target_node: int
    offset: int
    old_value: int
    new_value: int


PRODUCTION_CELLS = (
    MutationCell(
        logical_coordinate=(370, 369),
        source_node=369,
        target_node=370,
        offset=427536,
        old_value=1,
        new_value=0,
    ),
    MutationCell(
        logical_coordinate=(369, 370),
        source_node=370,
        target_node=369,
        offset=427573,
        old_value=1,
        new_value=0,
    ),
)


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def ensure_not_runtime_install_output(output_path: Path) -> None:
    if is_under_mods_tree(output_path):
        raise SystemExit(
            "Refusing to write mutated map_setting under a game mods directory; "
            "generate evidence output outside the game install and stage it only in the runtime A/B/A PR."
        )


def ensure_mutation_paths_are_safe(input_path: Path, output_path: Path, manifest_path: Path) -> None:
    ensure_not_runtime_install_output(output_path)
    for label, path in (("input", input_path), ("output", output_path), ("manifest", manifest_path)):
        rt.ensure_path_is_outside_repo(path, label)
    rt.ensure_distinct_round_trip_paths({"input": input_path, "output": output_path, "manifest": manifest_path})


def changed_offsets(before: bytes, after: bytes) -> list[int]:
    return [index for index, (left, right) in enumerate(zip(before, after)) if left != right]


def cell_to_manifest(cell: MutationCell) -> dict[str, Any]:
    return {
        "logical_coordinate": list(cell.logical_coordinate),
        "source_node": cell.source_node,
        "target_node": cell.target_node,
        "offset": cell.offset,
        "old": cell.old_value,
        "new": cell.new_value,
    }


def validate_candidate_cells(
    data: bytes,
    document: rt.MapSettingDocument,
    cells: tuple[MutationCell, ...],
) -> tuple[list[int], int, int, int]:
    chunked_values, width, height = inspect.flatten_chunked_binary_layer(document.chunked_binary_layer)
    if width != height:
        raise SystemExit(f"chunked_binary must be square for symmetric edge mutation, got {width}x{height}.")
    transpose_before = inspect.matrix_transpose_mismatch_count(chunked_values, width)
    if transpose_before != 0:
        raise SystemExit(f"Refusing mutation because transpose_mismatch_before is {transpose_before}, expected 0.")
    for cell in cells:
        x, y = cell.logical_coordinate
        if not (0 <= x < width and 0 <= y < height):
            raise SystemExit(f"Candidate cell {cell.logical_coordinate} is outside chunked_binary {width}x{height}.")
        computed_offset = inspect.chunked_cell_offset(document.chunked_binary_layer, x, y)
        if computed_offset != cell.offset:
            raise SystemExit(
                f"Candidate cell {cell.logical_coordinate} expected offset {cell.offset}, "
                f"but decoded structure reports {computed_offset}."
            )
        if cell.offset >= len(data):
            raise SystemExit(f"Candidate offset {cell.offset} is outside input size {len(data)}.")
        raw_value = data[cell.offset]
        if raw_value != cell.old_value:
            raise SystemExit(f"Offset {cell.offset} has value {raw_value}, expected old value {cell.old_value}.")
        logical_value = chunked_values[y * width + x]
        if logical_value != cell.old_value:
            raise SystemExit(
                f"Logical cell {cell.logical_coordinate} has value {logical_value}, expected {cell.old_value}."
            )
    return chunked_values, width, height, transpose_before


def validate_output(
    mutated: bytes,
    cells: tuple[MutationCell, ...],
    expected_width: int,
) -> int:
    document = rt.decode_map_setting(mutated)
    chunked_values, width, height = inspect.flatten_chunked_binary_layer(document.chunked_binary_layer)
    if width != expected_width or height != expected_width:
        raise SystemExit(f"Output chunked_binary shape changed: {width}x{height}, expected {expected_width}x{expected_width}.")
    for cell in cells:
        x, y = cell.logical_coordinate
        logical_value = chunked_values[y * width + x]
        if logical_value != cell.new_value:
            raise SystemExit(
                f"Output logical cell {cell.logical_coordinate} has value {logical_value}, expected {cell.new_value}."
            )
    return inspect.matrix_transpose_mismatch_count(chunked_values, width)


def build_manifest(
    input_path: Path,
    output_path: Path,
    manifest_path: Path,
    data: bytes,
    mutated: bytes,
    cells: tuple[MutationCell, ...],
    transpose_before: int,
    transpose_after: int,
) -> dict[str, Any]:
    diff_offsets = changed_offsets(data, mutated)
    return {
        "probe": "risk_accepted_minimal_symmetric_edge_mutation",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "manifest_path": str(manifest_path),
        "input_sha256": rt.sha256_bytes(data),
        "output_sha256": rt.sha256_bytes(mutated),
        "input_size": len(data),
        "output_size": len(mutated),
        "changed_offsets": diff_offsets,
        "changed_cells": [cell_to_manifest(cell) for cell in cells],
        "changed_cell_count": len(cells),
        "changed_byte_count": len(diff_offsets),
        "expected_changed_offsets": [cell.offset for cell in cells],
        "transpose_mismatch_before": transpose_before,
        "transpose_mismatch_after": transpose_after,
        "map_setting_node_world_transform": "unproven",
        "risk_acceptance_required": True,
        "risk_acceptance": "accepted_for_one_controlled_probe",
        "risk_label": "risk-accepted candidate, not proven safe",
        "runtime_installed": False,
        "safety": {
            "read_only_install_state": True,
            "map_setting_override_installed": False,
            "automatic_install": False,
            "allowed_mutation_only": True,
            "packed4_0_changed": False,
            "packed4_1_changed": False,
            "visual_assets_changed": False,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def mutate_symmetric_edge(
    input_path: Path,
    output_path: Path,
    manifest_path: Path,
    confirm_risk_accepted: bool,
    expected_sha256: str = rt.MAP_SETTING_SHA256,
    cells: tuple[MutationCell, ...] = PRODUCTION_CELLS,
) -> dict[str, Any]:
    if not confirm_risk_accepted:
        raise SystemExit("Refusing to mutate without --confirm-risk-accepted.")
    input_path = input_path.resolve()
    output_path = output_path.resolve()
    manifest_path = manifest_path.resolve()
    ensure_mutation_paths_are_safe(input_path, output_path, manifest_path)

    data = input_path.read_bytes()
    input_sha256 = rt.sha256_bytes(data)
    if input_sha256.lower() != expected_sha256.lower():
        raise SystemExit(
            f"Input SHA-256 {input_sha256} does not match expected {expected_sha256}; refusing mutation."
        )

    document = rt.decode_map_setting(data)
    _chunked_values, width, _height, transpose_before = validate_candidate_cells(data, document, cells)

    mutated = bytearray(data)
    for cell in cells:
        mutated[cell.offset] = cell.new_value
    mutated_bytes = bytes(mutated)

    diff_offsets = changed_offsets(data, mutated_bytes)
    expected_offsets = [cell.offset for cell in cells]
    if diff_offsets != expected_offsets:
        raise SystemExit(f"Unexpected changed offsets {diff_offsets}; expected {expected_offsets}.")
    if len(diff_offsets) != len(cells):
        raise SystemExit(f"Unexpected changed byte count {len(diff_offsets)}; expected {len(cells)}.")

    transpose_after = validate_output(mutated_bytes, cells, width)
    if transpose_after != 0:
        raise SystemExit(f"Refusing output because transpose_mismatch_after is {transpose_after}, expected 0.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(mutated_bytes)
    persisted = output_path.read_bytes()
    if persisted != mutated_bytes:
        raise SystemExit("Persisted mutation output differs from the in-memory mutation bytes.")

    manifest = build_manifest(input_path, output_path, manifest_path, data, persisted, cells, transpose_before, transpose_after)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "input_sha256": manifest["input_sha256"],
        "output_sha256": manifest["output_sha256"],
        "changed_offsets": manifest["changed_offsets"],
        "changed_byte_count": manifest["changed_byte_count"],
        "transpose_mismatch_after": manifest["transpose_mismatch_after"],
        "runtime_installed": manifest["runtime_installed"],
        "risk_label": manifest["risk_label"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one risk-accepted two-byte map_setting mutation outside the repo.")
    parser.add_argument("--input", type=Path, required=True, help="Repository-external original map_setting baseline.")
    parser.add_argument("--output", type=Path, required=True, help="Repository-external mutated map_setting output.")
    parser.add_argument("--manifest", type=Path, required=True, help="Repository-external mutation manifest.")
    parser.add_argument(
        "--confirm-risk-accepted",
        action="store_true",
        help="Required. Confirms docs/minimal_mutation_risk_acceptance.md has been reviewed and accepted.",
    )
    args = parser.parse_args()
    manifest = mutate_symmetric_edge(
        input_path=args.input,
        output_path=args.output,
        manifest_path=args.manifest,
        confirm_risk_accepted=args.confirm_risk_accepted,
    )
    print(json.dumps(stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
