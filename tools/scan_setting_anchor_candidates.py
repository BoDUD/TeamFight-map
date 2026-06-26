from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import bundle_utils  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402

KNOWN_MARKERS = (30, 900, 27000, 810000, 1451980, 1280, 320, 100)
OUTPUT_NAMES = (
    "setting_blob_signatures.json",
    "possible_coordinate_tables.json",
    "anchor_candidate_report.json",
)
SCAN_SIZE_LIMIT = 32 * 1024 * 1024


def paths_are_same_existing_file(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    try:
        return left.samefile(right)
    except OSError:
        return False


def ensure_output_dir_is_safe(bundle_path: Path, asset_index: Path, output_dir: Path) -> None:
    if rt.is_inside_repo(output_dir):
        raise SystemExit(f"Refusing to write setting scan evidence inside the repository: {output_dir}")
    if bundle_path == output_dir or output_dir in bundle_path.parents:
        raise SystemExit(f"Refusing to scan with bundle inside the output directory: {bundle_path}")
    if paths_are_same_existing_file(bundle_path, output_dir):
        raise SystemExit(f"Refusing to scan with bundle aliased to the output directory: {bundle_path}")
    for name in OUTPUT_NAMES:
        output_path = output_dir / name
        for label, source in (("bundle", bundle_path), ("asset index", asset_index)):
            if output_path == source or paths_are_same_existing_file(output_path, source):
                raise SystemExit(f"Refusing to overwrite {label} through scan output path: {output_path}")


def load_asset_index(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if "assets" in data:
        return data["assets"]
    if "candidates" in data:
        return data["candidates"]
    raise ValueError(f"Unsupported asset index shape: {path}")


def is_binary_setting_candidate(asset: dict[str, Any]) -> bool:
    key = asset.get("asset_key", "").lower()
    asset_type = asset.get("asset_type", "").lower()
    category = asset.get("category_guess", "").lower()
    if any(token in asset_type for token in ("png", "aseprite", "image")):
        return False
    if "aseprite_resources" in key or "#sheet" in key or "#anim" in key:
        return False
    return any(
        token in f"{key} {asset_type} {category}"
        for token in ("setting", "map_setting", "path", "visible", "view", "collision", "spawn", "map")
    )


def scan_known_markers(data: bytes) -> dict[str, Any]:
    u32_counts: Counter[int] = Counter()
    u64_counts: Counter[int] = Counter()
    samples: dict[str, list[int]] = {str(value): [] for value in KNOWN_MARKERS}
    for offset in range(0, max(0, len(data) - 4 + 1), 4):
        value = struct.unpack_from("<I", data, offset)[0]
        if value in KNOWN_MARKERS:
            u32_counts[value] += 1
            if len(samples[str(value)]) < 12:
                samples[str(value)].append(offset)
    for offset in range(0, max(0, len(data) - 8 + 1), 8):
        value = struct.unpack_from("<Q", data, offset)[0]
        if value in KNOWN_MARKERS:
            u64_counts[value] += 1
            if len(samples[str(value)]) < 12:
                samples[str(value)].append(offset)
    return {
        "markers": {
            str(value): {
                "u32_count": u32_counts[value],
                "u64_count": u64_counts[value],
                "sample_offsets": samples[str(value)],
            }
            for value in KNOWN_MARKERS
            if u32_counts[value] or u64_counts[value]
        }
    }


def scan_length_prefixed_arrays(data: bytes) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    element_sizes = (1, 2, 4, 8, 12, 16, 24, 32)
    for offset in range(0, max(0, len(data) - 4 + 1), 4):
        count = struct.unpack_from("<I", data, offset)[0]
        if not (1 <= count <= 1000000):
            continue
        for element_size in element_sizes:
            payload_size = count * element_size
            if payload_size and offset + 4 + payload_size <= len(data):
                if count in KNOWN_MARKERS or 8 <= count <= 2048:
                    candidates.append(
                        {
                            "offset": offset,
                            "count": count,
                            "element_size": element_size,
                            "payload_end": offset + 4 + payload_size,
                            "hypothesis": "unverified_length_prefixed_array",
                        }
                    )
                    break
        if len(candidates) >= 80:
            break
    return candidates


def finite_float(value: float) -> bool:
    return math.isfinite(value) and not math.isnan(value)


def scan_float_coordinate_pairs(data: bytes) -> list[dict[str, Any]]:
    ranges = {
        "unit_or_percent_0_100": (0.0, 100.0),
        "texture_0_1280": (0.0, 1280.0),
    }
    counters = {name: 0 for name in ranges}
    samples = {name: [] for name in ranges}
    for offset in range(0, max(0, len(data) - 8 + 1), 4):
        left, right = struct.unpack_from("<ff", data, offset)
        if not (finite_float(left) and finite_float(right)):
            continue
        for name, (low, high) in ranges.items():
            if low <= left <= high and low <= right <= high:
                counters[name] += 1
                if len(samples[name]) < 16:
                    samples[name].append({"offset": offset, "x": round(left, 6), "y": round(right, 6)})
    return [
        {
            "encoding": "float32_pair_little_endian",
            "range": name,
            "candidate_pair_count": counters[name],
            "sample_pairs": samples[name],
            "hypothesis": "unverified_coordinate_pairs",
        }
        for name in ranges
        if counters[name]
    ]


def scan_int16_coordinate_pairs(data: bytes) -> list[dict[str, Any]]:
    ranges = {
        "unit_or_percent_0_100": (0, 100),
        "texture_0_1280": (0, 1280),
    }
    counters = {name: 0 for name in ranges}
    samples = {name: [] for name in ranges}
    for offset in range(0, max(0, len(data) - 4 + 1), 2):
        left, right = struct.unpack_from("<hh", data, offset)
        for name, (low, high) in ranges.items():
            if low <= left <= high and low <= right <= high:
                counters[name] += 1
                if len(samples[name]) < 16:
                    samples[name].append({"offset": offset, "x": left, "y": right})
    return [
        {
            "encoding": "int16_pair_little_endian",
            "range": name,
            "candidate_pair_count": counters[name],
            "sample_pairs": samples[name],
            "hypothesis": "unverified_coordinate_pairs",
        }
        for name in ranges
        if counters[name]
    ]


def scan_blob(asset: dict[str, Any], data: bytes) -> dict[str, Any]:
    if len(data) > SCAN_SIZE_LIMIT:
        return {
            "asset_key": asset["asset_key"],
            "asset_type": asset["asset_type"],
            "size": len(data),
            "skipped": True,
            "reason": f"binary scan limit is {SCAN_SIZE_LIMIT} bytes",
        }
    markers = scan_known_markers(data)
    length_arrays = scan_length_prefixed_arrays(data)
    float_pairs = scan_float_coordinate_pairs(data)
    int16_pairs = scan_int16_coordinate_pairs(data)
    coordinate_candidates = float_pairs + int16_pairs
    return {
        "asset_key": asset["asset_key"],
        "asset_type": asset["asset_type"],
        "size": len(data),
        "sha256": bundle_utils.sha256_bytes(data),
        "known_size_markers": markers["markers"],
        "length_prefixed_array_candidates": length_arrays,
        "coordinate_pair_candidates": coordinate_candidates,
        "entity_table_hypothesis": (
            "unverified_coordinate_table_candidate"
            if any(item["candidate_pair_count"] >= 3 for item in coordinate_candidates)
            else "no_coordinate_table_candidate_detected"
        ),
    }


def scan_candidates(bundle_path: Path, asset_index: Path, output_dir: Path) -> dict[str, Any]:
    bundle_path = bundle_path.resolve()
    asset_index = asset_index.resolve()
    output_dir = output_dir.resolve()
    ensure_output_dir_is_safe(bundle_path, asset_index, output_dir)

    assets = load_asset_index(asset_index)
    candidate_assets = [asset for asset in assets if is_binary_setting_candidate(asset)]
    scans: list[dict[str, Any]] = []
    coordinate_tables: list[dict[str, Any]] = []
    for asset in candidate_assets:
        try:
            asset_type, data = bundle_utils.read_bundle_entry(bundle_path, asset["asset_key"])
        except KeyError:
            scans.append(
                {
                    "asset_key": asset["asset_key"],
                    "asset_type": asset.get("asset_type"),
                    "skipped": True,
                    "reason": "asset key from index was not found in bundle",
                }
            )
            continue
        scan = scan_blob({**asset, "asset_type": asset_type}, data)
        scans.append(scan)
        for candidate in scan.get("coordinate_pair_candidates", []):
            if candidate["candidate_pair_count"] >= 3:
                coordinate_tables.append(
                    {
                        "asset_key": scan["asset_key"],
                        "asset_type": scan["asset_type"],
                        "encoding": candidate["encoding"],
                        "range": candidate["range"],
                        "candidate_pair_count": candidate["candidate_pair_count"],
                        "sample_pairs": candidate["sample_pairs"],
                        "hypothesis": "unverified_coordinate_table",
                    }
                )

    output_dir.mkdir(parents=True, exist_ok=True)
    signatures = {
        "probe": "setting_blob_signature_scan",
        "bundle_path": str(bundle_path),
        "asset_index": str(asset_index),
        "candidate_asset_count": len(candidate_assets),
        "scans": scans,
        "payloads_written": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    possible_tables = {
        "probe": "possible_coordinate_tables",
        "tables": coordinate_tables,
        "coordinate_tables_confirmed": False,
        "confirmation_reason": "No semantic entity labels or three non-collinear runtime anchors are decoded by this scan.",
        "payloads_written": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    report = {
        "probe": "offline_runtime_anchor_candidate_report",
        "bundle_path": str(bundle_path),
        "asset_index": str(asset_index),
        "offline_anchor_result": "no_sufficient_anchor_found",
        "map_setting_node_world_transform": "unproven",
        "candidate_369_370": "blocked",
        "unverified_coordinate_table_count": len(coordinate_tables),
        "candidate_asset_count": len(candidate_assets),
        "next_step": "Use a stronger decoder or independent runtime/debug surface before any map_setting mutation.",
        "payloads_written": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "setting_blob_signatures.json").write_text(
        json.dumps(signatures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    (output_dir / "possible_coordinate_tables.json").write_text(
        json.dumps(possible_tables, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    (output_dir / "anchor_candidate_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return report


def stdout_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": report["probe"],
        "offline_anchor_result": report["offline_anchor_result"],
        "map_setting_node_world_transform": report["map_setting_node_world_transform"],
        "candidate_369_370": report["candidate_369_370"],
        "unverified_coordinate_table_count": report["unverified_coordinate_table_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only structure scan for map anchor setting blobs.")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--asset-index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = scan_candidates(args.bundle, args.asset_index, args.output_dir)
    print(json.dumps(stdout_summary(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
