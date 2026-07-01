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

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import analyze_chunked_binary_probe_targets as q2h  # noqa: E402
from tools import analyze_no15_singleton_components as q2l  # noqa: E402
from tools import analyze_packed4_1_node_profiles as q2m  # noqa: E402
from tools import map_setting_inspect as inspect  # noqa: E402
from tools import map_setting_round_trip as rt  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("D:/tfm2_q2a_evidence/q2r_map_setting_unclassified_sections")
JSON_OUTPUT_FILES = (
    "map_setting_section_inventory.json",
    "map_setting_residual_span_entropy.json",
    "dimensioned_array_candidates.json",
    "coordinate_like_value_candidates.json",
    "cross_layer_index_reference_candidates.json",
    "tracked_node_unclassified_context.json",
    "q2r_unclassified_section_interpretation.json",
)
TRACKED_NODES = (369, 370, 59, 837, 126, 617, 654, 184, 773, 498)
INTERESTING_DIMENSIONS = {
    30: "30",
    60: "60",
    90: "90",
    180: "180",
    900: "30x30 or 900-node vector",
    1800: "900 pairs or 1800 values",
    27000: "900x30 or 30x30x30",
    810000: "900x900",
}
INTERESTING_VALUE_LIMITS = (30, 60, 90, 180, 899, 900, 1280)


def is_under_mods_tree(path: Path) -> bool:
    return "mods" in (part.lower() for part in path.resolve().parts)


def planned_output_paths(output_dir: Path, max_candidates: int = 200) -> list[Path]:
    paths = [output_dir / name for name in JSON_OUTPUT_FILES]
    for index in range(1, max_candidates + 1):
        paths.append(output_dir / "candidate_masks" / f"candidate_900_vector_{index:03d}.png")
        paths.append(output_dir / "candidate_masks" / f"candidate_30x30_mask_{index:03d}.png")
    return paths


def ensure_paths_are_safe(input_path: Path, output_dir: Path) -> None:
    inspect.ensure_outside_repo(input_path, "input")
    inspect.ensure_outside_repo(output_dir, "output directory")
    if is_under_mods_tree(output_dir):
        raise SystemExit("Refusing to write Q2r analysis output under a runtime mods tree.")
    inspect.ensure_source_outside_output_tree(input_path, output_dir, "input")
    for output_path in planned_output_paths(output_dir):
        if is_under_mods_tree(output_path):
            raise SystemExit(f"Refusing to write runtime file path: {output_path}")
        if output_path == input_path or inspect.paths_are_same_existing_file(output_path, input_path):
            raise SystemExit(f"Refusing to overwrite input through generated output path: {output_path}")


def sha_payload(path: Path) -> dict[str, Any]:
    return {"path": str(path), "size": path.stat().st_size, "sha256": rt.sha256_file(path)}


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counter = Counter(data)
    total = len(data)
    return -sum((count / total) * math.log2(count / total) for count in counter.values())


def byte_stats(data: bytes) -> dict[str, Any]:
    if not data:
        return {
            "byte_length": 0,
            "entropy": 0.0,
            "unique_byte_count": 0,
            "min_byte": None,
            "max_byte": None,
        }
    return {
        "byte_length": len(data),
        "entropy": round(entropy(data), 6),
        "unique_byte_count": len(set(data)),
        "min_byte": min(data),
        "max_byte": max(data),
    }


def counter_payload(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def possible_dimensions(element_count: int) -> list[str]:
    matches = [label for count, label in INTERESTING_DIMENSIONS.items() if element_count == count]
    if element_count == 900:
        matches.append("30x30")
    if element_count == 27000:
        matches.append("900x30")
        matches.append("30x30x30")
    if element_count == 810000:
        matches.append("900x900")
    return sorted(set(matches))


def numeric_summary(values: list[int | float]) -> dict[str, Any]:
    if not values:
        return {"element_count": 0, "unique_value_count": 0, "min": None, "max": None}
    return {
        "element_count": len(values),
        "unique_value_count": len(set(values)),
        "min": min(values),
        "max": max(values),
    }


def section_record(
    section_id: str,
    kind: str,
    offset: int,
    end_offset: int,
    decoded_type: str,
    data: bytes,
    element_count: int | None = None,
    dimensions: list[str] | None = None,
    interpreted: bool = False,
) -> dict[str, Any]:
    span = data[offset:end_offset]
    stats = byte_stats(span)
    return {
        "section_id": section_id,
        "kind": kind,
        "byte_offset": offset,
        "byte_end_offset": end_offset,
        "byte_length": end_offset - offset,
        "decoded_type": decoded_type,
        "element_count": element_count,
        "possible_dimensions": dimensions or [],
        "entropy": stats["entropy"],
        "unique_value_count": stats["unique_byte_count"],
        "min": stats["min_byte"],
        "max": stats["max_byte"],
        "interpretation_status": "structural_container_known" if interpreted else "unclassified_or_residual",
    }


def inventory_sections(data: bytes) -> tuple[rt.MapSettingDocument, list[dict[str, Any]], list[dict[str, Any]]]:
    chunked, offset = rt.parse_chunked_binary_layer(data, 0)
    sections = [
        section_record(
            "chunked_binary",
            "known_chunked_binary",
            chunked.offset,
            chunked.end_offset,
            "chunked binary structural layer",
            data,
            element_count=810000,
            dimensions=["900x900"],
            interpreted=True,
        )
    ]
    packed_layers: list[rt.Packed4Layer] = []
    residual_spans: list[dict[str, Any]] = []
    for index in range(2):
        if offset >= len(data):
            break
        packed, offset = rt.parse_packed4_layer(data, offset)
        packed_layers.append(packed)
        layer_name = f"packed4_{index}"
        dims = ["900x900"] if index == 0 else ["900x30", "30x30x30"]
        sections.append(
            section_record(
                layer_name,
                f"known_{layer_name}",
                packed.offset,
                packed.end_offset,
                "packed4 structural layer",
                data,
                element_count=packed.cell_count,
                dimensions=dims,
                interpreted=True,
            )
        )
    if offset < len(data):
        residual = section_record(
            "residual_0001",
            "residual_bytes",
            offset,
            len(data),
            "unclassified trailing bytes after known structural layers",
            data,
            element_count=len(data) - offset,
            dimensions=possible_dimensions(len(data) - offset),
            interpreted=False,
        )
        sections.append(residual)
        residual_spans.append(residual)
    return rt.MapSettingDocument(chunked_binary_layer=chunked, packed4_layers=tuple(packed_layers)), sections, residual_spans


def base_metadata(input_path: Path, output_dir: Path, data: bytes) -> dict[str, Any]:
    return {
        "input_path": str(input_path),
        "input_sha256": rt.sha256_bytes(data),
        "input_size": len(data),
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


def unpack_values(span: bytes, interpretation: str) -> list[int | float]:
    if interpretation == "uint8":
        return list(span)
    if interpretation == "int8":
        return list(struct.unpack(f"<{len(span)}b", span)) if span else []
    if interpretation in ("uint16", "int16"):
        usable = len(span) // 2 * 2
        fmt = "H" if interpretation == "uint16" else "h"
        return list(struct.unpack(f"<{usable // 2}{fmt}", span[:usable])) if usable else []
    if interpretation in ("uint32", "int32", "float32"):
        usable = len(span) // 4 * 4
        fmt = {"uint32": "I", "int32": "i", "float32": "f"}[interpretation]
        values = list(struct.unpack(f"<{usable // 4}{fmt}", span[:usable])) if usable else []
        if interpretation == "float32":
            return [round(value, 6) for value in values if math.isfinite(value)]
        return values
    if interpretation == "packed4":
        values: list[int] = []
        for byte in span:
            values.append(byte & 0x0F)
            values.append(byte >> 4)
        return values
    if interpretation == "bitset":
        values = []
        for byte in span:
            for bit in range(8):
                values.append((byte >> bit) & 1)
        return values
    raise ValueError(interpretation)


def dimensioned_array_candidates(spans: list[dict[str, Any]], data: bytes) -> list[dict[str, Any]]:
    candidates = []
    for span in spans:
        raw = data[span["byte_offset"] : span["byte_end_offset"]]
        for interpretation in ("uint8", "int8", "uint16", "int16", "uint32", "int32", "float32", "packed4", "bitset"):
            values = unpack_values(raw, interpretation)
            dims = possible_dimensions(len(values))
            if not dims:
                continue
            summary = numeric_summary(values)
            candidate = {
                "span_id": span["section_id"],
                "byte_offset": span["byte_offset"],
                "byte_length": span["byte_length"],
                "interpretation": interpretation,
                "element_count": len(values),
                "possible_dimensions": dims,
                "unique_value_count": summary["unique_value_count"],
                "min": summary["min"],
                "max": summary["max"],
                "candidate_only": True,
                "not_proven_gameplay_field": True,
            }
            if len(values) == 900:
                candidate["candidate_mask_png"] = None
            candidates.append(candidate)
    return candidates


def coordinate_like_candidates(spans: list[dict[str, Any]], data: bytes) -> list[dict[str, Any]]:
    ranges = {
        "minimap_0_320": (0, 320),
        "background_0_1280": (0, 1280),
        "signed_640": (-640, 640),
    }
    candidates = []
    for span in spans:
        raw = data[span["byte_offset"] : span["byte_end_offset"]]
        for interpretation in ("uint16", "int16", "float32"):
            values = unpack_values(raw, interpretation)
            if len(values) < 4:
                continue
            pair_count = len(values) // 2
            if pair_count == 0:
                continue
            for range_name, (low, high) in ranges.items():
                pairs_in_range = 0
                near_integer_pairs = 0
                for index in range(pair_count):
                    x = values[index * 2]
                    y = values[index * 2 + 1]
                    if low <= x <= high and low <= y <= high:
                        pairs_in_range += 1
                        if isinstance(x, int) and isinstance(y, int):
                            near_integer_pairs += 1
                        elif abs(float(x) - round(float(x))) <= 0.001 and abs(float(y) - round(float(y))) <= 0.001:
                            near_integer_pairs += 1
                ratio = pairs_in_range / pair_count
                if ratio < 0.8:
                    continue
                candidates.append(
                    {
                        "span_id": span["section_id"],
                        "byte_offset": span["byte_offset"],
                        "byte_length": span["byte_length"],
                        "interpretation": interpretation,
                        "range": range_name,
                        "pair_count": pair_count,
                        "pairs_in_range": pairs_in_range,
                        "in_range_ratio": round(ratio, 6),
                        "near_integer_pair_count": near_integer_pairs,
                        "coordinate_like_candidate_only": True,
                        "not_proven_world_coordinate": True,
                        "not_proven_gameplay_field": True,
                    }
                )
    return candidates


def derive_static_node_sets(input_path: Path, expected_sha256: str | None) -> dict[str, Any]:
    try:
        _data, chunked, _packed0, _packed1, matrix_size, component_by_node, components, edge_records = q2l.load_graph_inputs(
            input_path,
            expected_sha256,
        )
    except Exception:
        return {
            "matrix_size": None,
            "tracked_nodes": list(TRACKED_NODES),
            "singleton_nodes": [],
            "large_component_nodes": [],
            "universal_like_nodes": [],
            "high_bridge_degree_nodes": [],
            "available": False,
        }
    rows = q2h.row_sums(chunked, matrix_size)
    columns = q2h.column_sums(chunked, matrix_size)
    singleton_nodes = q2l.singleton_nodes(components)
    large_component_id = q2l.largest_component_id(components)
    large_nodes = sorted(components[large_component_id])
    universal_like = [node for node in range(matrix_size) if rows[node] == matrix_size and columns[node] == matrix_size]
    degrees = q2m.bridge_degrees(edge_records, components)
    high_bridge = sorted(
        range(matrix_size),
        key=lambda node: (-degrees[node]["total_endpoint_count"], node),
    )[:20]
    tracked = {}
    for node in TRACKED_NODES:
        if node >= matrix_size:
            tracked[str(node)] = {"status": "not_applicable"}
            continue
        tracked[str(node)] = {
            "node": node,
            "row_sum": rows[node],
            "column_sum": columns[node],
            "row_class": q2h.classify_sum(rows[node], matrix_size),
            "column_class": q2h.classify_sum(columns[node], matrix_size),
            "component_id": component_by_node[node],
            "component_size": len(components[component_by_node[node]]),
            "is_singleton": node in set(singleton_nodes),
            "is_large_component": node in set(large_nodes),
            "is_universal_like": node in set(universal_like),
            "code15_endpoint_degree": degrees[node]["total_endpoint_count"],
        }
    return {
        "available": True,
        "matrix_size": matrix_size,
        "tracked_nodes": tracked,
        "singleton_nodes": singleton_nodes,
        "large_component_nodes": large_nodes[:120],
        "large_component_nodes_truncated": len(large_nodes) > 120,
        "universal_like_nodes": universal_like,
        "high_bridge_degree_nodes": high_bridge,
        "static_sets": {
            "singleton_node_count": len(singleton_nodes),
            "large_component_node_count": len(large_nodes),
            "universal_like_node_count": len(universal_like),
        },
    }


def cross_layer_reference_candidates(
    spans: list[dict[str, Any]],
    data: bytes,
    static_sets: dict[str, Any],
) -> list[dict[str, Any]]:
    sets = {"tracked_nodes": set(TRACKED_NODES)}
    if static_sets.get("available"):
        sets.update(
            {
                "singleton_nodes": set(static_sets["singleton_nodes"]),
                "large_component_nodes": set(static_sets["large_component_nodes"]),
                "universal_like_nodes": set(static_sets["universal_like_nodes"]),
                "high_bridge_degree_nodes": set(static_sets["high_bridge_degree_nodes"]),
            }
        )
    candidates = []
    for span in spans:
        raw = data[span["byte_offset"] : span["byte_end_offset"]]
        for interpretation in ("uint8", "uint16", "int16", "uint32", "int32"):
            values = unpack_values(raw, interpretation)
            if not values:
                continue
            int_values = [int(value) for value in values if isinstance(value, int) and 0 <= int(value) <= 899]
            if not int_values:
                continue
            counter = Counter(int_values)
            set_hits = {}
            for label, node_set in sets.items():
                hit_count = sum(count for node, count in counter.items() if node in node_set)
                if hit_count:
                    set_hits[label] = hit_count
            if not set_hits:
                continue
            total = len(int_values)
            candidates.append(
                {
                    "span_id": span["section_id"],
                    "byte_offset": span["byte_offset"],
                    "byte_length": span["byte_length"],
                    "interpretation": interpretation,
                    "node_index_like_value_count": total,
                    "unique_node_index_like_value_count": len(counter),
                    "set_hits": set_hits,
                    "top_values": [
                        {"node": node, "count": count}
                        for node, count in counter.most_common(20)
                    ],
                    "cross_layer_index_reference_candidate_only": True,
                    "not_proven_anchor": True,
                }
            )
    return candidates


def residual_entropy_payload(metadata: dict[str, Any], spans: list[dict[str, Any]], data: bytes) -> dict[str, Any]:
    return {
        "probe": "q2r_residual_span_entropy",
        **metadata,
        "residual_span_count": len(spans),
        "residual_spans": [
            {
                **span,
                "byte_stats": byte_stats(data[span["byte_offset"] : span["byte_end_offset"]]),
            }
            for span in spans
        ],
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }


def write_mask_png(values: list[int | float], path: Path) -> None:
    if len(values) != 900:
        return
    numeric = [float(value) for value in values]
    low = min(numeric)
    high = max(numeric)
    scale = 1.0 if high == low else high - low
    image = Image.new("RGBA", (30, 30), (0, 0, 0, 255))
    pixels = image.load()
    for y in range(30):
        for x in range(30):
            value = (numeric[y * 30 + x] - low) / scale
            gray = int(round(max(0.0, min(1.0, value)) * 255))
            pixels[x, y] = (gray, gray, gray, 255)
    image.resize((480, 480), Image.Resampling.NEAREST).save(path)


def write_candidate_pngs(
    output_dir: Path,
    dimension_candidates: list[dict[str, Any]],
    spans: list[dict[str, Any]],
    data: bytes,
) -> dict[str, Any]:
    mask_dir = output_dir / "candidate_masks"
    created = []
    span_by_id = {span["section_id"]: span for span in spans}
    index = 1
    for candidate in dimension_candidates:
        if candidate["element_count"] != 900:
            continue
        if index > 40:
            break
        span = span_by_id[candidate["span_id"]]
        raw = data[span["byte_offset"] : span["byte_end_offset"]]
        values = unpack_values(raw, candidate["interpretation"])
        path = mask_dir / f"candidate_900_vector_{index:03d}.png"
        mask_dir.mkdir(parents=True, exist_ok=True)
        write_mask_png(values, path)
        if path.exists():
            candidate["candidate_mask_png"] = str(path)
            created.append({"path": str(path), "size": path.stat().st_size, "sha256": rt.sha256_file(path)})
            index += 1
    return {"candidate_mask_dir": str(mask_dir), "candidate_mask_count": len(created), "candidate_masks": created}


def interpretation_payload(
    metadata: dict[str, Any],
    residual_spans: list[dict[str, Any]],
    dimension_candidates: list[dict[str, Any]],
    coordinate_candidates: list[dict[str, Any]],
    cross_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor_found = bool(coordinate_candidates or cross_refs)
    return {
        "probe": "q2r_unclassified_section_interpretation",
        **metadata,
        "unclassified_anchor_candidates_found": anchor_found,
        "residual_span_count": len(residual_spans),
        "dimensioned_array_candidate_count": len(dimension_candidates),
        "coordinate_like_candidate_count": len(coordinate_candidates),
        "cross_layer_reference_candidate_count": len(cross_refs),
        "node_world_transform": "candidate_not_proven" if anchor_found else "unproven",
        "interpretation_boundary": {
            "unclassified_sections": "read-only structural inventory only",
            "coordinate_like_values": "candidate only; not proven world coordinates",
            "cross_layer_references": "candidate only; not proven anchors",
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
            "chunked_binary mutation",
            "multi-edge or region mutation",
            "collision/path/spawn editing",
            "brush gameplay mask editing",
            "formal LOL map runtime export",
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def analyze_map_setting_unclassified_sections(
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_sha256: str | None = rt.MAP_SETTING_SHA256,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    ensure_paths_are_safe(input_path, output_dir)
    data = input_path.read_bytes()
    actual_sha = rt.sha256_bytes(data)
    if expected_sha256 and actual_sha.lower() != expected_sha256.lower():
        raise SystemExit(f"Input SHA-256 {actual_sha} does not match expected {expected_sha256}.")
    _document, sections, residual_spans = inventory_sections(data)
    metadata = base_metadata(input_path, output_dir, data)
    static_sets = derive_static_node_sets(input_path, expected_sha256)
    dimension_candidates = dimensioned_array_candidates(residual_spans, data)
    coordinate_candidates = coordinate_like_candidates(residual_spans, data)
    cross_refs = cross_layer_reference_candidates(residual_spans, data, static_sets)

    inventory_payload = {
        "probe": "q2r_map_setting_section_inventory",
        **metadata,
        "section_count": len(sections),
        "sections": sections,
        "known_section_count": sum(1 for section in sections if section["kind"].startswith("known_")),
        "residual_span_count": len(residual_spans),
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }
    dimension_payload = {
        "probe": "q2r_dimensioned_array_candidates",
        **metadata,
        "candidate_count": len(dimension_candidates),
        "candidates": dimension_candidates,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }
    coordinate_payload = {
        "probe": "q2r_coordinate_like_value_candidates",
        **metadata,
        "candidate_count": len(coordinate_candidates),
        "candidates": coordinate_candidates,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }
    cross_ref_payload = {
        "probe": "q2r_cross_layer_index_reference_candidates",
        **metadata,
        "candidate_count": len(cross_refs),
        "candidates": cross_refs,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }
    tracked_payload = {
        "probe": "q2r_tracked_node_unclassified_context",
        **metadata,
        "static_node_context": static_sets,
        "residual_reference_candidates": cross_refs,
        "runtime_mutation_allowed": False,
        "packed4_mutation_allowed": False,
        "map_editing_allowed": False,
    }
    residual_payload = residual_entropy_payload(metadata, residual_spans, data)
    interpretation = interpretation_payload(metadata, residual_spans, dimension_candidates, coordinate_candidates, cross_refs)

    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "map_setting_section_inventory": inventory_payload,
        "map_setting_residual_span_entropy": residual_payload,
        "dimensioned_array_candidates": dimension_payload,
        "coordinate_like_value_candidates": coordinate_payload,
        "cross_layer_index_reference_candidates": cross_ref_payload,
        "tracked_node_unclassified_context": tracked_payload,
        "q2r_unclassified_section_interpretation": interpretation,
    }
    outputs: dict[str, Path] = {}
    for key, payload in payloads.items():
        path = output_dir / f"{key}.json"
        write_json(path, payload)
        outputs[key] = path
    png_outputs = write_candidate_pngs(output_dir, dimension_candidates, residual_spans, data)
    return {
        "probe": "q2r_map_setting_unclassified_section_inventory",
        **metadata,
        "outputs": {key: sha_payload(path) for key, path in outputs.items()},
        "png_outputs": png_outputs,
        "unclassified_anchor_candidates_found": interpretation["unclassified_anchor_candidates_found"],
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
        "input_sha256": manifest["input_sha256"],
        "output_dir": manifest["output_dir"],
        "unclassified_anchor_candidates_found": manifest["unclassified_anchor_candidates_found"],
        "node_world_transform": manifest["node_world_transform"],
        "runtime_mutation_allowed": manifest["runtime_mutation_allowed"],
        "packed4_mutation_allowed": manifest["packed4_mutation_allowed"],
        "third_chunked_binary_runtime_probe_allowed": manifest["third_chunked_binary_runtime_probe_allowed"],
        "map_editing_allowed": manifest["map_editing_allowed"],
        "outputs": manifest["outputs"],
        "png_outputs": manifest["png_outputs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory unclassified map_setting sections without mutation.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-sha256", default=rt.MAP_SETTING_SHA256)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()

    manifest = analyze_map_setting_unclassified_sections(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_sha256=args.expected_sha256 or None,
    )
    print(json.dumps(manifest if args.print_manifest else stdout_summary(manifest), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
