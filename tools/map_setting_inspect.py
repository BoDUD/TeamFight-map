from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import map_setting_round_trip as rt  # noqa: E402

DEFAULT_ASSET_KEYS = {
    "background_5v5": "asset/base/aseprite_resources/ingame/5v5/background_5v5",
    "wall_5v5": "asset/base/aseprite_resources/ingame/5v5/wall_5v5",
    "wall_5v5_front": "asset/base/aseprite_resources/ingame/5v5/wall_5v5_front",
    "bush_5v5": "asset/base/aseprite_resources/ingame/5v5/bush_5v5",
    "minimap_5v5_bg": "asset/base/aseprite_resources/ingame/5v5/minimap_5v5_bg",
}


def ensure_outside_repo(path: Path, label: str) -> None:
    if rt.is_inside_repo(path):
        raise SystemExit(f"Refusing to write repository-internal {label}: {path}")


def read_u32(handle) -> int:
    raw = handle.read(4)
    if len(raw) != 4:
        raise EOFError("unexpected end of bundle while reading u32")
    return struct.unpack("<I", raw)[0]


def read_bundle_entry(bundle_path: Path, key: str) -> tuple[str, bytes]:
    with bundle_path.open("rb") as handle:
        entry_count = read_u32(handle)
        for _ in range(entry_count):
            type_len = read_u32(handle)
            asset_type = handle.read(type_len).decode("utf-8", "replace")
            key_len = read_u32(handle)
            asset_key = handle.read(key_len).decode("utf-8", "replace")
            data_len = read_u32(handle)
            data = handle.read(data_len)
            if len(data) != data_len:
                raise EOFError(f"unexpected end of bundle while reading asset data for {asset_key}")
            if asset_key == key:
                return asset_type, data
    raise KeyError(f"asset key not found in bundle: {key}")


def flatten_chunked_binary_layer(layer: rt.ChunkedBinaryLayer) -> tuple[list[int], int, int]:
    summary = rt.chunked_layer_summary(layer)
    if not summary["uniform_shape"]:
        raise ValueError("chunked binary layer is not uniform and cannot be flattened as a grid")
    width, height = summary["composed_size"]
    values = [0] * (width * height)
    grid_width = summary["row_widths"][0]
    grid_height = summary["row_counts_per_grid"][0]
    for group_y, group in enumerate(layer.groups):
        for group_x, grid in enumerate(group.grids):
            for local_y, row in enumerate(grid.rows):
                y = group_y * grid_height + local_y
                x0 = group_x * grid_width
                start = y * width + x0
                values[start : start + grid_width] = list(row)
    return values, int(width), int(height)


def unpack_packed4_layer(layer: rt.Packed4Layer) -> list[int]:
    values: list[int] = []
    for byte in layer.blob:
        values.append(byte & 0x0F)
        values.append(byte >> 4)
    return values


def histogram(values: list[int]) -> dict[str, int]:
    counter = Counter(values)
    return {str(key): counter[key] for key in sorted(counter)}


def bounding_boxes_by_value(values: list[int], width: int, height: int) -> dict[str, dict[str, Any]]:
    boxes: dict[int, list[int]] = {}
    counts: Counter[int] = Counter()
    for index, value in enumerate(values):
        x = index % width
        y = index // width
        counts[value] += 1
        if value not in boxes:
            boxes[value] = [x, y, x, y]
        else:
            box = boxes[value]
            box[0] = min(box[0], x)
            box[1] = min(box[1], y)
            box[2] = max(box[2], x)
            box[3] = max(box[3], y)
    return {
        str(value): {"count": counts[value], "bbox": boxes[value]}
        for value in sorted(boxes)
    }


def rotational_symmetry_mismatch_count(values: list[int], width: int, height: int) -> int:
    mismatches = 0
    for y in range(height):
        row_start = y * width
        opposite_row_start = (height - 1 - y) * width
        for x in range(width):
            if values[row_start + x] != values[opposite_row_start + (width - 1 - x)]:
                mismatches += 1
    return mismatches


def matrix_transpose_mismatch_count(values: list[int], size: int) -> int:
    mismatches = 0
    for y in range(size):
        row_start = y * size
        for x in range(size):
            if values[row_start + x] != values[x * size + y]:
                mismatches += 1
    return mismatches


def packed4_cell_location(layer: rt.Packed4Layer, x: int, y: int, width: int) -> dict[str, Any]:
    index = y * width + x
    byte_offset = layer.offset + 16 + index // 2
    return {
        "logical_coordinate": [x, y],
        "linear_cell_index": index,
        "serialized_byte_offset": byte_offset,
        "nibble": "low" if index % 2 == 0 else "high",
    }


def chunked_cell_offset(layer: rt.ChunkedBinaryLayer, x: int, y: int) -> int:
    summary = rt.chunked_layer_summary(layer)
    grid_width = int(summary["row_widths"][0])
    grid_height = int(summary["row_counts_per_grid"][0])
    group_y, local_y = divmod(y, grid_height)
    group_x, local_x = divmod(x, grid_width)
    offset = layer.offset + 8
    for current_group_y, group in enumerate(layer.groups):
        offset += 8
        for current_group_x, grid in enumerate(group.grids):
            offset += 8
            for current_local_y, row in enumerate(grid.rows):
                offset += 8
                if current_group_y == group_y and current_group_x == group_x and current_local_y == local_y:
                    return offset + local_x
                offset += len(row)
    raise ValueError(f"chunked coordinate outside layer: {(x, y)}")


def write_png_l(values: list[int], width: int, height: int, path: Path, max_value: int | None = None) -> None:
    from PIL import Image

    if len(values) != width * height:
        raise ValueError(f"{path.name}: got {len(values)} values for {width}x{height}")
    max_seen = max(values) if values else 0
    scale = 255 / max(1, max_value if max_value is not None else max_seen)
    image = Image.new("L", (width, height))
    image.putdata([round(value * scale) for value in values])
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def write_mask(values: list[int], width: int, height: int, selected: int, path: Path) -> None:
    from PIL import Image

    image = Image.new("L", (width, height))
    image.putdata([255 if value == selected else 0 for value in values])
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def extract_png(path: Path, data: bytes) -> dict[str, Any]:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    with Image.open(path) as image:
        size = list(image.size)
    return {"path": str(path), "size": size, "sha256": rt.sha256_file(path)}


def overlay_values_on_png(
    values: list[int],
    width: int,
    height: int,
    base_png: Path,
    output_path: Path,
    max_value: int,
) -> dict[str, Any]:
    from PIL import Image

    with Image.open(base_png).convert("RGBA") as base:
        mask = Image.new("L", (width, height))
        mask.putdata([round(value * 255 / max(1, max_value)) for value in values])
        mask = mask.resize(base.size, Image.Resampling.NEAREST)
        color = Image.new("RGBA", base.size, (255, 64, 0, 0))
        alpha = mask.point(lambda value: 0 if value == 0 else 96)
        color.putalpha(alpha)
        composed = Image.alpha_composite(base, color)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        composed.save(output_path)
        return {"path": str(output_path), "size": list(composed.size), "sha256": rt.sha256_file(output_path)}


def write_packed4_1_slices(values: list[int], output_dir: Path) -> list[dict[str, Any]]:
    if len(values) != 27000:
        return []
    outputs: list[dict[str, Any]] = []
    for slice_index in range(30):
        start = slice_index * 900
        path = output_dir / f"packed4_1_slice_{slice_index:02d}.png"
        write_png_l(values[start : start + 900], 30, 30, path, max_value=15)
        outputs.append({"slice": slice_index, "path": str(path), "sha256": rt.sha256_file(path)})
    return outputs


def source_target_from_matrix_coordinate(x: int, y: int, logical_size: int = 30) -> dict[str, Any]:
    source = y
    target = x
    return {
        "source_node": source,
        "target_node": target,
        "source_xy_30x30": [source % logical_size, source // logical_size],
        "target_xy_30x30": [target % logical_size, target // logical_size],
    }


def select_readonly_candidate(
    chunked_values: list[int],
    packed0_values: list[int],
    chunked_layer: rt.ChunkedBinaryLayer,
) -> dict[str, Any]:
    # Pick a low-risk matrix entry near the upper-left logical edge. Both the
    # old value and neighbor-sourced new value are common legal chunked values.
    width = 900
    preferred_sources = [31, 32, 61, 62]
    preferred_targets = [32, 33, 62, 63]
    for y in preferred_sources:
        for x in preferred_targets:
            index = y * width + x
            old_value = chunked_values[index]
            for neighbor_x, neighbor_y in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
                if not (0 <= neighbor_x < width and 0 <= neighbor_y < width):
                    continue
                new_value = chunked_values[neighbor_y * width + neighbor_x]
                if new_value != old_value:
                    context = source_target_from_matrix_coordinate(x, y)
                    return {
                        "status": "selected_for_follow_up_review",
                        "layer": "chunked_binary",
                        "hypothesis": "pairwise visibility or reachability bit between 30x30 logical cells; not confirmed",
                        "selection_reason": (
                            "The chunked layer has a 900x900 matrix shape, binary values, and a transpose mismatch count of 0, "
                            "which is consistent with a symmetric source-target relation rather than a direct 900x900 map texture."
                        ),
                        "logical_coordinate": [x, y],
                        **context,
                        "serialized_byte_offset": chunked_cell_offset(chunked_layer, x, y),
                        "old_value": old_value,
                        "new_value": new_value,
                        "new_value_source_coordinate": [neighbor_x, neighbor_y],
                        "predicted_effect": "hypothesis: one low-traffic edge source-target relation changes; no broad visual or AI effect is expected",
                        "prediction_confidence": "hypothesis",
                        "rollback_source_sha256": rt.MAP_SETTING_SHA256,
                        "do_not_mutate_in_this_pr": True,
                        "packed4_0_context_value": packed0_values[index],
                    }
    return {
        "status": "not_selected",
        "reason": "No preferred low-risk edge cell with a neighbor-sourced alternate value was found.",
    }


def build_manifest(
    input_path: Path,
    input_data: bytes,
    document: rt.MapSettingDocument,
    output_dir: Path,
    bundle_path: Path | None,
) -> dict[str, Any]:
    chunked_values, chunked_width, chunked_height = flatten_chunked_binary_layer(document.chunked_binary_layer)
    packed0_values = unpack_packed4_layer(document.packed4_layers[0])
    packed1_values = unpack_packed4_layer(document.packed4_layers[1]) if len(document.packed4_layers) > 1 else []
    candidate = select_readonly_candidate(chunked_values, packed0_values, document.chunked_binary_layer)
    return {
        "probe": "map_setting_layer_inspection",
        "input_path": str(input_path),
        "input_sha256": rt.sha256_bytes(input_data),
        "input_size": len(input_data),
        "bundle_path": str(bundle_path) if bundle_path else None,
        "output_dir": str(output_dir),
        "layers": {
            "chunked_binary": {
                "shape": [chunked_width, chunked_height],
                "histogram": histogram(chunked_values),
                "bounding_boxes_by_value": bounding_boxes_by_value(chunked_values, chunked_width, chunked_height),
                "rotational_symmetry_mismatch_count": rotational_symmetry_mismatch_count(
                    chunked_values, chunked_width, chunked_height
                ),
                "transpose_mismatch_count": matrix_transpose_mismatch_count(chunked_values, chunked_width),
                "hypothesis": "symmetric 900x900 source-target binary relation, likely visibility or reachability; not a direct map texture",
            },
            "packed4_0": {
                "shape": [900, 900],
                "histogram": histogram(packed0_values),
                "bounding_boxes_by_value": bounding_boxes_by_value(packed0_values, 900, 900),
                "rotational_symmetry_mismatch_count": rotational_symmetry_mismatch_count(packed0_values, 900, 900),
                "transpose_mismatch_count": matrix_transpose_mismatch_count(packed0_values, 900),
                "hypothesis": "900x900 source-target next-hop or direction relation; not confirmed",
            },
            "packed4_1": {
                "shape_candidates": [[30, 30, 30], [900, 30]],
                "value_count": len(packed1_values),
                "histogram": histogram(packed1_values),
                "hypothesis": "unverified 27,000-value table; excluded from first mutation target selection",
            },
        },
        "candidate_mutation": candidate,
        "safety": {
            "read_only": True,
            "mutated_map_setting_generated": False,
            "game_install_modified": False,
            "outputs_inside_repository": rt.is_inside_repo(output_dir),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def inspect_map_setting(
    input_path: Path,
    output_dir: Path,
    bundle_path: Path | None = None,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    bundle_path = bundle_path.resolve() if bundle_path else None
    ensure_outside_repo(input_path, "input")
    ensure_outside_repo(output_dir, "output directory")
    output_dir.mkdir(parents=True, exist_ok=True)

    data = input_path.read_bytes()
    if expected_sha256 and rt.sha256_bytes(data).lower() != expected_sha256.lower():
        raise SystemExit(f"Input SHA-256 {rt.sha256_bytes(data)} does not match expected {expected_sha256}.")
    document = rt.decode_map_setting(data)
    if len(document.packed4_layers) < 2:
        raise SystemExit("Expected at least two packed4 layers for current map_setting inspection.")

    chunked_values, chunked_width, chunked_height = flatten_chunked_binary_layer(document.chunked_binary_layer)
    packed0_values = unpack_packed4_layer(document.packed4_layers[0])
    packed1_values = unpack_packed4_layer(document.packed4_layers[1])

    write_png_l(chunked_values, chunked_width, chunked_height, output_dir / "chunked_binary_values.png", max_value=1)
    write_png_l(packed0_values, 900, 900, output_dir / "packed4_0_values.png", max_value=15)
    for value in range(16):
        write_mask(packed0_values, 900, 900, value, output_dir / f"packed4_0_value_{value}_mask.png")
    slice_outputs = write_packed4_1_slices(packed1_values, output_dir / "packed4_1_slices")

    extracted_assets: dict[str, Any] = {}
    overlays: dict[str, Any] = {}
    if bundle_path:
        for name, key in DEFAULT_ASSET_KEYS.items():
            try:
                asset_type, asset_data = read_bundle_entry(bundle_path, key)
            except KeyError:
                extracted_assets[name] = {"asset_key": key, "missing": True}
                continue
            asset_path = output_dir / "original_assets" / f"{name}.png"
            asset_info = extract_png(asset_path, asset_data)
            asset_info["asset_key"] = key
            asset_info["asset_type"] = asset_type
            extracted_assets[name] = asset_info
            overlays[f"{name}_chunked_binary"] = overlay_values_on_png(
                chunked_values,
                chunked_width,
                chunked_height,
                asset_path,
                output_dir / "overlays" / f"{name}_chunked_binary_overlay.png",
                max_value=1,
            )
            overlays[f"{name}_packed4_0"] = overlay_values_on_png(
                packed0_values,
                900,
                900,
                asset_path,
                output_dir / "overlays" / f"{name}_packed4_0_overlay.png",
                max_value=15,
            )

    manifest = build_manifest(input_path, data, document, output_dir, bundle_path)
    manifest["outputs"] = {
        "chunked_binary_values": str(output_dir / "chunked_binary_values.png"),
        "packed4_0_values": str(output_dir / "packed4_0_values.png"),
        "packed4_0_value_masks": [str(output_dir / f"packed4_0_value_{value}_mask.png") for value in range(16)],
        "packed4_1_slices": slice_outputs,
        "original_assets": extracted_assets,
        "overlays": overlays,
    }
    manifest_path = output_dir / "layer_inspection_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    candidate = manifest["candidate_mutation"]
    return {
        "probe": manifest["probe"],
        "input_sha256": manifest["input_sha256"],
        "output_dir": manifest["output_dir"],
        "manifest_path": str(Path(manifest["output_dir"]) / "layer_inspection_manifest.json"),
        "chunked_binary_shape": manifest["layers"]["chunked_binary"]["shape"],
        "packed4_0_shape": manifest["layers"]["packed4_0"]["shape"],
        "packed4_1_value_count": manifest["layers"]["packed4_1"]["value_count"],
        "candidate_status": candidate.get("status"),
        "candidate_layer": candidate.get("layer"),
        "candidate_logical_coordinate": candidate.get("logical_coordinate"),
        "read_only": manifest["safety"]["read_only"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate read-only map_setting layer diagnostics outside the repository.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Repository-external output directory.")
    parser.add_argument("--bundle", type=Path, default=None, help="Optional local bundle.game_data for original map overlays.")
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true", help="Print the full manifest JSON instead of a compact summary.")
    args = parser.parse_args()

    manifest = inspect_map_setting(
        input_path=args.input,
        output_dir=args.output_dir,
        bundle_path=args.bundle,
        expected_sha256=args.expected_sha256 or None,
    )
    payload = manifest if args.print_manifest else stdout_summary(manifest)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
