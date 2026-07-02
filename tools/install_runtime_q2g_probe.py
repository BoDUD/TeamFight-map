from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import install_runtime_spike_mod as spike  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


MODE_TO_MANIFEST = {
    "A1": "q2g_a1_stage_manifest.json",
    "B": "q2g_b_stage_manifest.json",
    "A2": "q2g_a2_stage_manifest.json",
}
BASELINE_SHA256 = rt.MAP_SETTING_SHA256
Q2G_CANDIDATE = "59-837"
EXPECTED_MUTATION_OFFSETS = [66605, 932331]
EXPECTED_MUTATION_CELLS = [
    {
        "logical_coordinate": [837, 59],
        "source_node": 59,
        "target_node": 837,
        "offset": 66605,
        "old": 1,
        "new": 0,
    },
    {
        "logical_coordinate": [59, 837],
        "source_node": 837,
        "target_node": 59,
        "offset": 932331,
        "old": 1,
        "new": 0,
    },
]
DEFAULT_EVIDENCE_DIR = Path("D:/tfm2_q2a_evidence/q2g_second_candidate_probe")


def normalize_mode(mode: str) -> str:
    normalized = mode.upper()
    if normalized not in MODE_TO_MANIFEST:
        raise SystemExit("Mode must be one of A1, B, or A2.")
    return normalized


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def ensure_source_is_safe(source: Path) -> None:
    if not source.is_file():
        raise SystemExit(f"map_setting source is not a file: {source}")
    if rt.is_inside_repo(source):
        raise SystemExit(f"Refusing to stage repository-internal map_setting source: {source}")
    if is_under_mods_tree(source):
        raise SystemExit("Refusing to stage from an installed mods tree; use repository-external evidence/source files.")


def load_mutation_manifest(path: Path | None, mode: str) -> dict[str, Any] | None:
    if mode != "B":
        return None
    if path is None:
        raise SystemExit("Mode B requires --mutation-manifest.")
    if not path.is_file():
        raise SystemExit(f"mutation manifest is not a file: {path}")
    if rt.is_inside_repo(path):
        raise SystemExit(f"Refusing to read repository-internal mutation manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_baseline_source(source: Path, mode: str) -> str:
    source_sha = spike.sha256_file(source)
    if source_sha.lower() != BASELINE_SHA256:
        raise SystemExit(f"Mode {mode} source SHA-256 {source_sha} does not match baseline {BASELINE_SHA256}.")
    return source_sha


def validate_mutation_manifest_shape(mutation_manifest: dict[str, Any]) -> None:
    if mutation_manifest.get("probe") != "risk_accepted_second_candidate_symmetric_edge_mutation":
        raise SystemExit("Mutation manifest probe is not the approved Q2g second-candidate probe.")
    if mutation_manifest.get("candidate") != Q2G_CANDIDATE:
        raise SystemExit("Mutation manifest candidate does not match approved Q2g candidate 59-837.")
    if mutation_manifest.get("risk_acceptance") != "accepted_for_one_controlled_second_candidate_probe":
        raise SystemExit("Mutation manifest risk_acceptance does not match Q2g acceptance.")
    if mutation_manifest.get("risk_label") != "risk-accepted second candidate, not proven safe":
        raise SystemExit("Mutation manifest risk_label does not match Q2g acceptance.")
    if mutation_manifest.get("input_sha256", "").lower() != BASELINE_SHA256:
        raise SystemExit("Mutation manifest input_sha256 does not match the known baseline.")
    if mutation_manifest.get("changed_offsets") != EXPECTED_MUTATION_OFFSETS:
        raise SystemExit("Mutation manifest changed_offsets do not match the approved Q2g offsets.")
    if mutation_manifest.get("expected_changed_offsets") != EXPECTED_MUTATION_OFFSETS:
        raise SystemExit("Mutation manifest expected_changed_offsets do not match the approved Q2g offsets.")
    if mutation_manifest.get("changed_cells") != EXPECTED_MUTATION_CELLS:
        raise SystemExit("Mutation manifest changed_cells do not match the approved Q2g cells.")
    if mutation_manifest.get("changed_byte_count") != 2:
        raise SystemExit("Mutation manifest changed_byte_count must be 2.")
    if mutation_manifest.get("changed_cell_count") != 2:
        raise SystemExit("Mutation manifest changed_cell_count must be 2.")
    if mutation_manifest.get("input_size") != mutation_manifest.get("output_size"):
        raise SystemExit("Mutation manifest input_size and output_size must match.")
    if mutation_manifest.get("transpose_mismatch_after") != 0:
        raise SystemExit("Mutation manifest transpose_mismatch_after must be 0.")
    if mutation_manifest.get("runtime_installed") is not False:
        raise SystemExit("Mutation manifest must state runtime_installed: false.")
    if mutation_manifest.get("map_setting_node_world_transform") != "unproven":
        raise SystemExit("Mutation manifest must keep map_setting_node_world_transform: unproven.")
    if mutation_manifest.get("runtime_stage_allowed_by_this_tool") is not False:
        raise SystemExit("Mutation manifest must state runtime_stage_allowed_by_this_tool: false.")


def validate_mutation_source(source: Path, mutation_manifest: dict[str, Any]) -> str:
    validate_mutation_manifest_shape(mutation_manifest)
    source_sha = spike.sha256_file(source)
    expected_sha = mutation_manifest.get("output_sha256")
    if source_sha.lower() != str(expected_sha).lower():
        raise SystemExit(f"Mode B source SHA-256 {source_sha} does not match mutation manifest output {expected_sha}.")
    if mutation_manifest.get("output_size") != source.stat().st_size:
        raise SystemExit("Mode B source size does not match mutation manifest output_size.")
    manifest_input_path = mutation_manifest.get("input_path")
    if not manifest_input_path:
        raise SystemExit("Mutation manifest must include input_path for B diff verification.")
    baseline_source = Path(str(manifest_input_path)).resolve()
    ensure_source_is_safe(baseline_source)
    if spike.sha256_file(baseline_source).lower() != BASELINE_SHA256:
        raise SystemExit("Mutation manifest input_path does not match the known baseline SHA-256.")
    baseline_data = baseline_source.read_bytes()
    mutated_data = source.read_bytes()
    if len(baseline_data) != len(mutated_data):
        raise SystemExit("Mode B baseline and mutated files have different lengths.")
    if len(mutated_data) <= max(EXPECTED_MUTATION_OFFSETS):
        raise SystemExit("Mode B source is too small to contain the approved Q2g offsets.")
    diff_offsets = [index for index, (left, right) in enumerate(zip(baseline_data, mutated_data)) if left != right]
    if diff_offsets != EXPECTED_MUTATION_OFFSETS:
        raise SystemExit(f"Mode B actual byte diff {diff_offsets} does not match the approved Q2g offsets.")
    for cell in EXPECTED_MUTATION_CELLS:
        offset = cell["offset"]
        if baseline_data[offset] != cell["old"] or mutated_data[offset] != cell["new"]:
            raise SystemExit("Mode B actual old/new byte values do not match the approved Q2g mutation.")
    return source_sha


def ensure_existing_install_can_stage(game_root: Path, clean: bool) -> None:
    if clean:
        return
    installed_mod = game_root / "mods" / spike.MOD_ID
    override_path = installed_mod / "mod.override_info"
    if not override_path.exists():
        return
    with override_path.open("r", encoding="utf-8") as handle:
        overrides = json.load(handle)
    if spike.MAP_SETTING_ASSET in overrides:
        raise SystemExit("Installed override already contains map_setting; run with --clean to reset before staging.")


def load_base_override_for_staging(installed_mod: Path) -> tuple[Path, dict[str, Any]]:
    override_path = installed_mod / "mod.override_info"
    overrides = spike.load_override_table(override_path)
    if set(overrides) != set(spike.DEFAULT_VISUAL_ASSETS):
        raise SystemExit("Q2g staging requires the default visual-only overrides.")
    return override_path, overrides


def override_with_map_setting(override_path: Path, overrides: dict[str, Any]) -> Path:
    overrides = dict(overrides)
    overrides[spike.MAP_SETTING_ASSET] = {"remapping": spike.MAP_SETTING_REMAP, "type": "override"}
    if set(overrides) != set(spike.DEFAULT_VISUAL_ASSETS) | {spike.MAP_SETTING_ASSET}:
        raise SystemExit("Q2g staging allows only default visual overrides and map_setting.")
    override_path.write_text(json.dumps(overrides, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return override_path


def stage_runtime_q2g_probe(
    game_root: Path,
    mode: str,
    map_setting_source: Path,
    evidence_dir: Path = DEFAULT_EVIDENCE_DIR,
    mutation_manifest_path: Path | None = None,
    clean: bool = False,
    enable_exclusive: bool = False,
) -> dict[str, Any]:
    mode = normalize_mode(mode)
    game_root = game_root.resolve()
    map_setting_source = map_setting_source.resolve()
    evidence_dir = evidence_dir.resolve()
    mutation_manifest_path = mutation_manifest_path.resolve() if mutation_manifest_path else None
    ensure_source_is_safe(map_setting_source)
    if rt.is_inside_repo(evidence_dir):
        raise SystemExit(f"Refusing to write stage evidence inside the repository: {evidence_dir}")

    mutation_manifest = load_mutation_manifest(mutation_manifest_path, mode)
    if mode in {"A1", "A2"}:
        source_sha = validate_baseline_source(map_setting_source, mode)
        expected_stage = "original_byte_equivalent"
    else:
        assert mutation_manifest is not None
        source_sha = validate_mutation_source(map_setting_source, mutation_manifest)
        expected_stage = "q2g_second_candidate_two_byte_mutation"

    ensure_existing_install_can_stage(game_root, clean)
    installed_mod = spike.copy_mod(game_root, clean=clean)
    override_path, base_overrides = load_base_override_for_staging(installed_mod)
    target = installed_mod / spike.MAP_SETTING_STAGED_RELATIVE_PATH
    expected_target = (game_root / "mods" / spike.MOD_ID / spike.MAP_SETTING_STAGED_RELATIVE_PATH).resolve()
    if target.resolve() != expected_target:
        raise SystemExit(f"Unexpected installed target path: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(map_setting_source, target)

    source_size = map_setting_source.stat().st_size
    target_size = target.stat().st_size
    target_sha = spike.sha256_file(target)
    byte_equal = spike.files_are_byte_equal(map_setting_source, target)
    if source_size != target_size or source_sha != target_sha or not byte_equal:
        raise SystemExit("Copied map_setting failed byte-equivalence checks; refusing staged Q2g probe.")

    override_path = override_with_map_setting(override_path, base_overrides)
    installed_overrides = json.loads(override_path.read_text(encoding="utf-8"))
    if spike.MAP_SETTING_ASSET not in installed_overrides:
        raise SystemExit("Installed override does not contain map_setting after staging.")
    if set(installed_overrides) != set(spike.DEFAULT_VISUAL_ASSETS) | {spike.MAP_SETTING_ASSET}:
        raise SystemExit("Installed override contains unexpected assets after Q2g staging.")

    config_path = None
    if enable_exclusive:
        config_path = spike.enable_mod(game_root, exclusive=True)

    evidence_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = evidence_dir / MODE_TO_MANIFEST[mode]
    game_exe = game_root / "TeamfightManager2.exe"
    base_version_path = game_root / "mod-sdk" / "base_version.txt"
    manifest = {
        "probe": "q2g_second_candidate_loader_probe_stage",
        "candidate": Q2G_CANDIDATE,
        "mode": mode,
        "stage": expected_stage,
        "mod_id": spike.MOD_ID,
        "game_root": str(game_root),
        "game_exe": str(game_exe),
        "game_exe_size": game_exe.stat().st_size if game_exe.exists() else None,
        "game_exe_sha256": spike.sha256_file(game_exe) if game_exe.exists() else None,
        "base_version": base_version_path.read_text(encoding="utf-8").strip() if base_version_path.exists() else None,
        "source_path": str(map_setting_source),
        "target_path": str(target),
        "target_path_expected": str(expected_target),
        "override_path": str(override_path),
        "asset_key": spike.MAP_SETTING_ASSET,
        "remapping": spike.MAP_SETTING_REMAP,
        "source_size": source_size,
        "target_size": target_size,
        "source_sha256": source_sha,
        "target_sha256": target_sha,
        "byte_equal": byte_equal,
        "override_keys": sorted(installed_overrides),
        "map_setting_override_installed": True,
        "unrelated_overrides_installed": False,
        "mutation_manifest_path": str(mutation_manifest_path) if mutation_manifest_path else None,
        "mutation_manifest_input_path": mutation_manifest.get("input_path") if mutation_manifest else None,
        "mutation_manifest_output_sha256": mutation_manifest.get("output_sha256") if mutation_manifest else None,
        "actual_changed_offsets": EXPECTED_MUTATION_OFFSETS if mode == "B" else [],
        "approved_changed_offsets": EXPECTED_MUTATION_OFFSETS if mode == "B" else [],
        "approved_changed_cells": EXPECTED_MUTATION_CELLS if mode == "B" else [],
        "enable_exclusive": enable_exclusive,
        "config_path": str(config_path) if config_path else None,
        "runtime_validation": "pending_manual_cold_start",
        "semantic_safety": "not_proven",
        "map_setting_node_world_transform": "unproven",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Staged Q2g {mode} map_setting probe in installed mod: {target}")
    print(f"Wrote stage manifest: {manifest_path}")
    return manifest


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "candidate": manifest["candidate"],
        "mode": manifest["mode"],
        "stage": manifest["stage"],
        "target_path": manifest["target_path"],
        "source_sha256": manifest["source_sha256"],
        "target_sha256": manifest["target_sha256"],
        "map_setting_override_installed": manifest["map_setting_override_installed"],
        "runtime_validation": manifest["runtime_validation"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage one Q2g A/B/A map_setting runtime mutation probe.")
    parser.add_argument("--game-root", type=Path, default=None)
    parser.add_argument("--mode", required=True, choices=("A1", "B", "A2", "a1", "b", "a2"))
    parser.add_argument("--map-setting-source", type=Path, required=True)
    parser.add_argument("--mutation-manifest", type=Path, default=None)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--enable-exclusive", action="store_true")
    args = parser.parse_args()
    game_root = (args.game_root or spike.infer_game_root()).resolve()
    manifest = stage_runtime_q2g_probe(
        game_root=game_root,
        mode=args.mode,
        map_setting_source=args.map_setting_source,
        evidence_dir=args.evidence_dir,
        mutation_manifest_path=args.mutation_manifest,
        clean=args.clean,
        enable_exclusive=args.enable_exclusive,
    )
    print(json.dumps(stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
