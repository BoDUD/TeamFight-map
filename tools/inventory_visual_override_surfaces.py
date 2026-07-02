from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/visual_map_detail_asset_inventory")
OUTPUT_FILENAME = "visual_override_surface_inventory.json"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

EXPECTED_SURFACES: list[dict[str, Any]] = [
    {
        "category": "background",
        "asset_candidate": "background_5v5",
        "visual_only": "proven visual-only background override",
        "default_enabled": True,
        "runtime_qa_needed": False,
        "risk": "low",
        "next_pr": "completed",
    },
    {
        "category": "terrain / wall",
        "asset_candidate": "wall_5v5",
        "visual_only": "default-enabled visual-only replacement of the existing wall layer",
        "default_enabled": True,
        "runtime_qa_needed": "default-package QA pending",
        "risk": "medium",
        "next_pr": "PR #37",
    },
    {
        "category": "terrain / wall",
        "asset_candidate": "wall_5v5_front",
        "visual_only": "default-enabled visual-only replacement of the existing front-wall layer",
        "default_enabled": True,
        "runtime_qa_needed": "default-package QA pending",
        "risk": "medium",
        "next_pr": "PR #37",
    },
    {
        "category": "brush visual",
        "asset_candidate": "bush_5v5",
        "visual_only": "only if the existing visual layer is replaced without changing gameplay brush masks",
        "default_enabled": False,
        "runtime_qa_needed": True,
        "risk": "high",
        "next_pr": "PR #38",
    },
    {
        "category": "minimap",
        "asset_candidate": "minimap_5v5_bg",
        "visual_only": "candidate prepared and optional installed-copy QA passed; not enabled by default",
        "default_enabled": False,
        "runtime_qa_needed": "default-enable QA needed before default package change",
        "risk": "medium",
        "next_pr": "PR #39",
    },
    {
        "category": "tower / crystal / base",
        "asset_candidate": "tower",
        "visual_only": "unknown until actor or atlas surface is identified",
        "default_enabled": False,
        "runtime_qa_needed": True,
        "risk": "high",
        "next_pr": "PR #40",
    },
    {
        "category": "tower / crystal / base",
        "asset_candidate": "crystal / base",
        "visual_only": "unknown until actor or atlas surface is identified",
        "default_enabled": False,
        "runtime_qa_needed": True,
        "risk": "high",
        "next_pr": "PR #40",
    },
    {
        "category": "jungle / neutral monsters",
        "asset_candidate": "monster / jungle objective actors",
        "visual_only": "unknown; likely actor sprites or animation atlases, not background paint",
        "default_enabled": False,
        "runtime_qa_needed": True,
        "risk": "high",
        "next_pr": "PR #42",
    },
]

DEFAULT_SCAN_RELATIVES = [
    "stage1b_evidence",
    "stage1c_evidence",
    "stage_runtime_spike_evidence",
    "native_layer_extracts",
    "native_actor_reference",
    "ModData",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def paths_are_same_existing_file(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    try:
        return left.samefile(right)
    except OSError:
        return False


def ensure_output_dir_is_safe(output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    if is_inside_repo(output_dir):
        raise SystemExit(f"Refusing to write visual inventory inside the repository: {output_dir}")
    if is_under_mods_tree(output_dir):
        raise SystemExit(f"Refusing to write visual inventory under a runtime mods tree: {output_dir}")
    if output_dir.exists() and not output_dir.is_dir():
        raise SystemExit(f"Refusing to overwrite non-directory visual inventory output: {output_dir}")
    return output_dir


def ensure_scan_root_is_safe(scan_root: Path) -> Path:
    scan_root = scan_root.resolve()
    if is_inside_repo(scan_root):
        raise SystemExit(f"Refusing to scan repository-internal visual source root: {scan_root}")
    if is_under_mods_tree(scan_root):
        raise SystemExit(f"Refusing to scan runtime mods tree as native visual source root: {scan_root}")
    return scan_root


def classify_path(path: Path) -> str:
    text = "/".join(part.lower() for part in path.parts)
    name = path.stem.lower()
    if "minimap" in text:
        return "minimap"
    if "background_5v5" in name or "background" in name:
        return "background"
    if "wall_5v5_front" in name or ("front" in name and "wall" in name):
        return "terrain / wall"
    if "wall_5v5" in name or any(token in text for token in ("wall", "stone", "rock", "terrain", "prop", "decoration")):
        return "terrain / wall"
    if any(token in text for token in ("bush", "brush", "grass")):
        return "brush visual"
    if any(token in text for token in ("tower", "turret", "crystal", "nexus", "base")):
        return "tower / crystal / base"
    if any(token in text for token in ("monster", "jungle", "serpen", "morgard", "epic", "neutral", "camp")):
        return "jungle / neutral monsters"
    return "unknown"


def suspected_asset_name(path: Path) -> str:
    name = path.stem.lower()
    for candidate in ("background_5v5", "minimap_5v5_bg", "wall_5v5_front", "wall_5v5", "bush_5v5"):
        if candidate in name:
            return candidate
    if "tower" in name or "turret" in name:
        return "tower"
    if "crystal" in name or "nexus" in name or "base" in name:
        return "crystal / base"
    if "monster" in name or "jungle" in name or "serpen" in name or "morgard" in name:
        return "monster / jungle objective actors"
    return path.stem


def reference_kind(path: Path) -> str:
    text = "/".join(part.lower() for part in path.parts)
    name = path.name.lower()
    if any(token in text for token in ("native_layer_extracts", "native_reference", "native_actor_reference")):
        return "native_or_extracted_reference"
    if any(
        token in name
        for token in (
            "screenshot",
            "marker",
            "after_",
            "flow",
            "title",
            "current",
            "progress",
            "match",
            "ingame",
            "runtime",
        )
    ):
        return "runtime_or_probe_screenshot"
    if "moddata" in text:
        return "game_data_image_candidate"
    return "unclassified_image_candidate"


def image_dimensions(path: Path) -> list[int] | None:
    try:
        with Image.open(path) as image:
            return [int(image.size[0]), int(image.size[1])]
    except Exception:
        return None


def iter_image_files(scan_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in scan_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        resolved = path.resolve()
        if is_inside_repo(resolved) or is_under_mods_tree(resolved):
            continue
        files.append(resolved)
    return sorted(files, key=lambda item: str(item).lower())


def entry_for_path(path: Path, scan_root: Path) -> dict[str, Any]:
    dimensions = image_dimensions(path)
    return {
        "path": str(path),
        "relative_to_scan_root": str(path.relative_to(scan_root)) if path.is_relative_to(scan_root) else None,
        "filename": path.name,
        "size": path.stat().st_size,
        "image_dimensions": dimensions,
        "sha256": sha256_file(path),
        "suspected_category": classify_path(path),
        "asset_candidate": suspected_asset_name(path),
        "reference_kind": reference_kind(path),
        "is_in_runtime_mods_tree": is_under_mods_tree(path),
        "is_repository_asset": is_inside_repo(path),
        "payload_copied_to_repository": False,
    }


def surface_matrix(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_candidate[entry["asset_candidate"]].append(entry)
    matrix: list[dict[str, Any]] = []
    for surface in EXPECTED_SURFACES:
        candidate = surface["asset_candidate"]
        matches = by_candidate.get(candidate, [])
        if not matches and candidate == "crystal / base":
            matches = by_candidate.get("crystal / base", [])
        if not matches and candidate == "monster / jungle objective actors":
            matches = by_candidate.get("monster / jungle objective actors", [])
        native_matches = [
            entry for entry in matches if entry["reference_kind"] == "native_or_extracted_reference"
        ]
        first = (native_matches or matches)[0] if matches else None
        matrix.append(
            {
                **surface,
                "native_reference_found": bool(native_matches),
                "match_count": len(matches),
                "native_reference_match_count": len(native_matches),
                "representative_path": first["path"] if first else None,
                "representative_reference_kind": first["reference_kind"] if first else None,
                "representative_dimensions": first["image_dimensions"] if first else None,
                "representative_sha256": first["sha256"] if first else None,
            }
        )
    return matrix


def category_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(entry["suspected_category"] for entry in entries)
    reference_counts = Counter(entry["reference_kind"] for entry in entries)
    return {
        "total_image_candidates": len(entries),
        "by_category": {category: counts[category] for category in sorted(counts)},
        "by_reference_kind": {kind: reference_counts[kind] for kind in sorted(reference_counts)},
    }


def default_scan_roots(game_root: Path | None = None) -> list[Path]:
    root = game_root.resolve() if game_root else REPO_ROOT.parent.resolve()
    roots = []
    for relative in DEFAULT_SCAN_RELATIVES:
        candidate = root / relative
        if candidate.exists() and candidate.is_dir():
            roots.append(candidate)
    return roots


def build_inventory(scan_roots: list[Path], output_dir: Path) -> dict[str, Any]:
    output_dir = ensure_output_dir_is_safe(output_dir)
    safe_roots = [ensure_scan_root_is_safe(root) for root in scan_roots]
    output_path = output_dir / OUTPUT_FILENAME

    entries: list[dict[str, Any]] = []
    for scan_root in safe_roots:
        for image_path in iter_image_files(scan_root):
            if paths_are_same_existing_file(output_path, image_path):
                raise SystemExit(f"Refusing to overwrite scanned visual source through output path: {output_path}")
            entries.append(entry_for_path(image_path, scan_root))

    matrix = surface_matrix(entries)
    return {
        "probe": "visual_map_detail_asset_inventory",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scan_roots": [str(root) for root in safe_roots],
        "output_path": str(output_path),
        "payloads_written": False,
        "default_runtime_package_changed": False,
        "map_setting_override_installed": False,
        "minimap_default_enabled": False,
        "gameplay_data_modified": False,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
        "entries": entries,
        "category_summary": category_summary(entries),
        "surface_matrix": matrix,
        "recommended_next_prs": [
            "wall_front_wall_default_package_runtime_qa",
            "bush_visual_candidate",
            "minimap_default_enable_decision",
            "tower_crystal_asset_investigation",
            "jungle_monster_asset_investigation",
        ],
        "conclusion": {
            "visual_detail_inventory_result": "completed",
            "default_runtime_package_changed": False,
            "map_setting_override_installed": False,
            "minimap_default_enabled": False,
            "gameplay_data_modified": False,
        },
    }


def write_inventory(scan_roots: list[Path], output_dir: Path) -> dict[str, Any]:
    manifest = build_inventory(scan_roots, output_dir)
    output_path = Path(manifest["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return {
        "probe": manifest["probe"],
        "output_path": str(output_path),
        "output_size": output_path.stat().st_size,
        "output_sha256": sha256_file(output_path),
        "scan_root_count": len(scan_roots),
        "image_candidate_count": manifest["category_summary"]["total_image_candidates"],
        "default_runtime_package_changed": manifest["default_runtime_package_changed"],
        "map_setting_override_installed": manifest["map_setting_override_installed"],
        "minimap_default_enabled": manifest["minimap_default_enabled"],
        "map_editing_allowed": manifest["map_editing_allowed"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory repository-external visual override surfaces for Route A.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--game-root", type=Path, default=None)
    parser.add_argument("--scan-root", type=Path, action="append", default=None)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    roots = args.scan_root if args.scan_root else default_scan_roots(args.game_root)
    if not roots:
        raise SystemExit("No scan roots were found. Pass one or more --scan-root paths.")
    summary = write_inventory(roots, args.output_dir)
    if args.print_manifest:
        print(Path(summary["output_path"]).read_text(encoding="utf-8"))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
