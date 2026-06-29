from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import analyze_chunked_binary_probe_targets as q2h  # noqa: E402
from tools import analyze_code15_component_graph as q2k  # noqa: E402
from tools import analyze_no15_singleton_components as q2l  # noqa: E402
from tools import analyze_packed4_next_hop_semantics as q2i  # noqa: E402
from tools import analyze_packed4_1_node_profiles as q2m  # noqa: E402
from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402
from tools import map_setting_validate_semantics as semantics  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2n_map_setting_mask_visual_correlation")
TRANSFORMS = semantics.TRANSFORMS
VISUAL_KEYS = ("background_5v5", "minimap_5v5_bg", "wall_5v5", "wall_5v5_front", "bush_5v5")
OUTPUT_FILES = (
    "structural_masks_manifest.json",
    "profile_0001_mask_30x30.png",
    "no15_large_component_mask_30x30.png",
    "code15_bridge_endpoint_heatmap_30x30.png",
    "packed4_0_direction_confidence_mask_30x30.png",
    "visual_resource_manifest.json",
    "transform_score_summary.json",
    "q2n_visual_correlation_interpretation.json",
)
MASK_OVERLAY_KEYS = ("profile0001", "large_component", "bridge_heatmap")


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def planned_output_paths(output_dir: Path) -> list[Path]:
    paths = [output_dir / name for name in OUTPUT_FILES]
    for transform in TRANSFORMS:
        for key in MASK_OVERLAY_KEYS:
            paths.append(output_dir / f"overlay_{key}_{transform}.png")
    for key in VISUAL_KEYS:
        paths.append(output_dir / "visual_samples" / f"{key}.png")
    return paths


def ensure_paths_are_safe(map_setting: Path, output_dir: Path, asset_sources: dict[str, Path]) -> None:
    inspect.ensure_outside_repo(map_setting, "map_setting")
    inspect.ensure_outside_repo(output_dir, "output directory")
    if is_under_mods_tree(output_dir):
        raise SystemExit("Refusing to write Q2n analysis output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(map_setting, output_dir, "map_setting")
    sources = {"map_setting": map_setting, **{f"asset:{key}": path for key, path in asset_sources.items()}}
    for label, source in sources.items():
        if label.startswith("asset:"):
            inspect.ensure_outside_repo(source, label)
        inspect.ensure_source_outside_output_tree(source, output_dir, label)
    for output_path in planned_output_paths(output_dir):
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")
        for label, source in sources.items():
            if output_path == source or inspect.paths_are_same_existing_file(output_path, source):
                raise SystemExit(f"Refusing to overwrite {label} through generated output path: {output_path}")


def counter_payload(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def base_metadata(map_setting: Path, output_dir: Path, data: bytes) -> dict[str, Any]:
    return {
        "map_setting_path": str(map_setting),
        "map_setting_sha256": rt.sha256_bytes(data),
        "map_setting_size": len(data),
        "output_dir": str(output_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "safety": {
            "read_only": True,
            "mutated_map_setting_generated": False,
            "runtime_install_modified": False,
            "map_setting_override_installed": False,
            "outputs_inside_repository": rt.is_inside_repo(output_dir),
            "outputs_under_mods_tree": is_under_mods_tree(output_dir),
        },
    }


def lower_name(path: Path) -> str:
    return path.name.lower()


def candidate_priority(path: Path, key: str) -> tuple[int, int, str]:
    text = str(path).lower().replace("\\", "/")
    score = 0
    if "native_layer_extracts" in text:
        score += 50
    if "native_reference" in text or "native_actor_reference" in text:
        score += 40
    if "/mods/" in text:
        score -= 100
    if "teamfight-map" in text:
        score -= 100
    if key in lower_name(path):
        score += 10
    return (-score, len(path.parts), text)


def discover_visual_assets(asset_dir: Path) -> dict[str, Path]:
    patterns = {
        "background_5v5": ("background_5v5.png", "native_background_5v5_reference.png"),
        "minimap_5v5_bg": ("minimap_5v5_bg.png",),
        "wall_5v5": ("wall_5v5.png", "native_wall_5v5_reference.png"),
        "wall_5v5_front": ("wall_5v5_front.png", "native_wall_5v5_front_reference.png"),
        "bush_5v5": ("bush_5v5.png", "native_bush_5v5_reference.png"),
    }
    discovered: dict[str, Path] = {}
    if not asset_dir.exists():
        return discovered
    files = [path for path in asset_dir.rglob("*.png") if path.is_file()]
    for key, names in patterns.items():
        candidates = [path for path in files if lower_name(path) in names]
        if candidates:
            discovered[key] = sorted(candidates, key=lambda path: candidate_priority(path, key))[0].resolve()
    return discovered


def explicit_asset_sources(args: argparse.Namespace) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    mapping = {
        "background_5v5": args.background,
        "minimap_5v5_bg": args.minimap,
        "wall_5v5": args.wall,
        "wall_5v5_front": args.wall_front,
        "bush_5v5": args.bush,
    }
    for key, value in mapping.items():
        if value:
            sources[key] = value.resolve()
    if args.asset_dir:
        discovered = discover_visual_assets(args.asset_dir.resolve())
        discovered.update(sources)
        sources = discovered
    return sources


def load_graph_inputs(
    map_setting: Path,
    expected_sha256: str | None,
) -> tuple[bytes, list[int], list[int], list[int], int, list[int], list[list[int]], list[dict[str, Any]]]:
    return q2l.load_graph_inputs(map_setting, expected_sha256)


def logical_size_for_matrix(matrix_size: int) -> int:
    return q2i.logical_size_for_matrix(matrix_size)


def build_structural_masks(
    chunked: list[int],
    packed0: list[int],
    packed1: list[int],
    matrix_size: int,
    component_by_node: list[int],
    components: list[list[int]],
    edge_records: list[dict[str, Any]],
) -> dict[str, list[float]]:
    logical_size = logical_size_for_matrix(matrix_size)
    _profile_size, profiles = q2m.node_major_profiles(packed1, matrix_size)
    profile_ids, _profile_counts = q2m.stable_profile_ids(profiles)
    singletons = set(q2l.singleton_nodes(components))
    singleton_profiles = {profiles[node] for node in singletons}
    profile0001_nodes = {
        node for node, profile in enumerate(profiles) if profile_ids[profile] == "profile_0001"
    }
    if len(singleton_profiles) == 1:
        singleton_profile = next(iter(singleton_profiles))
        profile0001_nodes = {node for node, profile in enumerate(profiles) if profile == singleton_profile}
    large_component = q2l.largest_component_id(components)
    large_nodes = set(components[large_component])
    bridge_counts = Counter()
    for record in edge_records:
        bridge_counts[record["source"]] += 1
        bridge_counts[record["target"]] += 1
    max_bridge = max(bridge_counts.values()) if bridge_counts else 1
    direction_confidence: list[float] = []
    direction_codes = set(range(8))
    for node in range(matrix_size):
        x = node % logical_size
        y = node // logical_size
        total = 0
        resolved = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx = x + dx
                ny = y + dy
                if not (0 <= nx < logical_size and 0 <= ny < logical_size):
                    continue
                target = ny * logical_size + nx
                total += 1
                if packed0[node * matrix_size + target] in direction_codes:
                    resolved += 1
        direction_confidence.append(resolved / total if total else 0.0)
    universal_rows = q2h.row_sums(chunked, matrix_size)
    universal_columns = q2h.column_sums(chunked, matrix_size)
    node837_mask = [
        1.0 if universal_rows[node] == matrix_size and universal_columns[node] == matrix_size else 0.0
        for node in range(matrix_size)
    ]
    return {
        "profile_0001": [1.0 if node in profile0001_nodes else 0.0 for node in range(matrix_size)],
        "large_component": [1.0 if node in large_nodes else 0.0 for node in range(matrix_size)],
        "bridge_heatmap": [bridge_counts[node] / max_bridge for node in range(matrix_size)],
        "direction_confidence": direction_confidence,
        "node837_universal_like": node837_mask,
    }


def transform_xy(x: int, y: int, size: int, transform: str) -> tuple[int, int]:
    last = size - 1
    if transform == "identity":
        return x, y
    if transform == "rotate90":
        return last - y, x
    if transform == "rotate180":
        return last - x, last - y
    if transform == "rotate270":
        return y, last - x
    if transform == "flip_x":
        return last - x, y
    if transform == "flip_y":
        return x, last - y
    if transform == "transpose":
        return y, x
    if transform == "anti_transpose":
        return last - y, last - x
    raise ValueError(f"Unknown transform: {transform}")


def transform_grid(values: list[float], logical_size: int, transform: str) -> list[float]:
    transformed = [0.0] * len(values)
    for y in range(logical_size):
        for x in range(logical_size):
            tx, ty = transform_xy(x, y, logical_size, transform)
            transformed[ty * logical_size + tx] = values[y * logical_size + x]
    return transformed


def mask_to_image(values: list[float], logical_size: int, path: Path, palette: str = "gray") -> None:
    image = Image.new("RGBA", (logical_size, logical_size), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(logical_size):
        for x in range(logical_size):
            value = max(0.0, min(1.0, values[y * logical_size + x]))
            alpha = int(round(value * 255))
            if palette == "cyan":
                color = (0, 220, 255, alpha)
            elif palette == "yellow":
                color = (255, 220, 0, alpha)
            elif palette == "magenta":
                color = (255, 0, 220, alpha)
            else:
                gray = int(round(value * 255))
                color = (gray, gray, gray, 255)
            pixels[x, y] = color
    image.resize((logical_size * 16, logical_size * 16), Image.Resampling.NEAREST).save(path)


def verify_png(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return {"width": image.width, "height": image.height, "mode": image.mode}


def visual_feature_grid(path: Path, logical_size: int) -> tuple[list[float], dict[str, Any]]:
    info = verify_png(path)
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        has_alpha_signal = alpha.getextrema()[0] < 250
        sampled = rgba.resize((logical_size, logical_size), Image.Resampling.BOX)
        if hasattr(sampled, "get_flattened_data"):
            pixels = list(sampled.get_flattened_data())
        else:
            pixels = list(sampled.getdata())
    values: list[float] = []
    if has_alpha_signal:
        values = [pixel[3] / 255.0 for pixel in pixels]
        method = "alpha_downsample"
    else:
        luminances = [(0.299 * r + 0.587 * g + 0.114 * b) for r, g, b, _a in pixels]
        avg = sum(luminances) / len(luminances)
        values = [abs(value - avg) / 255.0 for value in luminances]
        method = "luminance_deviation_downsample"
    return values, {**info, "feature_method": method, "sha256": rt.sha256_file(path), "size": path.stat().st_size}


def combined_visual_features(asset_sources: dict[str, Path], logical_size: int) -> tuple[dict[str, list[float]], dict[str, Any]]:
    grids: dict[str, list[float]] = {}
    manifest: dict[str, Any] = {}
    for key, path in sorted(asset_sources.items()):
        grids[key], manifest[key] = visual_feature_grid(path, logical_size)
        manifest[key]["path"] = str(path)
    feature_priority = [key for key in ("wall_5v5", "wall_5v5_front", "bush_5v5", "minimap_5v5_bg", "background_5v5") if key in grids]
    if not feature_priority:
        raise SystemExit("No supported visual resources were found or provided.")
    combined = [0.0] * (logical_size * logical_size)
    for key in feature_priority:
        weight = 1.0 if key.startswith("wall") else 0.75 if key == "bush_5v5" else 0.35
        combined = [max(left, min(1.0, right * weight)) for left, right in zip(combined, grids[key])]
    grids["combined_visual_feature"] = combined
    return grids, manifest


def dilation(values: list[float], logical_size: int) -> list[float]:
    result = [0.0] * len(values)
    for y in range(logical_size):
        for x in range(logical_size):
            best = 0.0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx = x + dx
                    ny = y + dy
                    if 0 <= nx < logical_size and 0 <= ny < logical_size:
                        best = max(best, values[ny * logical_size + nx])
            result[y * logical_size + x] = best
    return result


def average_product(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right)) / len(left) if left else 0.0


def weighted_mean(values: list[float], weights: list[float]) -> float:
    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0
    return sum(value * weight for value, weight in zip(values, weights)) / total_weight


def soft_iou(left: list[float], right: list[float]) -> float:
    intersection = sum(min(a, b) for a, b in zip(left, right))
    union = sum(max(a, b) for a, b in zip(left, right))
    return intersection / union if union else 0.0


def score_transform(
    masks: dict[str, list[float]],
    visual_grids: dict[str, list[float]],
    logical_size: int,
    transform: str,
) -> dict[str, Any]:
    features = visual_grids["combined_visual_feature"]
    boundary = dilation(features, logical_size)
    profile = transform_grid(masks["profile_0001"], logical_size, transform)
    large = transform_grid(masks["large_component"], logical_size, transform)
    bridge = transform_grid(masks["bridge_heatmap"], logical_size, transform)
    direction = transform_grid(masks["direction_confidence"], logical_size, transform)
    node837 = transform_grid(masks["node837_universal_like"], logical_size, transform)

    profile_boundary = weighted_mean(boundary, profile)
    profile_feature = weighted_mean(features, profile)
    profile_feature_iou = soft_iou(profile, features)
    large_open = weighted_mean([1.0 - value for value in features], large)
    large_feature_penalty = weighted_mean(features, large)
    bridge_boundary = weighted_mean(boundary, bridge)
    bridge_feature = weighted_mean(features, bridge)
    direction_open = weighted_mean([1.0 - value for value in features], direction)
    node837_feature = weighted_mean(features, node837)

    score = (
        profile_boundary * 0.25
        + profile_feature_iou * 0.15
        + (1.0 - profile_feature) * 0.10
        + large_open * 0.25
        + (1.0 - large_feature_penalty) * 0.10
        + bridge_boundary * 0.15
        + bridge_feature * 0.05
        + direction_open * 0.08
        + node837_feature * 0.02
    )
    return {
        "transform": transform,
        "score": round(score, 6),
        "components": {
            "profile0001_boundary_alignment": round(profile_boundary, 6),
            "profile0001_feature_overlap": round(profile_feature, 6),
            "profile0001_feature_iou": round(profile_feature_iou, 6),
            "large_component_open_overlap": round(large_open, 6),
            "large_component_feature_penalty": round(large_feature_penalty, 6),
            "bridge_heatmap_boundary_alignment": round(bridge_boundary, 6),
            "bridge_heatmap_feature_overlap": round(bridge_feature, 6),
            "direction_confidence_open_overlap": round(direction_open, 6),
            "node837_feature_overlap": round(node837_feature, 6),
        },
    }


def overlay_image(
    base_features: list[float],
    mask_values: list[float],
    logical_size: int,
    transform: str,
    path: Path,
    color: tuple[int, int, int],
) -> None:
    transformed = transform_grid(mask_values, logical_size, transform)
    scale = 24
    image = Image.new("RGBA", (logical_size, logical_size), (0, 0, 0, 255))
    pixels = image.load()
    for y in range(logical_size):
        for x in range(logical_size):
            feature = int(round(max(0.0, min(1.0, base_features[y * logical_size + x])) * 180))
            value = max(0.0, min(1.0, transformed[y * logical_size + x]))
            if value:
                alpha = value
                r = int(round(feature * (1 - alpha) + color[0] * alpha))
                g = int(round(feature * (1 - alpha) + color[1] * alpha))
                b = int(round(feature * (1 - alpha) + color[2] * alpha))
                pixels[x, y] = (r, g, b, 255)
            else:
                pixels[x, y] = (feature, feature, feature, 255)
    image = image.resize((logical_size * scale, logical_size * scale), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    for index in range(logical_size + 1):
        xy = index * scale
        draw.line([(xy, 0), (xy, logical_size * scale)], fill=(30, 30, 30, 180), width=1)
        draw.line([(0, xy), (logical_size * scale, xy)], fill=(30, 30, 30, 180), width=1)
    image.save(path)


def structural_masks_payload(
    metadata: dict[str, Any],
    masks: dict[str, list[float]],
    matrix_size: int,
    components: list[list[int]],
) -> dict[str, Any]:
    logical_size = logical_size_for_matrix(matrix_size)
    return {
        "probe": "q2n_structural_masks",
        **metadata,
        "coordinate_boundary": "30x30 table coordinates are unproven game-world coordinates.",
        "logical_size": logical_size,
        "masks": {
            "profile_0001": {
                "node_count": sum(1 for value in masks["profile_0001"] if value > 0),
                "description": "Q2m singleton-only node-major packed4_1 profile mask.",
            },
            "large_component": {
                "node_count": sum(1 for value in masks["large_component"] if value > 0),
                "description": "Q2k/Q2l no15 weak component with 810 nodes.",
            },
            "bridge_heatmap": {
                "nonzero_node_count": sum(1 for value in masks["bridge_heatmap"] if value > 0),
                "description": "Normalized code15 endpoint degree heatmap.",
            },
            "direction_confidence": {
                "nonzero_node_count": sum(1 for value in masks["direction_confidence"] if value > 0),
                "description": "Adjacent packed4_0 0-7 direction-code presence ratio per source node.",
            },
            "node837_universal_like": {
                "node_count": sum(1 for value in masks["node837_universal_like"] if value > 0),
                "description": "Nodes with row_sum == column_sum == 900.",
            },
        },
        "component_size_histogram": counter_payload(Counter(len(component) for component in components)),
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def visual_resource_payload(metadata: dict[str, Any], asset_sources: dict[str, Path], visual_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": "q2n_visual_resource_manifest",
        **metadata,
        "payloads_committed_to_repository": False,
        "resources": visual_manifest,
        "missing_resources": [key for key in VISUAL_KEYS if key not in asset_sources],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def transform_scores_payload(
    metadata: dict[str, Any],
    masks: dict[str, list[float]],
    visual_grids: dict[str, list[float]],
    logical_size: int,
) -> dict[str, Any]:
    scores = [score_transform(masks, visual_grids, logical_size, transform) for transform in TRANSFORMS]
    ranked = sorted(scores, key=lambda record: record["score"], reverse=True)
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    margin = best["score"] - second["score"] if second else None
    result = "single_transform_candidate" if margin is not None and margin >= 0.03 else "ambiguous"
    return {
        "probe": "q2n_transform_score_summary",
        **metadata,
        "scoring_boundary": "Heuristic visual correlation only; not node/world transform proof.",
        "scores": ranked,
        "best_transform": best["transform"],
        "second_transform": second["transform"] if second else None,
        "best_score": best["score"],
        "second_score": second["score"] if second else None,
        "margin": round(margin, 6) if margin is not None else None,
        "visual_transform_result": result,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def interpretation_payload(
    metadata: dict[str, Any],
    score_summary: dict[str, Any],
) -> dict[str, Any]:
    if score_summary["visual_transform_result"] == "single_transform_candidate":
        node_world_transform = "candidate_not_proven"
    else:
        node_world_transform = "unproven"
    return {
        "probe": "q2n_visual_correlation_interpretation",
        **metadata,
        "visual_correlation_result": score_summary["visual_transform_result"],
        "candidate_transform": score_summary["best_transform"],
        "candidate_margin": score_summary["margin"],
        "node_world_transform": node_world_transform,
        "interpretation_boundary": {
            "visual_correlation": "static mask-to-visual heuristic only",
            "node_world_transform": "not independently proven",
            "semantic_safety": "not proven",
            "map_editing": "not approved",
        },
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "third_chunked_binary_runtime_probe_allowed": False,
        "map_editing_allowed": False,
        "next_recommended_step": "continue_static_decoding",
        "blocked_actions": [
            "third runtime mutation",
            "packed4_0 mutation",
            "packed4_1 mutation",
            "multi-edge or region mutation",
            "collision/path/spawn editing",
            "brush gameplay mask editing",
            "formal LOL map runtime export",
        ],
    }


def correlate_map_setting_masks_with_visuals(
    map_setting: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    asset_sources: dict[str, Path] | None = None,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    map_setting = map_setting.resolve()
    output_dir = output_dir.resolve()
    asset_sources = {key: path.resolve() for key, path in (asset_sources or {}).items() if path}
    ensure_paths_are_safe(map_setting, output_dir, asset_sources)

    data, chunked, packed0, packed1, matrix_size, component_by_node, components, edge_records = load_graph_inputs(
        map_setting,
        expected_sha256,
    )
    logical_size = logical_size_for_matrix(matrix_size)
    metadata = base_metadata(map_setting, output_dir, data)
    masks = build_structural_masks(chunked, packed0, packed1, matrix_size, component_by_node, components, edge_records)
    visual_grids, visual_manifest = combined_visual_features(asset_sources, logical_size)

    structural_payload = structural_masks_payload(metadata, masks, matrix_size, components)
    visual_payload = visual_resource_payload(metadata, asset_sources, visual_manifest)
    score_payload = transform_scores_payload(metadata, masks, visual_grids, logical_size)
    interpretation = interpretation_payload(metadata, score_payload)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "structural_masks_manifest": output_dir / "structural_masks_manifest.json",
        "profile_0001_mask_30x30": output_dir / "profile_0001_mask_30x30.png",
        "no15_large_component_mask_30x30": output_dir / "no15_large_component_mask_30x30.png",
        "code15_bridge_endpoint_heatmap_30x30": output_dir / "code15_bridge_endpoint_heatmap_30x30.png",
        "packed4_0_direction_confidence_mask_30x30": output_dir / "packed4_0_direction_confidence_mask_30x30.png",
        "visual_resource_manifest": output_dir / "visual_resource_manifest.json",
        "transform_score_summary": output_dir / "transform_score_summary.json",
        "q2n_visual_correlation_interpretation": output_dir / "q2n_visual_correlation_interpretation.json",
    }
    outputs["structural_masks_manifest"].write_text(
        json.dumps(structural_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    outputs["visual_resource_manifest"].write_text(
        json.dumps(visual_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    outputs["transform_score_summary"].write_text(
        json.dumps(score_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    outputs["q2n_visual_correlation_interpretation"].write_text(
        json.dumps(interpretation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    mask_to_image(masks["profile_0001"], logical_size, outputs["profile_0001_mask_30x30"], "cyan")
    mask_to_image(masks["large_component"], logical_size, outputs["no15_large_component_mask_30x30"], "yellow")
    mask_to_image(masks["bridge_heatmap"], logical_size, outputs["code15_bridge_endpoint_heatmap_30x30"], "magenta")
    mask_to_image(masks["direction_confidence"], logical_size, outputs["packed4_0_direction_confidence_mask_30x30"], "gray")

    overlay_outputs: dict[str, Path] = {}
    for transform in TRANSFORMS:
        overlay_specs = {
            "profile0001": ("profile_0001", (0, 220, 255)),
            "large_component": ("large_component", (255, 220, 0)),
            "bridge_heatmap": ("bridge_heatmap", (255, 0, 220)),
        }
        for overlay_key, (mask_key, color) in overlay_specs.items():
            path = output_dir / f"overlay_{overlay_key}_{transform}.png"
            overlay_image(
                visual_grids["combined_visual_feature"],
                masks[mask_key],
                logical_size,
                transform,
                path,
                color,
            )
            overlay_outputs[f"overlay_{overlay_key}_{transform}"] = path

    all_outputs = {**outputs, **overlay_outputs}
    return {
        "probe": "q2n_map_setting_mask_visual_correlation",
        **metadata,
        "outputs": {
            key: {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": rt.sha256_file(path),
            }
            for key, path in all_outputs.items()
        },
        "visual_correlation_result": interpretation["visual_correlation_result"],
        "candidate_transform": interpretation["candidate_transform"],
        "node_world_transform": interpretation["node_world_transform"],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "third_chunked_binary_runtime_probe_allowed": False,
        "map_editing_allowed": False,
        "next_recommended_step": interpretation["next_recommended_step"],
    }


def stdout_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe": manifest["probe"],
        "map_setting_sha256": manifest["map_setting_sha256"],
        "output_dir": manifest["output_dir"],
        "visual_correlation_result": manifest["visual_correlation_result"],
        "candidate_transform": manifest["candidate_transform"],
        "node_world_transform": manifest["node_world_transform"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": manifest["third_chunked_binary_runtime_probe_allowed"],
        "map_editing_allowed": manifest["map_editing_allowed"],
        "outputs": manifest["outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Correlate map_setting structural masks with original visuals.")
    parser.add_argument("--map-setting", type=Path, required=True, help="Local original map_setting binary.")
    parser.add_argument("--asset-dir", type=Path, help="Directory to search for original visual PNG resources.")
    parser.add_argument("--background", type=Path, help="Explicit background_5v5 PNG.")
    parser.add_argument("--minimap", type=Path, help="Explicit minimap_5v5_bg PNG.")
    parser.add_argument("--wall", type=Path, help="Explicit wall_5v5 PNG.")
    parser.add_argument("--wall-front", type=Path, help="Explicit wall_5v5_front PNG.")
    parser.add_argument("--bush", type=Path, help="Explicit bush_5v5 PNG.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    asset_sources = explicit_asset_sources(args)
    manifest = correlate_map_setting_masks_with_visuals(
        map_setting=args.map_setting,
        output_dir=args.output_dir,
        asset_sources=asset_sources,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
