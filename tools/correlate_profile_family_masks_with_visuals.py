from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import analyze_packed4_1_profile_families as q2p  # noqa: E402
from tools import correlate_map_setting_masks_with_visuals as q2n  # noqa: E402
from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2q_profile_family_mask_visual_correlation")
TRANSFORMS = q2n.TRANSFORMS
VISUAL_KEYS = q2n.VISUAL_KEYS
JSON_OUTPUT_FILES = (
    "profile_family_visual_resource_manifest.json",
    "profile_family_anchor_candidate_manifest.json",
    "profile_family_transform_score_summary.json",
    "per_family_transform_rankings.json",
    "aggregate_transform_vote_summary.json",
    "q2q_profile_family_visual_correlation_interpretation.json",
)
OVERLAY_DIR = "family_mask_overlays"
ROBUSTNESS_SUBSETS = (
    "all_resources",
    "wall_only",
    "bush_only",
    "minimap_only",
    "background_only",
    "without_top_5_high_degree_families",
    "without_singleton_family",
)


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def planned_output_paths(output_dir: Path, max_family_count: int = 900) -> list[Path]:
    paths = [output_dir / name for name in JSON_OUTPUT_FILES]
    for index in range(1, max_family_count + 1):
        family_id = f"family_{index:04d}"
        for transform in TRANSFORMS:
            paths.append(output_dir / OVERLAY_DIR / f"{family_id}_{transform}.png")
    return paths


def ensure_paths_are_safe(map_setting: Path, output_dir: Path, asset_sources: dict[str, Path]) -> None:
    inspect.ensure_outside_repo(map_setting, "map_setting")
    inspect.ensure_outside_repo(output_dir, "output directory")
    if is_under_mods_tree(output_dir):
        raise SystemExit("Refusing to write Q2q analysis output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(map_setting, output_dir, "map_setting")
    sources: dict[str, Path] = {"map_setting": map_setting}
    for key, source in asset_sources.items():
        inspect.ensure_outside_repo(source, f"repository-internal asset:{key}")
        if is_under_mods_tree(source):
            raise SystemExit(f"Refusing to use visual asset from runtime mods tree: {source}")
        inspect.ensure_source_outside_output_tree(source, output_dir, f"asset:{key}")
        sources[f"asset:{key}"] = source
    for output_path in planned_output_paths(output_dir):
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")
        for label, source in sources.items():
            if output_path == source or inspect.paths_are_same_existing_file(output_path, source):
                raise SystemExit(f"Refusing to overwrite {label} through generated output path: {output_path}")


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


def counter_payload(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def derive_profile_family_candidates(
    map_setting: Path,
    expected_sha256: str | None,
) -> tuple[bytes, int, list[dict[str, Any]], dict[str, list[int]]]:
    data, chunked, _packed0, packed1, matrix_size, component_by_node, components, edge_records = q2p.load_family_inputs(
        map_setting,
        expected_sha256,
    )
    _logical_size, profiles = q2p.q2m.node_major_profiles(packed1, matrix_size)
    profile_ids, profile_counts = q2p.q2m.stable_profile_ids(profiles)
    by_profile = q2p.nodes_by_profile(profiles)
    singletons = q2p.q2l.singleton_nodes(components)
    singleton_profiles = {profiles[node] for node in singletons}
    singleton_profile = next(iter(singleton_profiles)) if len(singleton_profiles) == 1 else None
    node837_profile = profiles[837] if len(profiles) > 837 else None
    exact_families = [[profile] for profile in sorted(profile_counts, key=lambda profile: (-profile_counts[profile], profile))]
    family_records: list[dict[str, Any]] = []
    family_nodes_by_id: dict[str, list[int]] = {}
    for index, family in enumerate(exact_families, start=1):
        family_id = f"family_{index:04d}"
        nodes = q2p.family_nodes(family, by_profile)
        family_nodes_by_id[family_id] = nodes
        family_records.append(
            q2p.family_record(
                family_id,
                family,
                nodes,
                profile_ids,
                profile_counts,
                chunked,
                component_by_node,
                components,
                edge_records,
                matrix_size,
                singleton_profile,
                node837_profile,
            )
        )
    candidates: list[dict[str, Any]] = []
    for record in family_records:
        score, reasons = q2p.anchor_candidate_score(record)
        if score <= 0:
            continue
        candidate = {
            "family_id": record["family_id"],
            "node_count": record["node_count"],
            "profile_count": record["profile_count"],
            "asymmetry_score": record["asymmetry"]["asymmetry_score"],
            "anchor_candidate_score": score,
            "dominant_role": record["dominant_role"],
            "component_role_counts": record["component_role_counts"],
            "spatial_pattern": record["spatial"]["spatial_pattern"],
            "code15_endpoint_degree_stats": record["code15_endpoint_degree_stats"],
            "representative_profile": record["representative_profile"],
            "reason": ", ".join(reasons),
            "may_use_for_visual_correlation": True,
            "runtime_mutation_allowed": False,
            "packed4_mutation_allowed": False,
            "map_editing_allowed": False,
        }
        candidates.append(candidate)
    candidates.sort(
        key=lambda item: (
            -item["anchor_candidate_score"],
            -item["asymmetry_score"],
            item["node_count"],
            item["family_id"],
        )
    )
    return data, matrix_size, candidates, family_nodes_by_id


def family_mask(nodes: list[int], matrix_size: int) -> list[float]:
    node_set = set(nodes)
    return [1.0 if node in node_set else 0.0 for node in range(matrix_size)]


def combine_visual_subset(
    visual_grids: dict[str, list[float]],
    selected_keys: list[str],
    logical_size: int,
) -> list[float] | None:
    available = [key for key in selected_keys if key in visual_grids]
    if not available:
        return None
    combined = [0.0] * (logical_size * logical_size)
    for key in available:
        weight = 1.0 if key.startswith("wall") else 0.75 if key == "bush_5v5" else 0.35
        combined = [max(left, min(1.0, right * weight)) for left, right in zip(combined, visual_grids[key])]
    return combined


def visual_subset_grid(visual_grids: dict[str, list[float]], subset: str, logical_size: int) -> list[float] | None:
    if subset in ("all_resources", "without_top_5_high_degree_families", "without_singleton_family"):
        return visual_grids.get("combined_visual_feature")
    if subset == "wall_only":
        return combine_visual_subset(visual_grids, ["wall_5v5", "wall_5v5_front"], logical_size)
    if subset == "bush_only":
        return combine_visual_subset(visual_grids, ["bush_5v5"], logical_size)
    if subset == "minimap_only":
        return combine_visual_subset(visual_grids, ["minimap_5v5_bg"], logical_size)
    if subset == "background_only":
        return combine_visual_subset(visual_grids, ["background_5v5"], logical_size)
    raise ValueError(f"Unknown robustness subset: {subset}")


def score_family_transform(
    mask_values: list[float],
    feature_values: list[float],
    logical_size: int,
    transform: str,
) -> dict[str, Any]:
    transformed = q2n.transform_grid(mask_values, logical_size, transform)
    boundary = q2n.dilation(feature_values, logical_size)
    feature_overlap = q2n.weighted_mean(feature_values, transformed)
    boundary_alignment = q2n.weighted_mean(boundary, transformed)
    feature_iou = q2n.soft_iou(transformed, feature_values)
    inverse_open_overlap = q2n.weighted_mean([1.0 - value for value in feature_values], transformed)
    score = feature_overlap * 0.45 + boundary_alignment * 0.25 + feature_iou * 0.25 + (1.0 - inverse_open_overlap) * 0.05
    return {
        "transform": transform,
        "score": round(score, 6),
        "components": {
            "feature_overlap": round(feature_overlap, 6),
            "boundary_alignment": round(boundary_alignment, 6),
            "feature_iou": round(feature_iou, 6),
            "inverse_open_overlap": round(inverse_open_overlap, 6),
        },
    }


def rank_family(
    candidate: dict[str, Any],
    mask_values: list[float],
    feature_values: list[float],
    logical_size: int,
) -> dict[str, Any]:
    scores = [score_family_transform(mask_values, feature_values, logical_size, transform) for transform in TRANSFORMS]
    ranked = sorted(scores, key=lambda record: record["score"], reverse=True)
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    margin = best["score"] - second["score"] if second else 0.0
    result = "single_family_candidate" if margin >= 0.03 else "ambiguous"
    return {
        "family_id": candidate["family_id"],
        "node_count": candidate["node_count"],
        "asymmetry_score": candidate["asymmetry_score"],
        "anchor_candidate_score": candidate["anchor_candidate_score"],
        "dominant_role": candidate["dominant_role"],
        "spatial_pattern": candidate["spatial_pattern"],
        "code15_endpoint_degree_average": candidate["code15_endpoint_degree_stats"]["average"],
        "best_transform": best["transform"],
        "second_transform": second["transform"] if second else None,
        "best_score": best["score"],
        "second_score": second["score"] if second else None,
        "margin": round(margin, 6),
        "visual_correlation_result": result,
        "ranked_transforms": ranked,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def family_vote_weight(ranking: dict[str, Any]) -> float:
    node_weight = min(1.0, math.sqrt(max(1, ranking["node_count"])) / math.sqrt(12))
    degree_average = ranking["code15_endpoint_degree_average"] or 0.0
    degree_weight = 0.5 + min(1.0, degree_average / 120.0)
    asymmetry_weight = 0.5 + ranking["asymmetry_score"]
    margin_weight = max(0.0, ranking["margin"])
    candidate_weight = 0.5 + ranking["anchor_candidate_score"]
    return round(node_weight * degree_weight * asymmetry_weight * candidate_weight * margin_weight, 8)


def aggregate_rankings(rankings: list[dict[str, Any]]) -> dict[str, Any]:
    votes: Counter[str] = Counter()
    family_votes: list[dict[str, Any]] = []
    for ranking in rankings:
        weight = family_vote_weight(ranking)
        votes[ranking["best_transform"]] += weight
        family_votes.append(
            {
                "family_id": ranking["family_id"],
                "best_transform": ranking["best_transform"],
                "margin": ranking["margin"],
                "vote_weight": weight,
            }
        )
    ordered_votes = sorted(votes.items(), key=lambda item: (-item[1], item[0]))
    best_transform = ordered_votes[0][0] if ordered_votes else None
    best_vote = ordered_votes[0][1] if ordered_votes else 0.0
    second_transform = ordered_votes[1][0] if len(ordered_votes) > 1 else None
    second_vote = ordered_votes[1][1] if len(ordered_votes) > 1 else 0.0
    total_vote = sum(votes.values())
    best_share = best_vote / total_vote if total_vote else 0.0
    return {
        "transform_votes": {transform: round(votes[transform], 6) for transform in sorted(votes)},
        "best_transform": best_transform,
        "second_transform": second_transform,
        "best_vote": round(best_vote, 6),
        "second_vote": round(second_vote, 6),
        "aggregate_margin": round(best_vote - second_vote, 6),
        "best_vote_share": round(best_share, 6),
        "family_votes": family_votes,
    }


def rank_subset(
    subset: str,
    candidates: list[dict[str, Any]],
    family_nodes_by_id: dict[str, list[int]],
    matrix_size: int,
    feature_values: list[float] | None,
    logical_size: int,
) -> dict[str, Any]:
    if feature_values is None:
        return {
            "subset": subset,
            "status": "not_available",
            "reason": "required visual resource was not provided or discovered",
        }
    subset_candidates = candidates
    if subset == "without_top_5_high_degree_families":
        by_degree = sorted(
            candidates,
            key=lambda item: (-(item["code15_endpoint_degree_stats"]["average"] or 0.0), item["family_id"]),
        )
        removed = {item["family_id"] for item in by_degree[:5]}
        subset_candidates = [item for item in candidates if item["family_id"] not in removed]
    elif subset == "without_singleton_family":
        subset_candidates = [
            item
            for item in candidates
            if item["component_role_counts"].get("singleton_component", 0) != item["node_count"]
        ]
    rankings = [
        rank_family(
            candidate,
            family_mask(family_nodes_by_id[candidate["family_id"]], matrix_size),
            feature_values,
            logical_size,
        )
        for candidate in subset_candidates
    ]
    aggregate = aggregate_rankings(rankings)
    best_margin = aggregate["aggregate_margin"]
    result = "single_transform_candidate" if best_margin >= 0.03 and aggregate["best_vote_share"] >= 0.6 else "ambiguous"
    return {
        "subset": subset,
        "status": "ok",
        "candidate_count": len(subset_candidates),
        "aggregate": aggregate,
        "visual_correlation_result": result,
    }


def contradictory_subsets(subsets: list[dict[str, Any]], best_transform: str | None) -> list[dict[str, Any]]:
    contradictions = []
    for subset in subsets:
        if subset.get("status") != "ok":
            continue
        if subset.get("visual_correlation_result") != "single_transform_candidate":
            continue
        subset_best = subset["aggregate"]["best_transform"]
        if subset_best != best_transform:
            contradictions.append(
                {
                    "subset": subset["subset"],
                    "best_transform": subset_best,
                    "aggregate_margin": subset["aggregate"]["aggregate_margin"],
                }
            )
    return contradictions


def final_interpretation(
    metadata: dict[str, Any],
    aggregate: dict[str, Any],
    robustness: list[dict[str, Any]],
) -> dict[str, Any]:
    contradictions = contradictory_subsets(robustness, aggregate["best_transform"])
    single = (
        aggregate["aggregate_margin"] >= 0.03
        and aggregate["best_vote_share"] >= 0.6
        and not contradictions
    )
    result = "single_transform_candidate" if single else "ambiguous"
    return {
        "probe": "q2q_profile_family_visual_correlation_interpretation",
        **metadata,
        "q2q_result": result,
        "visual_correlation_result": result,
        "candidate_transform": aggregate["best_transform"] if single else "none",
        "node_world_transform": "candidate_not_proven" if single else "unproven",
        "aggregate_best_transform": aggregate["best_transform"],
        "aggregate_second_transform": aggregate["second_transform"],
        "aggregate_margin": aggregate["aggregate_margin"],
        "best_vote_share": aggregate["best_vote_share"],
        "contradictory_subsets": contradictions,
        "decision_rule": {
            "single_transform_candidate": [
                "aggregate best margin >= 0.03",
                "at least 60% weighted family votes choose the same transform",
                "wall/bush/minimap/background subsets do not contradict the aggregate candidate",
            ],
        },
        "interpretation_boundary": {
            "visual_correlation": "static mask-to-visual heuristic only",
            "node_world_transform": "candidate only if reported; not independently proven",
            "semantic_safety": "not proven",
            "map_editing": "not approved",
            "profile_family_masks": "read-only exact-family masks from Q2P; not runtime anchors",
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


def visual_resource_payload(
    metadata: dict[str, Any],
    asset_sources: dict[str, Path],
    visual_manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "probe": "q2q_profile_family_visual_resource_manifest",
        **metadata,
        "payloads_committed_to_repository": False,
        "resources": visual_manifest,
        "missing_resources": [key for key in VISUAL_KEYS if key not in asset_sources],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def anchor_candidate_payload(metadata: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "probe": "q2q_profile_family_anchor_candidate_manifest",
        **metadata,
        "source": "derived from original map_setting using Q2P exact profile-family rules",
        "candidate_count": len(candidates),
        "anchor_candidate_profiles": candidates,
        "may_use_for_visual_correlation": bool(candidates),
        "node_world_transform": "unproven",
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def write_overlay_outputs(
    output_dir: Path,
    rankings: list[dict[str, Any]],
    family_nodes_by_id: dict[str, list[int]],
    feature_values: list[float],
    matrix_size: int,
    logical_size: int,
    limit: int,
) -> dict[str, Any]:
    overlay_dir = output_dir / OVERLAY_DIR
    overlay_dir.mkdir(parents=True, exist_ok=True)
    created: list[dict[str, Any]] = []
    for ranking in rankings[:limit]:
        mask_values = family_mask(family_nodes_by_id[ranking["family_id"]], matrix_size)
        for transform in TRANSFORMS:
            path = overlay_dir / f"{ranking['family_id']}_{transform}.png"
            q2n.overlay_image(feature_values, mask_values, logical_size, transform, path, (0, 220, 255))
            created.append(
                {
                    "family_id": ranking["family_id"],
                    "transform": transform,
                    "path": str(path),
                    "size": path.stat().st_size,
                    "sha256": rt.sha256_file(path),
                }
            )
    return {
        "overlay_dir": str(overlay_dir),
        "overlay_family_limit": limit,
        "overlay_count": len(created),
        "overlays": created,
    }


def correlate_profile_family_masks_with_visuals(
    map_setting: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    asset_sources: dict[str, Path] | None = None,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
    overlay_family_limit: int = 10,
) -> dict[str, Any]:
    if overlay_family_limit < 0:
        raise SystemExit("--overlay-family-limit must be non-negative.")
    map_setting = map_setting.resolve()
    output_dir = output_dir.resolve()
    asset_sources = {key: path.resolve() for key, path in (asset_sources or {}).items() if path}
    ensure_paths_are_safe(map_setting, output_dir, asset_sources)

    data, matrix_size, candidates, family_nodes_by_id = derive_profile_family_candidates(map_setting, expected_sha256)
    if not candidates:
        raise SystemExit("No Q2P asymmetric profile-family candidates were found.")
    logical_size = q2n.logical_size_for_matrix(matrix_size)
    metadata = base_metadata(map_setting, output_dir, data)
    visual_grids, visual_manifest = q2n.combined_visual_features(asset_sources, logical_size)
    combined_features = visual_grids["combined_visual_feature"]

    rankings = [
        rank_family(
            candidate,
            family_mask(family_nodes_by_id[candidate["family_id"]], matrix_size),
            combined_features,
            logical_size,
        )
        for candidate in candidates
    ]
    aggregate = aggregate_rankings(rankings)
    robustness: list[dict[str, Any]] = []
    for subset in ROBUSTNESS_SUBSETS:
        feature_values = visual_subset_grid(visual_grids, subset, logical_size)
        robustness.append(rank_subset(subset, candidates, family_nodes_by_id, matrix_size, feature_values, logical_size))
    interpretation = final_interpretation(metadata, aggregate, robustness)

    transform_summary = {
        "probe": "q2q_profile_family_transform_score_summary",
        **metadata,
        "scoring_boundary": "Heuristic profile-family mask-to-visual correlation only; not node/world transform proof.",
        "candidate_count": len(candidates),
        "transforms": list(TRANSFORMS),
        "aggregate": aggregate,
        "robustness": robustness,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }
    per_family_payload = {
        "probe": "q2q_per_family_transform_rankings",
        **metadata,
        "candidate_count": len(candidates),
        "rankings": rankings,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }
    aggregate_payload = {
        "probe": "q2q_aggregate_transform_vote_summary",
        **metadata,
        **aggregate,
        "robustness": robustness,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "profile_family_visual_resource_manifest": visual_resource_payload(metadata, asset_sources, visual_manifest),
        "profile_family_anchor_candidate_manifest": anchor_candidate_payload(metadata, candidates),
        "profile_family_transform_score_summary": transform_summary,
        "per_family_transform_rankings": per_family_payload,
        "aggregate_transform_vote_summary": aggregate_payload,
        "q2q_profile_family_visual_correlation_interpretation": interpretation,
    }
    outputs: dict[str, Path] = {}
    for key, payload in payloads.items():
        path = output_dir / f"{key}.json"
        write_json(path, payload)
        outputs[key] = path
    overlay_outputs = write_overlay_outputs(
        output_dir,
        rankings,
        family_nodes_by_id,
        combined_features,
        matrix_size,
        logical_size,
        overlay_family_limit,
    )
    return {
        "probe": "q2q_profile_family_mask_visual_correlation",
        **metadata,
        "outputs": {
            key: {"path": str(path), "size": path.stat().st_size, "sha256": rt.sha256_file(path)}
            for key, path in outputs.items()
        },
        "overlay_outputs": overlay_outputs,
        "q2q_result": interpretation["q2q_result"],
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
        "q2q_result": manifest["q2q_result"],
        "candidate_transform": manifest["candidate_transform"],
        "node_world_transform": manifest["node_world_transform"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": manifest["third_chunked_binary_runtime_probe_allowed"],
        "map_editing_allowed": manifest["map_editing_allowed"],
        "outputs": manifest["outputs"],
        "overlay_outputs": manifest["overlay_outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Correlate Q2P profile-family masks with original visuals.")
    parser.add_argument("--map-setting", type=Path, required=True, help="Local original map_setting binary.")
    parser.add_argument("--asset-dir", type=Path, help="Directory to search for original visual PNG resources.")
    parser.add_argument("--background", type=Path, help="Explicit background_5v5 PNG.")
    parser.add_argument("--minimap", type=Path, help="Explicit minimap_5v5_bg PNG.")
    parser.add_argument("--wall", type=Path, help="Explicit wall_5v5 PNG.")
    parser.add_argument("--wall-front", type=Path, help="Explicit wall_5v5_front PNG.")
    parser.add_argument("--bush", type=Path, help="Explicit bush_5v5 PNG.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--overlay-family-limit", type=int, default=10)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    asset_sources = q2n.explicit_asset_sources(args)
    manifest = correlate_profile_family_masks_with_visuals(
        map_setting=args.map_setting,
        output_dir=args.output_dir,
        asset_sources=asset_sources,
        expected_sha256=args.expected_sha256 or None,
        overlay_family_limit=args.overlay_family_limit,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
