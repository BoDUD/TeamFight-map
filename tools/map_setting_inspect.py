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

from tools import map_setting_round_trip as rt  # noqa: E402

DEFAULT_ASSET_KEYS = {
    "background_5v5": "asset/base/aseprite_resources/ingame/5v5/background_5v5",
    "wall_5v5": "asset/base/aseprite_resources/ingame/5v5/wall_5v5",
    "wall_5v5_front": "asset/base/aseprite_resources/ingame/5v5/wall_5v5_front",
    "bush_5v5": "asset/base/aseprite_resources/ingame/5v5/bush_5v5",
    "minimap_5v5_bg": "asset/base/aseprite_resources/ingame/5v5/minimap_5v5_bg",
}
DEFAULT_LAYOUT_PATH = REPO_ROOT / "data" / "map" / "tfm2_lol_like_map.json"
LOGICAL_GRID_SIZE = 30
MATRIX_SIZE = LOGICAL_GRID_SIZE * LOGICAL_GRID_SIZE
MIN_LANE_CLEARANCE_FOR_EDGE_CANDIDATE = 12.0


def ensure_outside_repo(path: Path, label: str) -> None:
    if rt.is_inside_repo(path):
        raise SystemExit(f"Refusing to write repository-internal {label}: {path}")


def paths_are_same_existing_file(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    try:
        return left.samefile(right)
    except OSError:
        return False


def ensure_source_outside_output_tree(source_path: Path, output_dir: Path, label: str) -> None:
    if source_path == output_dir or output_dir in source_path.parents:
        raise SystemExit(f"Refusing to inspect with {label} inside the output directory: {source_path}")
    if paths_are_same_existing_file(source_path, output_dir):
        raise SystemExit(f"Refusing to inspect with {label} aliased to the output directory: {source_path}")


def planned_output_paths(output_dir: Path) -> list[Path]:
    paths = [
        output_dir / "chunked_binary_values.png",
        output_dir / "packed4_0_values.png",
        output_dir / "candidate_nodes_on_minimap.png",
        output_dir / "candidate_clearance_manifest.json",
        output_dir / "layer_inspection_manifest.json",
    ]
    paths.extend(output_dir / f"packed4_0_value_{value}_mask.png" for value in range(16))
    paths.extend(output_dir / "packed4_1_slices" / f"packed4_1_slice_{slice_index:02d}.png" for slice_index in range(30))
    paths.extend(output_dir / f"source_{node}_relation_mask_30x30.png" for node in range(MATRIX_SIZE))
    paths.extend(output_dir / f"target_{node}_relation_mask_30x30.png" for node in range(MATRIX_SIZE))
    for name in DEFAULT_ASSET_KEYS:
        paths.append(output_dir / "original_assets" / f"{name}.png")
        paths.append(output_dir / "overlays" / f"{name}_chunked_binary_overlay.png")
        paths.append(output_dir / "overlays" / f"{name}_packed4_0_overlay.png")
    return paths


def ensure_no_source_output_conflicts(
    input_path: Path,
    bundle_path: Path | None,
    output_dir: Path,
    layout_path: Path | None = None,
) -> None:
    ensure_source_outside_output_tree(input_path, output_dir, "input")
    if bundle_path:
        ensure_source_outside_output_tree(bundle_path, output_dir, "bundle")
    if layout_path:
        ensure_source_outside_output_tree(layout_path, output_dir, "layout")
    sources = {"input": input_path}
    if bundle_path:
        sources["bundle"] = bundle_path
    if layout_path:
        sources["layout"] = layout_path
    for output_path in planned_output_paths(output_dir):
        for label, source_path in sources.items():
            if output_path == source_path or paths_are_same_existing_file(output_path, source_path):
                raise SystemExit(
                    f"Refusing to overwrite {label} through generated output path: {output_path}"
                )


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


def packed4_shape(layer: rt.Packed4Layer) -> tuple[int, int]:
    if layer.cell_count == MATRIX_SIZE * MATRIX_SIZE:
        return MATRIX_SIZE, MATRIX_SIZE
    side = math.isqrt(layer.cell_count)
    if side * side == layer.cell_count:
        return side, side
    return int(layer.cell_count), 1


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


def load_layout(layout_path: Path | None) -> dict[str, Any] | None:
    if not layout_path:
        return None
    return json.loads(layout_path.read_text(encoding="utf-8"))


def node_to_world(node: int, logical_size: int = LOGICAL_GRID_SIZE) -> list[float]:
    return [
        ((node % logical_size) + 0.5) * 100 / logical_size,
        ((node // logical_size) + 0.5) * 100 / logical_size,
    ]


def point_distance(left: list[float] | tuple[float, float], right: list[float] | tuple[float, float]) -> float:
    return math.hypot(left[0] - right[0], left[1] - right[1])


def distance_to_segment(
    point: list[float] | tuple[float, float],
    start: list[float] | tuple[float, float],
    end: list[float] | tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 0 and dy == 0:
        return point_distance(point, start)
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    projected = [start[0] + t * dx, start[1] + t * dy]
    return point_distance(point, projected)


def layout_feature_points(layout: dict[str, Any]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for key, anchor in layout.get("anchors", {}).items():
        if "center" in anchor:
            points.append({"id": key, "kind": "anchor", "center": anchor["center"]})
    for collection_name, kind in (
        ("towers", "tower"),
        ("objectives", "objective"),
        ("functional_brush", "brush"),
        ("gates", "gate"),
    ):
        for item in layout.get(collection_name, []):
            if "center" in item:
                points.append({"id": item["id"], "kind": kind, "center": item["center"]})
    for camp in layout.get("jungle", {}).get("camps", []):
        points.append({"id": camp["id"], "kind": "camp", "center": camp["center"]})
    return points


def layout_feature_lines(layout: dict[str, Any]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for lane in layout.get("lanes", []):
        points = lane.get("centerline", [])
        for index in range(len(points) - 1):
            lines.append({"id": lane["id"], "kind": "lane", "start": points[index], "end": points[index + 1]})
    for half in layout.get("jungle", {}).get("half_jungles", []):
        points = half.get("main_loop", [])
        for index in range(len(points) - 1):
            lines.append({"id": half["id"], "kind": "jungle_loop", "start": points[index], "end": points[index + 1]})
    return lines


def nearest_layout_feature(point: list[float], layout: dict[str, Any]) -> dict[str, Any]:
    nearest: dict[str, Any] | None = None
    for feature in layout_feature_points(layout):
        distance = point_distance(point, feature["center"])
        if nearest is None or distance < nearest["distance"]:
            nearest = {
                "kind": feature["kind"],
                "id": feature["id"],
                "distance": distance,
            }
    for feature in layout_feature_lines(layout):
        distance = distance_to_segment(point, feature["start"], feature["end"])
        if nearest is None or distance < nearest["distance"]:
            nearest = {
                "kind": feature["kind"],
                "id": feature["id"],
                "distance": distance,
            }
    assert nearest is not None
    nearest["distance"] = round(nearest["distance"], 3)
    return nearest


def lane_clearance(point: list[float], layout: dict[str, Any]) -> float:
    distances = [
        distance_to_segment(point, feature["start"], feature["end"])
        for feature in layout_feature_lines(layout)
        if feature["kind"] == "lane"
    ]
    return round(min(distances), 3) if distances else 0.0


def edge_clearance_score(source_node: int, target_node: int, layout: dict[str, Any]) -> dict[str, Any]:
    source_world = node_to_world(source_node)
    target_world = node_to_world(target_node)
    source_nearest = nearest_layout_feature(source_world, layout)
    target_nearest = nearest_layout_feature(target_world, layout)
    return {
        "source_world": source_world,
        "target_world": target_world,
        "source_nearest_feature": source_nearest,
        "target_nearest_feature": target_nearest,
        "source_lane_clearance": lane_clearance(source_world, layout),
        "target_lane_clearance": lane_clearance(target_world, layout),
        "minimum_feature_clearance": round(min(source_nearest["distance"], target_nearest["distance"]), 3),
        "minimum_lane_clearance": round(
            min(lane_clearance(source_world, layout), lane_clearance(target_world, layout)), 3
        ),
    }


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


def write_source_relation_mask(values: list[int], matrix_width: int, source_node: int, path: Path) -> dict[str, Any]:
    if matrix_width != MATRIX_SIZE:
        return {"path": str(path), "skipped": True, "reason": "source relation masks require a 900x900 matrix"}
    row = values[source_node * matrix_width : (source_node + 1) * matrix_width]
    write_png_l(row, LOGICAL_GRID_SIZE, LOGICAL_GRID_SIZE, path, max_value=1)
    return {"path": str(path), "sha256": rt.sha256_file(path)}


def write_target_relation_mask(values: list[int], matrix_width: int, target_node: int, path: Path) -> dict[str, Any]:
    if matrix_width != MATRIX_SIZE:
        return {"path": str(path), "skipped": True, "reason": "target relation masks require a 900x900 matrix"}
    column = [values[source_node * matrix_width + target_node] for source_node in range(MATRIX_SIZE)]
    write_png_l(column, LOGICAL_GRID_SIZE, LOGICAL_GRID_SIZE, path, max_value=1)
    return {"path": str(path), "sha256": rt.sha256_file(path)}


def to_canvas_point(point: list[float], size: int) -> tuple[int, int]:
    return (round(point[0] * (size - 1) / 100), round(point[1] * (size - 1) / 100))


def write_candidate_nodes_on_minimap(
    candidate: dict[str, Any],
    layout: dict[str, Any] | None,
    path: Path,
    base_minimap: Path | None = None,
) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    if candidate.get("candidate_unit") != "undirected_edge" or not layout:
        return {"path": str(path), "skipped": True, "reason": "no edge candidate with layout clearance data"}
    if base_minimap and base_minimap.exists():
        image = Image.open(base_minimap).convert("RGBA")
    else:
        image = Image.new("RGBA", (320, 320), (32, 34, 43, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    size = image.size[0]

    for lane in layout.get("lanes", []):
        points = [to_canvas_point(point, size) for point in lane.get("centerline", [])]
        if len(points) > 1:
            draw.line(points, fill=(255, 230, 96, 180), width=max(1, size // 120))
    for tower in layout.get("towers", []):
        x, y = to_canvas_point(tower["center"], size)
        draw.rectangle((x - 2, y - 2, x + 2, y + 2), fill=(90, 180, 255, 220))
    for objective in layout.get("objectives", []):
        x, y = to_canvas_point(objective["center"], size)
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(255, 96, 96, 230), width=2)
    for camp in layout.get("jungle", {}).get("camps", []):
        x, y = to_canvas_point(camp["center"], size)
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 160, 64, 220))
    for brush in layout.get("functional_brush", []):
        x, y = to_canvas_point(brush["center"], size)
        draw.rectangle((x - 2, y - 2, x + 2, y + 2), outline=(72, 220, 120, 220), width=1)

    source = candidate["edge"]["source_world"]
    target = candidate["edge"]["target_world"]
    source_point = to_canvas_point(source, size)
    target_point = to_canvas_point(target, size)
    draw.line([source_point, target_point], fill=(255, 255, 255, 255), width=max(2, size // 80))
    for point, color in ((source_point, (0, 220, 255, 255)), (target_point, (255, 80, 220, 255))):
        radius = max(4, size // 50)
        draw.ellipse(
            (point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius),
            fill=color,
            outline=(255, 255, 255, 255),
            width=2,
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return {"path": str(path), "size": list(image.size), "sha256": rt.sha256_file(path)}


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
    layout: dict[str, Any] | None,
) -> dict[str, Any]:
    width = MATRIX_SIZE
    if len(chunked_values) != MATRIX_SIZE * MATRIX_SIZE:
        return {
            "status": "not_selected",
            "reason": "edge candidate selection requires a 900x900 chunked relation matrix",
        }
    if not layout:
        return {
            "status": "needs_world_grid_validation",
            "reason": "layout clearance data is required before selecting a mutation edge candidate",
        }

    transpose_before = matrix_transpose_mismatch_count(chunked_values, width)
    candidates: list[dict[str, Any]] = []
    for source_y in range(LOGICAL_GRID_SIZE):
        for source_x in range(LOGICAL_GRID_SIZE):
            source_node = source_y * LOGICAL_GRID_SIZE + source_x
            for dx, dy in ((1, 0), (0, 1)):
                target_x = source_x + dx
                target_y = source_y + dy
                if target_x >= LOGICAL_GRID_SIZE or target_y >= LOGICAL_GRID_SIZE:
                    continue
                target_node = target_y * LOGICAL_GRID_SIZE + target_x
                forward_index = source_node * width + target_node
                reverse_index = target_node * width + source_node
                if chunked_values[forward_index] != 1 or chunked_values[reverse_index] != 1:
                    continue
                clearance = edge_clearance_score(source_node, target_node, layout)
                if clearance["minimum_lane_clearance"] < MIN_LANE_CLEARANCE_FOR_EDGE_CANDIDATE:
                    continue
                candidates.append(
                    {
                        "source_node": source_node,
                        "target_node": target_node,
                        "clearance": clearance,
                    }
                )

    if not candidates:
        return {
            "status": "not_selected",
            "reason": "No adjacent symmetric edge met the current design-clearance threshold.",
            "transpose_mismatch_count_before": transpose_before,
        }

    candidates.sort(
        key=lambda item: (
            -item["clearance"]["minimum_feature_clearance"],
            -item["clearance"]["minimum_lane_clearance"],
            item["source_node"],
            item["target_node"],
        )
    )
    chosen = candidates[0]
    source_node = chosen["source_node"]
    target_node = chosen["target_node"]
    forward_index = source_node * width + target_node
    reverse_index = target_node * width + source_node
    mutated_values = list(chunked_values)
    mutated_values[forward_index] = 0
    mutated_values[reverse_index] = 0
    cells = [
        {
            "logical_coordinate": [target_node, source_node],
            "source_node": source_node,
            "target_node": target_node,
            "source_xy_30x30": [source_node % LOGICAL_GRID_SIZE, source_node // LOGICAL_GRID_SIZE],
            "target_xy_30x30": [target_node % LOGICAL_GRID_SIZE, target_node // LOGICAL_GRID_SIZE],
            "serialized_byte_offset": chunked_cell_offset(chunked_layer, target_node, source_node),
            "old_value": chunked_values[forward_index],
            "new_value": 0,
            "packed4_0_context_value": packed0_values[forward_index] if len(packed0_values) > forward_index else None,
        },
        {
            "logical_coordinate": [source_node, target_node],
            "source_node": target_node,
            "target_node": source_node,
            "source_xy_30x30": [target_node % LOGICAL_GRID_SIZE, target_node // LOGICAL_GRID_SIZE],
            "target_xy_30x30": [source_node % LOGICAL_GRID_SIZE, source_node // LOGICAL_GRID_SIZE],
            "serialized_byte_offset": chunked_cell_offset(chunked_layer, source_node, target_node),
            "old_value": chunked_values[reverse_index],
            "new_value": 0,
            "packed4_0_context_value": packed0_values[reverse_index] if len(packed0_values) > reverse_index else None,
        },
    ]
    return {
        "status": "needs_world_grid_validation",
        "candidate_unit": "undirected_edge",
        "layer": "chunked_binary",
        "hypothesis": "pairwise visibility or reachability bit between 30x30 logical cells; not confirmed",
        "selection_reason": (
            "The chunked layer has a 900x900 matrix shape, binary values, and transpose_mismatch_count == 0. "
            "The candidate is therefore a symmetric undirected edge, not a single cell, so a follow-up mutation can preserve "
            "the observed transpose-symmetry invariant."
        ),
        "edge": {
            "source_node": source_node,
            "target_node": target_node,
            "source_xy_30x30": [source_node % LOGICAL_GRID_SIZE, source_node // LOGICAL_GRID_SIZE],
            "target_xy_30x30": [target_node % LOGICAL_GRID_SIZE, target_node // LOGICAL_GRID_SIZE],
            "source_world": chosen["clearance"]["source_world"],
            "target_world": chosen["clearance"]["target_world"],
        },
        "cells": cells,
        "old_value": 1,
        "new_value": 0,
        "changed_cell_count": 2,
        "changed_byte_count": 2,
        "transpose_mismatch_count_before": transpose_before,
        "transpose_mismatch_count_after_if_applied": matrix_transpose_mismatch_count(mutated_values, width),
        "clearance": chosen["clearance"],
        "risk_classification": "unverified",
        "risk_reason": (
            "Design-space clearance can be measured, but the original map_setting world/grid transform is not yet proven. "
            "This candidate must not move to runtime mutation until that transform is validated or manually accepted."
        ),
        "predicted_effect": "hypothesis: one symmetric source-target relation edge is removed; local gameplay effect is unknown",
        "prediction_confidence": "hypothesis",
        "rollback_source_sha256": rt.MAP_SETTING_SHA256,
        "do_not_mutate_in_this_pr": True,
    }


def build_manifest(
    input_path: Path,
    input_data: bytes,
    document: rt.MapSettingDocument,
    output_dir: Path,
    bundle_path: Path | None,
    layout_path: Path | None,
    layout: dict[str, Any] | None,
) -> dict[str, Any]:
    chunked_values, chunked_width, chunked_height = flatten_chunked_binary_layer(document.chunked_binary_layer)
    packed0_values = unpack_packed4_layer(document.packed4_layers[0])
    packed0_width, packed0_height = packed4_shape(document.packed4_layers[0])
    packed1_values = unpack_packed4_layer(document.packed4_layers[1]) if len(document.packed4_layers) > 1 else []
    candidate = select_readonly_candidate(chunked_values, packed0_values, document.chunked_binary_layer, layout)
    return {
        "probe": "map_setting_layer_inspection",
        "input_path": str(input_path),
        "input_sha256": rt.sha256_bytes(input_data),
        "input_size": len(input_data),
        "bundle_path": str(bundle_path) if bundle_path else None,
        "layout_path": str(layout_path) if layout_path else None,
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
                "shape": [packed0_width, packed0_height],
                "histogram": histogram(packed0_values),
                "bounding_boxes_by_value": bounding_boxes_by_value(packed0_values, packed0_width, packed0_height),
                "rotational_symmetry_mismatch_count": rotational_symmetry_mismatch_count(
                    packed0_values, packed0_width, packed0_height
                ),
                "transpose_mismatch_count": (
                    matrix_transpose_mismatch_count(packed0_values, packed0_width)
                    if packed0_width == packed0_height
                    else None
                ),
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
        "candidate_clearance": {
            "status": candidate.get("status"),
            "risk_classification": candidate.get("risk_classification", "unverified"),
            "transform": {
                "assumption": "30x30 node centers mapped linearly to normalized design coordinates",
                "status": "unverified",
                "requires": "Validate against original map_setting world/grid anchors before runtime mutation.",
            },
            "clearance": candidate.get("clearance"),
        },
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
    layout_path: Path | None = DEFAULT_LAYOUT_PATH,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    bundle_path = bundle_path.resolve() if bundle_path else None
    layout_path = layout_path.resolve() if layout_path else None
    ensure_outside_repo(input_path, "input")
    ensure_outside_repo(output_dir, "output directory")
    if bundle_path:
        ensure_outside_repo(bundle_path, "bundle")
    ensure_no_source_output_conflicts(input_path, bundle_path, output_dir, layout_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = input_path.read_bytes()
    if expected_sha256 and rt.sha256_bytes(data).lower() != expected_sha256.lower():
        raise SystemExit(f"Input SHA-256 {rt.sha256_bytes(data)} does not match expected {expected_sha256}.")
    document = rt.decode_map_setting(data)
    if len(document.packed4_layers) < 2:
        raise SystemExit("Expected at least two packed4 layers for current map_setting inspection.")

    chunked_values, chunked_width, chunked_height = flatten_chunked_binary_layer(document.chunked_binary_layer)
    packed0_values = unpack_packed4_layer(document.packed4_layers[0])
    packed0_width, packed0_height = packed4_shape(document.packed4_layers[0])
    packed1_values = unpack_packed4_layer(document.packed4_layers[1])
    layout = load_layout(layout_path)

    write_png_l(chunked_values, chunked_width, chunked_height, output_dir / "chunked_binary_values.png", max_value=1)
    write_png_l(packed0_values, packed0_width, packed0_height, output_dir / "packed4_0_values.png", max_value=15)
    for value in range(16):
        write_mask(packed0_values, packed0_width, packed0_height, value, output_dir / f"packed4_0_value_{value}_mask.png")
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
                packed0_width,
                packed0_height,
                asset_path,
                output_dir / "overlays" / f"{name}_packed4_0_overlay.png",
                max_value=15,
            )

    manifest = build_manifest(input_path, data, document, output_dir, bundle_path, layout_path, layout)
    candidate = manifest["candidate_mutation"]
    source_mask = None
    target_mask = None
    candidate_map = None
    if candidate.get("candidate_unit") == "undirected_edge":
        source_node = candidate["edge"]["source_node"]
        target_node = candidate["edge"]["target_node"]
        source_mask = write_source_relation_mask(
            chunked_values,
            chunked_width,
            source_node,
            output_dir / f"source_{source_node}_relation_mask_30x30.png",
        )
        target_mask = write_target_relation_mask(
            chunked_values,
            chunked_width,
            target_node,
            output_dir / f"target_{target_node}_relation_mask_30x30.png",
        )
        minimap_asset = output_dir / "original_assets" / "minimap_5v5_bg.png"
        candidate_map = write_candidate_nodes_on_minimap(
            candidate,
            layout,
            output_dir / "candidate_nodes_on_minimap.png",
            base_minimap=minimap_asset if minimap_asset.exists() else None,
        )
    clearance_manifest_path = output_dir / "candidate_clearance_manifest.json"
    clearance_manifest_path.write_text(
        json.dumps(manifest["candidate_clearance"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest["outputs"] = {
        "chunked_binary_values": str(output_dir / "chunked_binary_values.png"),
        "packed4_0_values": str(output_dir / "packed4_0_values.png"),
        "packed4_0_value_masks": [str(output_dir / f"packed4_0_value_{value}_mask.png") for value in range(16)],
        "packed4_1_slices": slice_outputs,
        "candidate_nodes_on_minimap": candidate_map,
        "source_relation_mask_30x30": source_mask,
        "target_relation_mask_30x30": target_mask,
        "candidate_clearance_manifest": str(clearance_manifest_path),
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
        "candidate_unit": candidate.get("candidate_unit"),
        "candidate_edge": candidate.get("edge"),
        "risk_classification": candidate.get("risk_classification"),
        "read_only": manifest["safety"]["read_only"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate read-only map_setting layer diagnostics outside the repository.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Repository-external output directory.")
    parser.add_argument("--bundle", type=Path, default=None, help="Optional local bundle.game_data for original map overlays.")
    parser.add_argument(
        "--layout",
        type=Path,
        default=DEFAULT_LAYOUT_PATH,
        help="Optional design layout used only for unverified 30x30 clearance diagnostics.",
    )
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true", help="Print the full manifest JSON instead of a compact summary.")
    args = parser.parse_args()

    manifest = inspect_map_setting(
        input_path=args.input,
        output_dir=args.output_dir,
        bundle_path=args.bundle,
        layout_path=args.layout,
        expected_sha256=args.expected_sha256 or None,
    )
    payload = manifest if args.print_manifest else stdout_summary(manifest)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
