from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402

LOGICAL_GRID_SIZE = 30
MATRIX_SIZE = LOGICAL_GRID_SIZE * LOGICAL_GRID_SIZE
CANDIDATE_EDGE = (369, 370)
TRANSFORMS = (
    "identity",
    "rotate90",
    "rotate180",
    "rotate270",
    "flip_x",
    "flip_y",
    "transpose",
    "anti_transpose",
)
RESOURCE_KEYS = {
    "wall_5v5": "asset/base/aseprite_resources/ingame/5v5/wall_5v5",
    "wall_5v5_front": "asset/base/aseprite_resources/ingame/5v5/wall_5v5_front",
    "minimap_5v5_bg": "asset/base/aseprite_resources/ingame/5v5/minimap_5v5_bg",
}


def planned_output_paths(output_dir: Path) -> list[Path]:
    paths = [
        output_dir / "semantic_validation_manifest.json",
        output_dir / "chunked_packed4_contingency.json",
        output_dir / "candidate_rotation180.json",
        output_dir / "direction_code_mapping.json",
        output_dir / "transform_scores.json",
        output_dir / "best_transform_overlay.png",
        output_dir / "runtime_grid_probe.png",
        output_dir / "runtime_anchor_measurements.json",
        output_dir / "candidate_decision.json",
    ]
    for transform in TRANSFORMS:
        paths.append(output_dir / f"blocked_edge_overlay_{transform}.png")
        paths.append(output_dir / f"open_edge_overlay_{transform}.png")
    for name in RESOURCE_KEYS:
        paths.append(output_dir / "original_assets" / f"{name}.png")
    return paths


def ensure_no_output_conflicts(
    input_path: Path,
    output_dir: Path,
    bundle_path: Path | None = None,
    layout_path: Path | None = None,
) -> None:
    inspect.ensure_outside_repo(input_path, "input")
    inspect.ensure_outside_repo(output_dir, "output directory")
    inspect.ensure_source_outside_output_tree(input_path, output_dir, "input")
    sources = {"input": input_path}
    if bundle_path:
        inspect.ensure_outside_repo(bundle_path, "bundle")
        inspect.ensure_source_outside_output_tree(bundle_path, output_dir, "bundle")
        sources["bundle"] = bundle_path
    if layout_path:
        inspect.ensure_source_outside_output_tree(layout_path, output_dir, "layout")
        sources["layout"] = layout_path
    for output_path in planned_output_paths(output_dir):
        for label, source in sources.items():
            if output_path == source or inspect.paths_are_same_existing_file(output_path, source):
                raise SystemExit(f"Refusing to overwrite {label} through generated output path: {output_path}")


def matrix_rows(values: list[int], size: int) -> list[bytes]:
    return [bytes(values[row * size : (row + 1) * size]) for row in range(size)]


def row_sum_histogram(values: list[int], size: int) -> dict[str, int]:
    counts = Counter(sum(values[row * size : (row + 1) * size]) for row in range(size))
    return {str(key): counts[key] for key in sorted(counts)}


def rotation180_relation_mismatch_count(values: list[int], size: int = MATRIX_SIZE) -> int:
    mismatch_count = 0
    for source in range(size):
        rotated_source = size - 1 - source
        for target in range(size):
            rotated_target = size - 1 - target
            if values[source * size + target] != values[rotated_source * size + rotated_target]:
                mismatch_count += 1
    return mismatch_count


def chunked_invariants(values: list[int], size: int = MATRIX_SIZE) -> dict[str, Any]:
    rows = matrix_rows(values, size)
    diagonal = [values[index * size + index] for index in range(size)]
    rotation180_mismatch_count = rotation180_relation_mismatch_count(values, size)
    connected_pair_count = 0
    signature_mismatch_count = 0
    transitivity_violation_count = 0
    for source in range(size):
        source_row = rows[source]
        for target, is_connected in enumerate(source_row):
            if source == target or is_connected != 1:
                continue
            connected_pair_count += 1
            target_row = rows[target]
            if source_row != target_row:
                signature_mismatch_count += 1
                transitivity_violation_count += sum(
                    1 for left, right in zip(source_row, target_row) if left != right
                )
    mismatch_ratio = signature_mismatch_count / connected_pair_count if connected_pair_count else 0.0
    closure_like = connected_pair_count > 0 and signature_mismatch_count == 0
    return {
        "diagonal_0_count": diagonal.count(0),
        "diagonal_1_count": diagonal.count(1),
        "transpose_mismatch_count": inspect.matrix_transpose_mismatch_count(values, size),
        "rotation180_relation_mismatch_count": rotation180_mismatch_count,
        "rotation180_relation_symmetric": rotation180_mismatch_count == 0,
        "row_sum_histogram": row_sum_histogram(values, size),
        "unique_row_count": len(set(rows)),
        "connected_pair_count": connected_pair_count,
        "connected_pair_row_signature_mismatch_count": signature_mismatch_count,
        "connected_pair_row_signature_mismatch_ratio": round(mismatch_ratio, 6),
        "transitivity_violation_count": transitivity_violation_count,
        "closure_like": closure_like,
        "interpretation": (
            "connected_component_or_reachability_closure"
            if closure_like
            else "pairwise_relation_or_non_transitive_visibility_candidate"
        ),
    }


def contingency_table(chunked: list[int], packed: list[int]) -> dict[str, Any]:
    table = {str(chunk_value): {str(code): 0 for code in range(16)} for chunk_value in (0, 1)}
    for chunk_value, code in zip(chunked, packed):
        table[str(chunk_value)][str(code)] += 1
    chunk0_total = sum(table["0"].values())
    packed15_total = table["0"]["15"] + table["1"]["15"]
    p_packed15_given_chunk0 = table["0"]["15"] / chunk0_total if chunk0_total else 0.0
    p_chunk0_given_packed15 = table["0"]["15"] / packed15_total if packed15_total else 0.0
    return {
        "table": table,
        "probabilities": {
            "p_packed4_0_eq_15_given_chunked_binary_eq_0": round(p_packed15_given_chunk0, 6),
            "p_chunked_binary_eq_0_given_packed4_0_eq_15": round(p_chunk0_given_packed15, 6),
        },
        "sentinel_hypothesis": {
            "packed4_0_15_strongly_implies_chunked_0": p_chunk0_given_packed15 >= 0.95,
            "chunked_0_strongly_implies_packed4_0_15": p_packed15_given_chunk0 >= 0.95,
        },
    }


def candidate_cross_layer_record(
    chunked: list[int],
    packed: list[int],
    contingency: dict[str, Any],
    size: int = MATRIX_SIZE,
    edge: tuple[int, int] = CANDIDATE_EDGE,
) -> dict[str, Any]:
    source, target = edge
    forward_index = source * size + target
    reverse_index = target * size + source
    packed_forward = packed[forward_index]
    packed_reverse = packed[reverse_index]
    strong_chunk0_requires_sentinel = contingency["sentinel_hypothesis"][
        "chunked_0_strongly_implies_packed4_0_15"
    ]
    would_conflict = strong_chunk0_requires_sentinel and (packed_forward != 15 or packed_reverse != 15)
    return {
        "edge": [source, target],
        "chunked_forward": chunked[forward_index],
        "chunked_reverse": chunked[reverse_index],
        "packed4_forward": packed_forward,
        "packed4_reverse": packed_reverse,
        "hypothetical_chunked_forward": 0,
        "hypothetical_chunked_reverse": 0,
        "cross_layer_consistency_after_hypothetical_edit": (
            "would_conflict_with_packed4_0_sentinel_hypothesis"
            if would_conflict
            else "no_packed4_0_conflict_detected_for_this_edge"
        ),
    }


def candidate_rotation180_record(
    chunked: list[int],
    size: int = MATRIX_SIZE,
    edge: tuple[int, int] = CANDIDATE_EDGE,
) -> dict[str, Any]:
    source, target = edge
    rotated_source = size - 1 - source
    rotated_target = size - 1 - target
    cells = [
        {
            "logical_coordinate": [source, target],
            "serialized_matrix_index": source * size + target,
            "value": chunked[source * size + target],
        },
        {
            "logical_coordinate": [target, source],
            "serialized_matrix_index": target * size + source,
            "value": chunked[target * size + source],
        },
        {
            "logical_coordinate": [rotated_source, rotated_target],
            "serialized_matrix_index": rotated_source * size + rotated_target,
            "value": chunked[rotated_source * size + rotated_target],
        },
        {
            "logical_coordinate": [rotated_target, rotated_source],
            "serialized_matrix_index": rotated_target * size + rotated_source,
            "value": chunked[rotated_target * size + rotated_source],
        },
    ]
    return {
        "edge": [source, target],
        "rotated_edge": [rotated_source, rotated_target],
        "cells": cells,
        "candidate_is_self_rotating": {tuple(cell["logical_coordinate"]) for cell in cells[:2]}
        == {tuple(cell["logical_coordinate"]) for cell in cells[2:]},
    }


def adjacent_direction_distributions(packed: list[int], logical_size: int = LOGICAL_GRID_SIZE) -> dict[str, Any]:
    matrix_size = logical_size * logical_size
    direction_names = {
        (-1, -1): "NW",
        (0, -1): "N",
        (1, -1): "NE",
        (-1, 0): "W",
        (1, 0): "E",
        (-1, 1): "SW",
        (0, 1): "S",
        (1, 1): "SE",
    }
    by_displacement: dict[str, Counter[int]] = defaultdict(Counter)
    by_code: dict[int, Counter[str]] = defaultdict(Counter)
    for source_y in range(logical_size):
        for source_x in range(logical_size):
            source = source_y * logical_size + source_x
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    target_x = source_x + dx
                    target_y = source_y + dy
                    if not (0 <= target_x < logical_size and 0 <= target_y < logical_size):
                        continue
                    target = target_y * logical_size + target_x
                    code = packed[source * matrix_size + target]
                    direction = direction_names[(dx, dy)]
                    by_displacement[f"{dx},{dy}:{direction}"][code] += 1
                    by_code[code][direction] += 1

    code_to_direction: dict[str, str] = {}
    purity_by_code: dict[str, float] = {}
    unresolved_codes: list[int] = []
    for code in sorted(by_code):
        total = sum(by_code[code].values())
        direction, count = by_code[code].most_common(1)[0]
        purity = count / total if total else 0.0
        code_to_direction[str(code)] = direction
        purity_by_code[str(code)] = round(purity, 6)
        if purity < 0.70:
            unresolved_codes.append(code)
    return {
        "displacement_to_code_distribution": {
            key: {str(code): counter[code] for code in sorted(counter)}
            for key, counter in sorted(by_displacement.items())
        },
        "code_to_direction": code_to_direction,
        "purity_by_code": purity_by_code,
        "unresolved_codes": unresolved_codes,
        "stability": "stable" if not unresolved_codes else "ambiguous",
    }


def adjacent_edges(chunked: list[int], size: int = LOGICAL_GRID_SIZE) -> list[dict[str, Any]]:
    matrix_size = size * size
    edges: list[dict[str, Any]] = []
    for source_y in range(size):
        for source_x in range(size):
            source = source_y * size + source_x
            for dx, dy, edge_kind in ((1, 0, "horizontal"), (0, 1, "vertical"), (1, 1, "diagonal"), (-1, 1, "diagonal")):
                target_x = source_x + dx
                target_y = source_y + dy
                if not (0 <= target_x < size and 0 <= target_y < size):
                    continue
                target = target_y * size + target_x
                forward = chunked[source * matrix_size + target]
                reverse = chunked[target * matrix_size + source]
                open_edge = forward == 1 and reverse == 1
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "source_xy": [source_x, source_y],
                        "target_xy": [target_x, target_y],
                        "kind": edge_kind,
                        "open": open_edge,
                    }
                )
    return edges


def passability_summary(edges: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    for edge in edges:
        by_kind[edge["kind"]]["open" if edge["open"] else "blocked"] += 1
    return {
        kind: {"open": counter["open"], "blocked": counter["blocked"]}
        for kind, counter in sorted(by_kind.items())
    }


def transform_unit_point(x: float, y: float, transform: str) -> tuple[float, float]:
    if transform == "identity":
        return x, y
    if transform == "rotate90":
        return 1 - y, x
    if transform == "rotate180":
        return 1 - x, 1 - y
    if transform == "rotate270":
        return y, 1 - x
    if transform == "flip_x":
        return 1 - x, y
    if transform == "flip_y":
        return x, 1 - y
    if transform == "transpose":
        return y, x
    if transform == "anti_transpose":
        return 1 - y, 1 - x
    raise ValueError(f"unknown transform: {transform}")


def node_unit_xy(node: int, logical_size: int = LOGICAL_GRID_SIZE) -> tuple[float, float]:
    return ((node % logical_size + 0.5) / logical_size, (node // logical_size + 0.5) / logical_size)


def node_pixel(node: int, transform: str, image_size: tuple[int, int]) -> tuple[int, int]:
    x, y = node_unit_xy(node)
    tx, ty = transform_unit_point(x, y, transform)
    return (
        max(0, min(image_size[0] - 1, round(tx * (image_size[0] - 1)))),
        max(0, min(image_size[1] - 1, round(ty * (image_size[1] - 1)))),
    )


def sample_points_between(start: tuple[int, int], end: tuple[int, int], steps: int = 5) -> list[tuple[int, int]]:
    points = []
    for index in range(steps):
        t = index / max(1, steps - 1)
        points.append((round(start[0] + (end[0] - start[0]) * t), round(start[1] + (end[1] - start[1]) * t)))
    return points


def sample_alpha(image, points: list[tuple[int, int]], radius: int = 1) -> float:
    width, height = image.size
    values: list[float] = []
    pixels = image.load()
    for x, y in points:
        for yy in range(max(0, y - radius), min(height, y + radius + 1)):
            for xx in range(max(0, x - radius), min(width, x + radius + 1)):
                values.append(pixels[xx, yy][3] / 255)
    return sum(values) / len(values) if values else 0.0


def sample_darkness(image, points: list[tuple[int, int]], radius: int = 1) -> float:
    width, height = image.size
    values: list[float] = []
    pixels = image.convert("RGB").load()
    for x, y in points:
        for yy in range(max(0, y - radius), min(height, y + radius + 1)):
            for xx in range(max(0, x - radius), min(width, x + radius + 1)):
                r, g, b = pixels[xx, yy]
                luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
                values.append(1 - luminance)
    return sum(values) / len(values) if values else 0.0


def extract_reference_assets(bundle_path: Path, output_dir: Path) -> dict[str, Any]:
    assets: dict[str, Any] = {}
    for name, key in RESOURCE_KEYS.items():
        asset_type, data = inspect.read_bundle_entry(bundle_path, key)
        asset_path = output_dir / "original_assets" / f"{name}.png"
        info = inspect.extract_png(asset_path, data)
        info["asset_key"] = key
        info["asset_type"] = asset_type
        assets[name] = info
    return assets


def load_wall_union(wall_path: Path, front_path: Path):
    from PIL import Image, ImageChops

    wall = Image.open(wall_path).convert("RGBA")
    front = Image.open(front_path).convert("RGBA").resize(wall.size)
    alpha = ImageChops.lighter(wall.getchannel("A"), front.getchannel("A"))
    union = Image.new("RGBA", wall.size, (0, 0, 0, 0))
    union.putalpha(alpha)
    return union


def score_transform(transform: str, edges: list[dict[str, Any]], wall_union, minimap) -> dict[str, Any]:
    blocked_wall: list[float] = []
    open_wall: list[float] = []
    blocked_minimap: list[float] = []
    open_minimap: list[float] = []
    for edge in edges:
        wall_start = node_pixel(edge["source"], transform, wall_union.size)
        wall_end = node_pixel(edge["target"], transform, wall_union.size)
        wall_points = sample_points_between(wall_start, wall_end)
        mini_start = node_pixel(edge["source"], transform, minimap.size)
        mini_end = node_pixel(edge["target"], transform, minimap.size)
        mini_points = sample_points_between(mini_start, mini_end)
        if edge["open"]:
            open_wall.append(sample_alpha(wall_union, wall_points, radius=2))
            open_minimap.append(sample_darkness(minimap, mini_points, radius=1))
        else:
            blocked_wall.append(sample_alpha(wall_union, wall_points, radius=2))
            blocked_minimap.append(sample_darkness(minimap, mini_points, radius=1))
    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0
    blocked_wall_mean = mean(blocked_wall)
    open_wall_mean = mean(open_wall)
    blocked_minimap_dark_mean = mean(blocked_minimap)
    open_minimap_dark_mean = mean(open_minimap)
    wall_separation = blocked_wall_mean - open_wall_mean
    minimap_separation = blocked_minimap_dark_mean - open_minimap_dark_mean
    score = wall_separation * 0.7 + minimap_separation * 0.3
    return {
        "transform": transform,
        "score": round(score, 6),
        "wall_blocked_mean": round(blocked_wall_mean, 6),
        "wall_open_mean": round(open_wall_mean, 6),
        "wall_separation": round(wall_separation, 6),
        "minimap_blocked_dark_mean": round(blocked_minimap_dark_mean, 6),
        "minimap_open_dark_mean": round(open_minimap_dark_mean, 6),
        "minimap_separation": round(minimap_separation, 6),
        "blocked_edge_count": len(blocked_wall),
        "open_edge_count": len(open_wall),
    }


def draw_edge_overlay(base_path: Path, edges: list[dict[str, Any]], transform: str, output_path: Path, mode: str) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    image = Image.open(base_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    color = (255, 64, 64, 180) if mode == "blocked" else (64, 230, 255, 130)
    for edge in edges:
        if mode == "blocked" and edge["open"]:
            continue
        if mode == "open" and not edge["open"]:
            continue
        start = node_pixel(edge["source"], transform, image.size)
        end = node_pixel(edge["target"], transform, image.size)
        draw.line([start, end], fill=color, width=1)
    result = Image.alpha_composite(image, overlay)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path)
    return {"path": str(output_path), "sha256": rt.sha256_file(output_path), "size": list(result.size)}


def draw_best_transform_overlay(base_path: Path, edges: list[dict[str, Any]], transform: str, output_path: Path) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    image = Image.open(base_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    for edge in edges:
        color = (80, 240, 255, 125) if edge["open"] else (255, 64, 64, 190)
        start = node_pixel(edge["source"], transform, image.size)
        end = node_pixel(edge["target"], transform, image.size)
        draw.line([start, end], fill=color, width=1)
    result = Image.alpha_composite(image, overlay)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path)
    return {"path": str(output_path), "sha256": rt.sha256_file(output_path), "size": list(result.size)}


def transform_scores(edges: list[dict[str, Any]], output_dir: Path, assets: dict[str, Any]) -> dict[str, Any]:
    from PIL import Image

    wall_union = load_wall_union(Path(assets["wall_5v5"]["path"]), Path(assets["wall_5v5_front"]["path"]))
    minimap_path = Path(assets["minimap_5v5_bg"]["path"])
    minimap = Image.open(minimap_path).convert("RGBA")
    scores = [score_transform(transform, edges, wall_union, minimap) for transform in TRANSFORMS]
    scores.sort(key=lambda item: item["score"], reverse=True)
    best = scores[0]
    second = scores[1] if len(scores) > 1 else None
    margin = best["score"] - second["score"] if second else 0.0
    conclusion = "single_best" if margin >= 0.05 else "ambiguous"
    overlays: dict[str, Any] = {}
    for transform in TRANSFORMS:
        overlays[f"blocked_{transform}"] = draw_edge_overlay(
            minimap_path,
            edges,
            transform,
            output_dir / f"blocked_edge_overlay_{transform}.png",
            "blocked",
        )
        overlays[f"open_{transform}"] = draw_edge_overlay(
            minimap_path,
            edges,
            transform,
            output_dir / f"open_edge_overlay_{transform}.png",
            "open",
        )
    best_overlay = draw_best_transform_overlay(
        minimap_path,
        edges,
        best["transform"],
        output_dir / "best_transform_overlay.png",
    )
    return {
        "scores": scores,
        "best_transform": best["transform"],
        "second_transform": second["transform"] if second else None,
        "score_margin": round(margin, 6),
        "conclusion": conclusion,
        "overlays": overlays,
        "best_transform_overlay": best_overlay,
        "scoring": {
            "reward": "blocked edges near wall alpha/dark minimap marks",
            "penalty": "open edges crossing wall alpha/dark minimap marks",
            "ambiguous_margin_threshold": 0.05,
        },
    }


def draw_runtime_grid_probe(output_path: Path, transform: str) -> dict[str, Any]:
    from PIL import Image, ImageDraw, ImageFont

    size = 1280
    image = Image.new("RGBA", (size, size), (18, 104, 112, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        small_font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    def draw_label(point: tuple[int, int], label: str, fill: tuple[int, int, int, int], used_font, dx: int = 18, dy: int = -10) -> None:
        bbox = draw.textbbox((0, 0), label, font=used_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = point[0] + dx
        y = point[1] + dy
        if x + text_width > size - 8:
            x = point[0] - text_width - 18
        if x < 8:
            x = point[0] + 18
        if x + text_width > size - 8:
            x = size - text_width - 8
        if x < 8:
            x = 8
        if y + text_height > size - 8:
            y = point[1] - text_height - 18
        if y < 8:
            y = point[1] + 18
        if y + text_height > size - 8:
            y = size - text_height - 8
        if y < 8:
            y = 8
        draw.rectangle(
            (x - 4, y - 3, x + text_width + 4, y + text_height + 3),
            fill=(18, 104, 112, 210),
        )
        draw.text((x, y), label, fill=fill, font=used_font)

    for index in range(LOGICAL_GRID_SIZE + 1):
        unit = index / LOGICAL_GRID_SIZE
        start_v = transform_unit_point(unit, 0, transform)
        end_v = transform_unit_point(unit, 1, transform)
        start_h = transform_unit_point(0, unit, transform)
        end_h = transform_unit_point(1, unit, transform)
        color = (255, 255, 255, 170) if index % 5 == 0 else (255, 255, 255, 80)
        width = 3 if index % 5 == 0 else 1
        draw.line(
            [
                (round(start_v[0] * (size - 1)), round(start_v[1] * (size - 1))),
                (round(end_v[0] * (size - 1)), round(end_v[1] * (size - 1))),
            ],
            fill=color,
            width=width,
        )
        draw.line(
            [
                (round(start_h[0] * (size - 1)), round(start_h[1] * (size - 1))),
                (round(end_h[0] * (size - 1)), round(end_h[1] * (size - 1))),
            ],
            fill=color,
            width=width,
        )

    origin = node_pixel(0, transform, (size, size))
    plus_x = node_pixel(4, transform, (size, size))
    plus_y = node_pixel(120, transform, (size, size))
    draw.line([origin, plus_x], fill=(80, 255, 120, 255), width=6)
    draw.line([origin, plus_y], fill=(80, 160, 255, 255), width=6)
    draw_label(plus_x, "+X", (80, 255, 120, 255), font, 12, -10)
    draw_label(plus_y, "+Y", (80, 160, 255, 255), font, 12, -10)

    corners = {
        "logical NW 0": (0, (255, 64, 64, 255)),
        "logical NE 29": (29, (80, 255, 120, 255)),
        "logical SW 870": (870, (80, 160, 255, 255)),
        "logical SE 899": (899, (255, 220, 80, 255)),
    }
    for label, (node, color) in corners.items():
        point = node_pixel(node, transform, (size, size))
        draw.ellipse((point[0] - 14, point[1] - 14, point[0] + 14, point[1] + 14), fill=color)
        draw_label(point, label, (255, 255, 255, 255), small_font)

    for node, label, color, label_offset in (
        (369, "node 369", (0, 255, 255, 255), (24, -36)),
        (370, "node 370", (255, 80, 220, 255), (24, 12)),
        (465, "center-ish 465", (255, 255, 255, 255), (22, -12)),
    ):
        point = node_pixel(node, transform, (size, size))
        radius = 18 if node in CANDIDATE_EDGE else 11
        draw.ellipse((point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius), fill=color)
        draw_label(point, label, (255, 255, 255, 255), font, label_offset[0], label_offset[1])
    draw.line(
        [node_pixel(CANDIDATE_EDGE[0], transform, (size, size)), node_pixel(CANDIDATE_EDGE[1], transform, (size, size))],
        fill=(255, 255, 255, 255),
        width=5,
    )
    draw.text((24, 24), f"TFM2 map_setting 30x30 grid probe - transform: {transform}", fill=(255, 255, 255, 255), font=font)
    draw.text((24, 54), "Only background_5v5 visual probe. No map_setting override.", fill=(255, 255, 255, 255), font=small_font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return {"path": str(output_path), "sha256": rt.sha256_file(output_path), "size": [size, size], "transform": transform}


def runtime_anchor_manifest(transform: str, output_path: Path) -> dict[str, Any]:
    anchors = {
        "logical_origin_node_0": node_pixel(0, transform, (1280, 1280)),
        "logical_x_max_node_29": node_pixel(29, transform, (1280, 1280)),
        "logical_y_max_node_870": node_pixel(870, transform, (1280, 1280)),
        "logical_corner_node_899": node_pixel(899, transform, (1280, 1280)),
        "candidate_node_369": node_pixel(369, transform, (1280, 1280)),
        "candidate_node_370": node_pixel(370, transform, (1280, 1280)),
    }
    manifest = {
        "status": "pending_manual_runtime_capture",
        "runtime_grid_probe": str(output_path),
        "expected_screenshot": "runtime_grid_probe_screenshot.png",
        "transform_used_for_probe": transform,
        "pixel_anchors_in_probe_image": {key: list(value) for key, value in anchors.items()},
        "manual_measurements_required": [
            "blue_base",
            "red_base",
            "map_center",
            "two_visible_towers_or_objectives",
            "candidate_edge_369_370_location",
        ],
        "map_setting_override_installed": False,
    }
    return manifest


def candidate_decision(
    invariants: dict[str, Any],
    candidate_cross_layer: dict[str, Any],
    direction_mapping: dict[str, Any],
    scores: dict[str, Any],
    candidate_rotation: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    remaining: list[str] = []
    if invariants["closure_like"]:
        blockers.append("chunked_binary behaves like a transitive reachability closure")
    if candidate_cross_layer["cross_layer_consistency_after_hypothetical_edit"].startswith("would_conflict"):
        blockers.append("hypothetical chunked edit conflicts with packed4_0 sentinel hypothesis")
    if invariants["rotation180_relation_symmetric"] and not candidate_rotation["candidate_is_self_rotating"]:
        blockers.append("chunked_binary also preserves 180-degree node rotation; candidate would require its rotated edge")
    if direction_mapping["stability"] != "stable":
        remaining.append("packed4_0 direction code mapping is ambiguous")
    if scores["conclusion"] != "single_best":
        remaining.append("offline wall/minimap transform scoring is ambiguous")
    remaining.append("independent runtime node/world anchor has not been captured")

    if blockers:
        status = "rejected"
    elif remaining:
        status = "pending_independent_node_anchor"
    else:
        status = "validated_for_mutation_pr"
    return {
        "candidate_edge": list(CANDIDATE_EDGE),
        "candidate_status": status,
        "may_enter_mutation_pr": status == "validated_for_mutation_pr",
        "blockers": blockers,
        "remaining_validation": remaining,
        "approved_mutation_scope_if_later_validated": {
            "layer": "chunked_binary",
            "changed_cell_count": 4 if blockers and any("180-degree" in item for item in blockers) else 2,
            "changed_byte_count": 4 if blockers and any("180-degree" in item for item in blockers) else 2,
            "preserve_transpose_symmetry": True,
            "preserve_rotation180_symmetry": invariants["rotation180_relation_symmetric"],
            "no_map_setting_mutation_in_this_pr": True,
        },
    }


def build_semantic_validation(
    input_path: Path,
    output_dir: Path,
    bundle_path: Path,
    layout_path: Path | None = inspect.DEFAULT_LAYOUT_PATH,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    bundle_path = bundle_path.resolve()
    layout_path = layout_path.resolve() if layout_path else None
    ensure_no_output_conflicts(input_path, output_dir, bundle_path, layout_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = input_path.read_bytes()
    if expected_sha256 and rt.sha256_bytes(data).lower() != expected_sha256.lower():
        raise SystemExit(f"Input SHA-256 {rt.sha256_bytes(data)} does not match expected {expected_sha256}.")
    document = rt.decode_map_setting(data)
    if len(document.packed4_layers) < 2:
        raise SystemExit("Expected at least two packed4 layers for semantic validation.")

    chunked, width, height = inspect.flatten_chunked_binary_layer(document.chunked_binary_layer)
    if (width, height) != (MATRIX_SIZE, MATRIX_SIZE):
        raise SystemExit(f"Expected chunked_binary {MATRIX_SIZE}x{MATRIX_SIZE}, got {width}x{height}.")
    packed0 = inspect.unpack_packed4_layer(document.packed4_layers[0])
    if len(packed0) != MATRIX_SIZE * MATRIX_SIZE:
        raise SystemExit("Expected packed4_0 to contain 810,000 cells.")

    invariants = chunked_invariants(chunked, MATRIX_SIZE)
    contingency = contingency_table(chunked, packed0)
    candidate_cross = candidate_cross_layer_record(chunked, packed0, contingency, MATRIX_SIZE, CANDIDATE_EDGE)
    candidate_rotation = candidate_rotation180_record(chunked, MATRIX_SIZE, CANDIDATE_EDGE)
    direction_mapping = adjacent_direction_distributions(packed0, LOGICAL_GRID_SIZE)
    edges = adjacent_edges(chunked, LOGICAL_GRID_SIZE)
    assets = extract_reference_assets(bundle_path, output_dir)
    scores = transform_scores(edges, output_dir, assets)
    probe = draw_runtime_grid_probe(output_dir / "runtime_grid_probe.png", scores["best_transform"])
    runtime_manifest = runtime_anchor_manifest(scores["best_transform"], Path(probe["path"]))
    decision = candidate_decision(invariants, candidate_cross, direction_mapping, scores, candidate_rotation)

    outputs = {
        "chunked_packed4_contingency": output_dir / "chunked_packed4_contingency.json",
        "candidate_rotation180": output_dir / "candidate_rotation180.json",
        "direction_code_mapping": output_dir / "direction_code_mapping.json",
        "transform_scores": output_dir / "transform_scores.json",
        "runtime_anchor_measurements": output_dir / "runtime_anchor_measurements.json",
        "candidate_decision": output_dir / "candidate_decision.json",
    }
    outputs["chunked_packed4_contingency"].write_text(
        json.dumps({"contingency": contingency, "candidate": candidate_cross}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    outputs["candidate_rotation180"].write_text(
        json.dumps(candidate_rotation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    outputs["direction_code_mapping"].write_text(
        json.dumps(direction_mapping, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    outputs["transform_scores"].write_text(
        json.dumps(scores, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    outputs["runtime_anchor_measurements"].write_text(
        json.dumps(runtime_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    outputs["candidate_decision"].write_text(
        json.dumps(decision, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    manifest = {
        "probe": "map_setting_transform_semantic_validation",
        "input_path": str(input_path),
        "input_sha256": rt.sha256_bytes(data),
        "input_size": len(data),
        "bundle_path": str(bundle_path),
        "layout_path": str(layout_path) if layout_path else None,
        "output_dir": str(output_dir),
        "chunked_binary_invariants": invariants,
        "chunked_packed4_contingency_path": str(outputs["chunked_packed4_contingency"]),
        "candidate_rotation180_path": str(outputs["candidate_rotation180"]),
        "direction_code_mapping_path": str(outputs["direction_code_mapping"]),
        "local_passability_graph": {
            "summary": passability_summary(edges),
            "edge_count": len(edges),
            "source": "adjacent chunked_binary symmetric relation",
        },
        "transform_scores_path": str(outputs["transform_scores"]),
        "transform_summary": {
            "best_transform": scores["best_transform"],
            "second_transform": scores["second_transform"],
            "score_margin": scores["score_margin"],
            "conclusion": scores["conclusion"],
        },
        "runtime_grid_probe": probe,
        "runtime_anchor_measurements_path": str(outputs["runtime_anchor_measurements"]),
        "candidate_decision": decision,
        "candidate_decision_path": str(outputs["candidate_decision"]),
        "safety": {
            "read_only": True,
            "map_setting_mutated": False,
            "map_setting_override_installed": False,
            "original_resources_committed": False,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = output_dir / "semantic_validation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "input_sha256": manifest["input_sha256"],
        "output_dir": manifest["output_dir"],
        "candidate_status": manifest["candidate_decision"]["candidate_status"],
        "best_transform": manifest["transform_summary"]["best_transform"],
        "transform_conclusion": manifest["transform_summary"]["conclusion"],
        "runtime_grid_probe": manifest["runtime_grid_probe"]["path"],
        "read_only": manifest["safety"]["read_only"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate map_setting relation semantics and 30x30 transform.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--bundle", type=Path, required=True, help="Local bundle.game_data for original visual resources.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Repository-external evidence directory.")
    parser.add_argument("--layout", type=Path, default=inspect.DEFAULT_LAYOUT_PATH)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = build_semantic_validation(
        input_path=args.input,
        output_dir=args.output_dir,
        bundle_path=args.bundle,
        layout_path=args.layout,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
