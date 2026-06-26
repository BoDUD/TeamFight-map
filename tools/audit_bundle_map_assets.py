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

from tools import bundle_utils  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402

KEYWORDS = (
    "map",
    "setting",
    "5v5",
    "path",
    "visible",
    "view",
    "collision",
    "wall",
    "bush",
    "brush",
    "tower",
    "nexus",
    "spawn",
    "serpen",
    "morgard",
    "epic",
    "monster",
    "minimap",
)
OUTPUT_NAMES = (
    "bundle_asset_index.json",
    "bundle_map_related_assets.json",
    "bundle_map_anchor_candidates.json",
)


def paths_are_same_existing_file(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    try:
        return left.samefile(right)
    except OSError:
        return False


def ensure_output_dir_is_safe(bundle_path: Path, output_dir: Path) -> None:
    if rt.is_inside_repo(output_dir):
        raise SystemExit(f"Refusing to write bundle audit evidence inside the repository: {output_dir}")
    if bundle_path == output_dir or output_dir in bundle_path.parents:
        raise SystemExit(f"Refusing to audit with bundle inside the output directory: {bundle_path}")
    if paths_are_same_existing_file(bundle_path, output_dir):
        raise SystemExit(f"Refusing to audit with bundle aliased to the output directory: {bundle_path}")
    for name in OUTPUT_NAMES:
        output_path = output_dir / name
        if output_path == bundle_path or paths_are_same_existing_file(output_path, bundle_path):
            raise SystemExit(f"Refusing to overwrite bundle through audit output path: {output_path}")


def keyword_hits(asset_key: str, asset_type: str) -> list[str]:
    haystack = f"{asset_key} {asset_type}".lower()
    return [keyword for keyword in KEYWORDS if keyword in haystack]


def category_guess(asset_key: str, asset_type: str) -> str:
    key = asset_key.lower()
    type_lower = asset_type.lower()
    if key == "asset/base/setting/map_setting":
        return "map_setting"
    if "setting" in key or "setting" in type_lower:
        return "setting_or_runtime_data_candidate"
    if "minimap" in key:
        return "minimap_visual_reference"
    if any(token in key for token in ("wall", "bush", "brush", "background")) and "5v5" in key:
        return "map_visual_layer_reference"
    if any(token in key for token in ("tower", "nexus", "serpen", "morgard", "epic", "monster")):
        return "actor_or_objective_visual_reference"
    if any(token in key for token in ("path", "visible", "view", "collision", "spawn")):
        return "possible_runtime_anchor_data"
    if "map" in key or "5v5" in key:
        return "map_related_unverified"
    return "unrelated"


def candidate_record(entry: dict[str, Any]) -> dict[str, Any]:
    category = entry["category_guess"]
    reasons: list[str] = []
    if category in {"map_setting", "setting_or_runtime_data_candidate", "possible_runtime_anchor_data"}:
        candidate_kind = "possible_binary_anchor_source"
        reasons.append("metadata key/type suggests setting or runtime map data")
    elif category.endswith("_reference") or category == "map_visual_layer_reference":
        candidate_kind = "visual_alignment_reference"
        reasons.append("visual map/object asset can help offline overlay scoring but is not coordinate proof")
    else:
        candidate_kind = "map_related_unverified"
        reasons.append("keyword match only; no decoded anchor semantics")
    if "map_setting" in entry["asset_key"]:
        reasons.append("known loader-read map_setting asset")
    return {
        "asset_key": entry["asset_key"],
        "asset_type": entry["asset_type"],
        "size": entry["size"],
        "sha256": entry["sha256"],
        "category_guess": category,
        "candidate_kind": candidate_kind,
        "hypothesis": "unverified",
        "reasons": reasons,
    }


def audit_bundle(bundle_path: Path, output_dir: Path) -> dict[str, Any]:
    bundle_path = bundle_path.resolve()
    output_dir = output_dir.resolve()
    ensure_output_dir_is_safe(bundle_path, output_dir)
    entries: list[dict[str, Any]] = []
    for entry in bundle_utils.iter_bundle_entries(bundle_path):
        entry_dict = {
            "asset_key": entry.asset_key,
            "asset_type": entry.asset_type,
            "size": entry.size,
            "sha256": entry.sha256,
            "data_offset": entry.data_offset,
            "category_guess": category_guess(entry.asset_key, entry.asset_type),
        }
        entries.append(entry_dict)
    entries.sort(key=lambda item: item["asset_key"])

    related: list[dict[str, Any]] = []
    for entry in entries:
        hits = keyword_hits(entry["asset_key"], entry["asset_type"])
        if hits:
            related.append({**entry, "keyword_hits": hits})

    candidates = [candidate_record(entry) for entry in related]
    category_counts = Counter(entry["category_guess"] for entry in related)
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_index = {
        "probe": "bundle_map_asset_index",
        "bundle_path": str(bundle_path),
        "bundle_size": bundle_path.stat().st_size,
        "asset_count": len(entries),
        "assets": entries,
        "payloads_written": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    related_manifest = {
        "probe": "bundle_map_related_assets",
        "bundle_path": str(bundle_path),
        "keywords": list(KEYWORDS),
        "related_asset_count": len(related),
        "category_counts": {key: category_counts[key] for key in sorted(category_counts)},
        "assets": related,
        "payloads_written": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    candidate_manifest = {
        "probe": "bundle_map_anchor_candidates",
        "bundle_path": str(bundle_path),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "result": {
            "offline_anchor_result": "metadata_only_candidates_unverified",
            "map_setting_node_world_transform": "unproven",
            "candidate_369_370": "blocked",
        },
        "payloads_written": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "bundle_asset_index.json").write_text(
        json.dumps(bundle_index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    (output_dir / "bundle_map_related_assets.json").write_text(
        json.dumps(related_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    (output_dir / "bundle_map_anchor_candidates.json").write_text(
        json.dumps(candidate_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return candidate_manifest


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "candidate_count": manifest["candidate_count"],
        "offline_anchor_result": manifest["result"]["offline_anchor_result"],
        "map_setting_node_world_transform": manifest["result"]["map_setting_node_world_transform"],
        "payloads_written": manifest["payloads_written"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only metadata audit for map-related bundle assets.")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = audit_bundle(args.bundle, args.output_dir)
    print(json.dumps(stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
