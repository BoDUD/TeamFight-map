from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import map_setting_mutate_symmetric_edge as edge_mutation  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


Q2G_CANDIDATE_ID = "59-837"
Q2G_PRODUCTION_CELLS = (
    edge_mutation.MutationCell(
        logical_coordinate=(837, 59),
        source_node=59,
        target_node=837,
        offset=66605,
        old_value=1,
        new_value=0,
    ),
    edge_mutation.MutationCell(
        logical_coordinate=(59, 837),
        source_node=837,
        target_node=59,
        offset=932331,
        old_value=1,
        new_value=0,
    ),
)


def build_q2g_manifest(
    input_path: Path,
    output_path: Path,
    manifest_path: Path,
    data: bytes,
    mutated: bytes,
    cells: tuple[edge_mutation.MutationCell, ...],
    transpose_before: int,
    transpose_after: int,
) -> dict[str, Any]:
    diff_offsets = edge_mutation.changed_offsets(data, mutated)
    return {
        "probe": "risk_accepted_second_candidate_symmetric_edge_mutation",
        "candidate": Q2G_CANDIDATE_ID,
        "layer": "chunked_binary",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "manifest_path": str(manifest_path),
        "input_sha256": rt.sha256_bytes(data),
        "output_sha256": rt.sha256_bytes(mutated),
        "input_size": len(data),
        "output_size": len(mutated),
        "changed_offsets": diff_offsets,
        "changed_cells": [edge_mutation.cell_to_manifest(cell) for cell in cells],
        "changed_cell_count": len(cells),
        "changed_byte_count": len(diff_offsets),
        "expected_changed_offsets": [cell.offset for cell in cells],
        "transpose_mismatch_before": transpose_before,
        "transpose_mismatch_after": transpose_after,
        "map_setting_node_world_transform": "unproven",
        "risk_acceptance_required": True,
        "risk_acceptance": "accepted_for_one_controlled_second_candidate_probe",
        "risk_label": "risk-accepted second candidate, not proven safe",
        "runtime_installed": False,
        "runtime_stage_allowed_by_this_tool": False,
        "intended_runtime_gate": "PR #15 A/B/A only",
        "safety": {
            "candidate_hardcoded": True,
            "read_only_install_state": True,
            "map_setting_override_installed": False,
            "automatic_install": False,
            "allowed_mutation_only": True,
            "packed4_0_changed": False,
            "packed4_1_changed": False,
            "visual_assets_changed": False,
            "second_candidate_only": True,
            "multi_edge_mutation": False,
            "region_mutation": False,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _mutate_q2g_second_candidate(
    input_path: Path,
    output_path: Path,
    manifest_path: Path,
    confirm_risk_accepted: bool,
    expected_sha256: str = rt.MAP_SETTING_SHA256,
    cells: tuple[edge_mutation.MutationCell, ...] = Q2G_PRODUCTION_CELLS,
) -> dict[str, Any]:
    if not confirm_risk_accepted:
        raise SystemExit("Refusing to mutate without --confirm-risk-accepted.")
    input_path = input_path.resolve()
    output_path = output_path.resolve()
    manifest_path = manifest_path.resolve()
    edge_mutation.ensure_mutation_paths_are_safe(input_path, output_path, manifest_path)

    data = input_path.read_bytes()
    input_sha256 = rt.sha256_bytes(data)
    if input_sha256.lower() != expected_sha256.lower():
        raise SystemExit(
            f"Input SHA-256 {input_sha256} does not match expected {expected_sha256}; refusing mutation."
        )

    document = rt.decode_map_setting(data)
    _chunked_values, width, _height, transpose_before = edge_mutation.validate_candidate_cells(data, document, cells)

    mutated = bytearray(data)
    for cell in cells:
        mutated[cell.offset] = cell.new_value
    mutated_bytes = bytes(mutated)

    diff_offsets = edge_mutation.changed_offsets(data, mutated_bytes)
    expected_offsets = [cell.offset for cell in cells]
    if diff_offsets != expected_offsets:
        raise SystemExit(f"Unexpected changed offsets {diff_offsets}; expected {expected_offsets}.")
    if len(diff_offsets) != len(cells):
        raise SystemExit(f"Unexpected changed byte count {len(diff_offsets)}; expected {len(cells)}.")

    transpose_after = edge_mutation.validate_output(mutated_bytes, cells, width)
    if transpose_after != 0:
        raise SystemExit(f"Refusing output because transpose_mismatch_after is {transpose_after}, expected 0.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(mutated_bytes)
    persisted = output_path.read_bytes()
    if persisted != mutated_bytes:
        raise SystemExit("Persisted mutation output differs from the in-memory mutation bytes.")

    manifest = build_q2g_manifest(input_path, output_path, manifest_path, data, persisted, cells, transpose_before, transpose_after)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


def mutate_q2g_second_candidate(
    input_path: Path,
    output_path: Path,
    manifest_path: Path,
    confirm_risk_accepted: bool,
) -> dict[str, Any]:
    return _mutate_q2g_second_candidate(
        input_path=input_path,
        output_path=output_path,
        manifest_path=manifest_path,
        confirm_risk_accepted=confirm_risk_accepted,
        expected_sha256=rt.MAP_SETTING_SHA256,
        cells=Q2G_PRODUCTION_CELLS,
    )


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "candidate": manifest["candidate"],
        "input_sha256": manifest["input_sha256"],
        "output_sha256": manifest["output_sha256"],
        "changed_offsets": manifest["changed_offsets"],
        "changed_byte_count": manifest["changed_byte_count"],
        "transpose_mismatch_after": manifest["transpose_mismatch_after"],
        "runtime_installed": manifest["runtime_installed"],
        "risk_label": manifest["risk_label"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the risk-accepted Q2g second-candidate two-byte map_setting mutation outside the repo."
    )
    parser.add_argument("--input", type=Path, required=True, help="Repository-external original map_setting baseline.")
    parser.add_argument("--output", type=Path, required=True, help="Repository-external mutated map_setting output.")
    parser.add_argument("--manifest", type=Path, required=True, help="Repository-external mutation manifest.")
    parser.add_argument(
        "--confirm-risk-accepted",
        action="store_true",
        help="Required. Confirms docs/q2g_second_candidate_risk_acceptance.md has been reviewed and accepted.",
    )
    args = parser.parse_args()
    manifest = mutate_q2g_second_candidate(
        input_path=args.input,
        output_path=args.output,
        manifest_path=args.manifest,
        confirm_risk_accepted=args.confirm_risk_accepted,
    )
    print(json.dumps(stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
