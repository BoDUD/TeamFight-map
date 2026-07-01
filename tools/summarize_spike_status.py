from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2s_map_setting_route_decision")
OUTPUT_FILENAME = "q2s_status_matrix.json"


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def ensure_output_is_safe(output_path: Path) -> Path:
    output_path = output_path.resolve()
    inspect.ensure_outside_repo(output_path, "Q2S status output")
    if is_under_mods_tree(output_path):
        raise SystemExit("Refusing to write Q2S status output under a runtime mods tree.")
    if output_path.exists() and output_path.is_dir():
        raise SystemExit(f"Refusing to overwrite directory with Q2S status output: {output_path}")
    return output_path


def build_status_matrix() -> dict[str, Any]:
    return {
        "probe": "q2s_map_setting_route_decision",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "q2_map_setting_route_status": "blocked_pending_runtime_anchor",
        "node_world_transform": "unproven",
        "semantic_safety": "not_proven",
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "third_chunked_binary_runtime_probe_allowed": False,
        "map_editing_allowed": False,
        "recommended_next_route": "choose_visual_only_deliverable_or_runtime_anchor_spike",
        "proven": [
            "background_5v5 visual override works",
            "map_setting override registration and local file read work",
            "map_setting structural decode/re-encode round trip is byte-identical",
            "bounded two-byte chunked_binary mutations can be loaded and observed in 5v5",
        ],
        "not_proven": [
            "chunked_binary gameplay semantics",
            "packed4_0 gameplay semantics",
            "packed4_1 gameplay semantics",
            "node/world transform",
            "collision editing",
            "lane path editing",
            "spawn editing",
            "brush gameplay mask",
            "objective placement",
            "safe broader map_setting mutation",
        ],
        "closed_or_low_value_routes": [
            {
                "route": "blind third chunked_binary runtime probe",
                "status": "not_approved",
                "reason": "Q2e/Q2f and Q2g loader probes produced no clear semantic signal.",
            },
            {
                "route": "more coarse visual correlation masks",
                "status": "low_value",
                "reason": "Q2N and Q2Q visual correlation results stayed ambiguous.",
            },
            {
                "route": "residual/unclassified map_setting section search",
                "status": "closed",
                "reason": "Q2R found the known structural layers consume the full baseline file.",
            },
            {
                "route": "region or multi-edge mutation",
                "status": "not_approved",
                "reason": "No semantic field proof or node/world transform is available.",
            },
            {
                "route": "packed4 mutation",
                "status": "not_approved",
                "reason": "packed4_0 and packed4_1 roles remain static candidates, not editable gameplay fields.",
            },
        ],
        "route_a_visual_only_deliverable": {
            "status": "allowed_for_separate_pr",
            "purpose": "Produce a non-gameplay LOL-like visual skin or concept mod.",
            "allowed": [
                "background_5v5",
                "minimap_5v5_bg",
                "visual-only layer resources after separate visual QA",
                "docs/concept assets",
                "README and install instructions",
            ],
            "forbidden": [
                "map_setting",
                "collision/path/spawn data",
                "brush gameplay",
                "objective placement",
                "AI route edits",
            ],
            "recommended_label": "visual-only LOL-like map skin",
        },
        "route_b_runtime_anchor_spike": {
            "status": "allowed_for_separate_pr",
            "purpose": "Find independent runtime evidence before any gameplay map editing.",
            "must_prove_before_map_editing": [
                "node_world_transform",
                "field semantic proof",
                "one small local reversible effect",
            ],
            "candidate_surfaces": [
                "DLL / ModExtension ability to read entity positions",
                "runtime screenshot plus deterministic entity position anchors",
                "debug overlay or camera transform",
                "memory-safe process observation",
                "other reliable runtime evidence",
            ],
            "must_not_mix_with": [
                "visual-only deliverable",
                "map_setting mutation",
                "collision/path/spawn edits",
            ],
        },
        "next_pr_recommendation": {
            "preferred": "route_a_visual_only_deliverable",
            "reason": (
                "The visual override route is the only currently proven user-facing deliverable; "
                "gameplay map editing remains blocked pending runtime anchor and semantic proof."
            ),
            "possible_follow_up": {
                "branch": "visual/lol-like-background-minimap-skin",
                "title": "[visual] add LOL-like non-gameplay map skin package",
            },
        },
        "blocked_actions": [
            "third runtime mutation",
            "packed4_0 mutation",
            "packed4_1 mutation",
            "multi-edge or region mutation",
            "collision/path/spawn editing",
            "brush gameplay mask editing",
            "objective placement edit",
            "formal LOL gameplay map export",
        ],
    }


def write_status_matrix(output_path: Path) -> dict[str, Any]:
    output_path = ensure_output_is_safe(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    matrix = build_status_matrix()
    output_path.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return {
        "probe": "q2s_map_setting_route_decision",
        "output": {
            "path": str(output_path),
            "size": output_path.stat().st_size,
            "sha256": rt.sha256_file(output_path),
        },
        "q2_map_setting_route_status": matrix["q2_map_setting_route_status"],
        "node_world_transform": matrix["node_world_transform"],
        "semantic_safety": matrix["semantic_safety"],
        "runtime_mutation_allowed": matrix["runtime_mutation_allowed"],
        "packed4_mutation_allowed": matrix["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": matrix["third_chunked_binary_runtime_probe_allowed"],
        "map_editing_allowed": matrix["map_editing_allowed"],
        "recommended_next_route": matrix["recommended_next_route"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Q2S map_setting spike route-decision status matrix.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR / OUTPUT_FILENAME)
    parser.add_argument("--print-matrix", action="store_true")
    args = parser.parse_args()

    summary = write_status_matrix(args.output)
    if args.print_matrix:
        print((args.output.resolve()).read_text(encoding="utf-8"))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
