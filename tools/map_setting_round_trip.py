from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_SETTING_SHA256 = "6fee0c2b22905b5387976529d218f407efc5ca4ef9edb63d3f520a78eb8e9ca0"


class DecodeError(ValueError):
    pass


@dataclass(frozen=True)
class ChunkedGrid:
    rows: tuple[bytes, ...]


@dataclass(frozen=True)
class ChunkedGroup:
    grids: tuple[ChunkedGrid, ...]


@dataclass(frozen=True)
class ChunkedBinaryLayer:
    offset: int
    end_offset: int
    groups: tuple[ChunkedGroup, ...]


@dataclass(frozen=True)
class Packed4Layer:
    offset: int
    end_offset: int
    cell_count: int
    byte_count: int
    blob: bytes


@dataclass(frozen=True)
class MapSettingDocument:
    chunked_binary_layer: ChunkedBinaryLayer
    packed4_layers: tuple[Packed4Layer, ...]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pack_u64(value: int) -> bytes:
    return struct.pack("<Q", value)


def read_u64(data: bytes, offset: int) -> int:
    if offset + 8 > len(data):
        raise DecodeError(f"unexpected end of map_setting at offset {offset}")
    return struct.unpack_from("<Q", data, offset)[0]


def require_reasonable_count(value: int, label: str, offset: int, upper_bound: int = 4096) -> None:
    if not (1 <= value <= upper_bound):
        raise DecodeError(f"invalid {label} {value} at offset {offset}")


def parse_chunked_binary_layer(data: bytes, offset: int = 0) -> tuple[ChunkedBinaryLayer, int]:
    start = offset
    group_count = read_u64(data, offset)
    require_reasonable_count(group_count, "chunk group count", offset, upper_bound=256)
    offset += 8

    groups: list[ChunkedGroup] = []
    for _group_index in range(group_count):
        grid_count_offset = offset
        grid_count = read_u64(data, offset)
        require_reasonable_count(grid_count, "chunk grid count", grid_count_offset, upper_bound=256)
        offset += 8

        grids: list[ChunkedGrid] = []
        for _grid_index in range(grid_count):
            row_count_offset = offset
            row_count = read_u64(data, offset)
            require_reasonable_count(row_count, "chunk row count", row_count_offset, upper_bound=256)
            offset += 8

            rows: list[bytes] = []
            for _row_index in range(row_count):
                width_offset = offset
                width = read_u64(data, offset)
                require_reasonable_count(width, "chunk row width", width_offset)
                offset += 8

                row = data[offset : offset + width]
                if len(row) != width:
                    raise DecodeError(f"unexpected end while reading chunk row at offset {offset}")
                rows.append(row)
                offset += width
            grids.append(ChunkedGrid(rows=tuple(rows)))
        groups.append(ChunkedGroup(grids=tuple(grids)))

    return ChunkedBinaryLayer(offset=start, end_offset=offset, groups=tuple(groups)), offset


def parse_packed4_layer(data: bytes, offset: int) -> tuple[Packed4Layer, int]:
    start = offset
    cell_count = read_u64(data, offset)
    byte_count = read_u64(data, offset + 8)
    if byte_count * 2 != cell_count:
        raise DecodeError(f"packed4 layer at offset {offset} has cell_count={cell_count} byte_count={byte_count}")
    blob_start = offset + 16
    blob_end = blob_start + byte_count
    blob = data[blob_start:blob_end]
    if len(blob) != byte_count:
        raise DecodeError(f"unexpected end while reading packed4 layer at offset {offset}")
    return Packed4Layer(offset=start, end_offset=blob_end, cell_count=cell_count, byte_count=byte_count, blob=blob), blob_end


def decode_map_setting(data: bytes) -> MapSettingDocument:
    chunked, offset = parse_chunked_binary_layer(data, 0)
    packed_layers: list[Packed4Layer] = []
    while offset < len(data):
        packed, offset = parse_packed4_layer(data, offset)
        packed_layers.append(packed)
    if not packed_layers:
        raise DecodeError("map_setting has no packed4 layers after the chunked binary layer")
    return MapSettingDocument(chunked_binary_layer=chunked, packed4_layers=tuple(packed_layers))


def encode_chunked_binary_layer(layer: ChunkedBinaryLayer) -> bytes:
    out = bytearray()
    out += pack_u64(len(layer.groups))
    for group in layer.groups:
        out += pack_u64(len(group.grids))
        for grid in group.grids:
            out += pack_u64(len(grid.rows))
            for row in grid.rows:
                out += pack_u64(len(row))
                out += row
    return bytes(out)


def encode_packed4_layer(layer: Packed4Layer) -> bytes:
    if len(layer.blob) != layer.byte_count:
        raise ValueError("packed4 blob length no longer matches byte_count")
    if layer.byte_count * 2 != layer.cell_count:
        raise ValueError("packed4 byte_count no longer matches cell_count")
    return pack_u64(layer.cell_count) + pack_u64(layer.byte_count) + layer.blob


def encode_map_setting(document: MapSettingDocument) -> bytes:
    out = bytearray()
    out += encode_chunked_binary_layer(document.chunked_binary_layer)
    for layer in document.packed4_layers:
        out += encode_packed4_layer(layer)
    return bytes(out)


def nibble_histogram(blob: bytes) -> dict[str, int]:
    counter: Counter[int] = Counter()
    for byte in blob:
        counter[byte & 0x0F] += 1
        counter[byte >> 4] += 1
    return {str(key): counter[key] for key in sorted(counter)}


def chunked_layer_summary(layer: ChunkedBinaryLayer) -> dict[str, Any]:
    group_lengths: list[int] = []
    row_counts: list[int] = []
    row_widths: list[int] = []
    histogram: Counter[int] = Counter()
    for group in layer.groups:
        group_lengths.append(len(group.grids))
        for grid in group.grids:
            row_counts.append(len(grid.rows))
            for row in grid.rows:
                row_widths.append(len(row))
                histogram.update(row)

    unique_grid_counts = sorted(set(group_lengths))
    unique_row_counts = sorted(set(row_counts))
    unique_row_widths = sorted(set(row_widths))
    uniform = len(unique_grid_counts) == 1 and len(unique_row_counts) == 1 and len(unique_row_widths) == 1
    composed_size = None
    if uniform:
        composed_size = [unique_grid_counts[0] * unique_row_widths[0], len(layer.groups) * unique_row_counts[0]]

    return {
        "offset": layer.offset,
        "end_offset": layer.end_offset,
        "serialized_size": layer.end_offset - layer.offset,
        "group_count": len(layer.groups),
        "grid_counts_per_group": unique_grid_counts,
        "row_counts_per_grid": unique_row_counts,
        "row_widths": unique_row_widths,
        "uniform_shape": uniform,
        "composed_size": composed_size,
        "value_histogram": {str(key): histogram[key] for key in sorted(histogram)},
    }


def packed4_layer_summary(layer: Packed4Layer) -> dict[str, Any]:
    return {
        "offset": layer.offset,
        "end_offset": layer.end_offset,
        "serialized_size": layer.end_offset - layer.offset,
        "cell_count": layer.cell_count,
        "byte_count": layer.byte_count,
        "value_histogram": nibble_histogram(layer.blob),
        "payload_sha256": sha256_bytes(layer.blob),
    }


def first_difference(left: bytes, right: bytes, context: int = 16) -> dict[str, Any] | None:
    if left == right:
        return None
    limit = min(len(left), len(right))
    offset = 0
    while offset < limit and left[offset] == right[offset]:
        offset += 1
    start = max(0, offset - context)
    end = min(max(len(left), len(right)), offset + context + 1)
    return {
        "offset": offset,
        "input_size": len(left),
        "output_size": len(right),
        "input_context_hex": left[start : min(end, len(left))].hex(" "),
        "output_context_hex": right[start : min(end, len(right))].hex(" "),
    }


def is_inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPO_ROOT.resolve())
        return True
    except ValueError:
        return False


def ensure_evidence_path_is_outside_repo(path: Path) -> None:
    if is_inside_repo(path):
        raise SystemExit(f"Refusing to write map_setting round-trip evidence inside the repository: {path}")


def build_manifest(input_path: Path, output_path: Path, data: bytes, encoded: bytes, document: MapSettingDocument) -> dict[str, Any]:
    diff = first_difference(data, encoded)
    byte_identical = diff is None
    return {
        "probe": "map_setting_byte_identical_round_trip",
        "result": "pass" if byte_identical else "fail",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_size": len(data),
        "output_size": len(encoded),
        "input_sha256": sha256_bytes(data),
        "output_sha256": sha256_bytes(encoded),
        "byte_identical": byte_identical,
        "first_difference": diff,
        "decoded_layout": {
            "chunked_binary_layer": chunked_layer_summary(document.chunked_binary_layer),
            "packed4_layers": [packed4_layer_summary(layer) for layer in document.packed4_layers],
            "packed4_layer_count": len(document.packed4_layers),
            "consumed_bytes": document.packed4_layers[-1].end_offset,
            "trailing_bytes": 0,
        },
        "safety": {
            "raw_input_committed_to_repository": False,
            "raw_output_committed_to_repository": False,
            "field_mutations": False,
            "decode_scope": "structural framing only: chunked binary layer plus packed4 layer envelopes; gameplay fields remain uninterpreted",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def round_trip_file(
    input_path: Path,
    evidence_dir: Path,
    output_path: Path | None = None,
    manifest_path: Path | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    evidence_dir = evidence_dir.resolve()
    output_path = (output_path or evidence_dir / "map_setting.roundtrip.map_setting").resolve()
    manifest_path = (manifest_path or evidence_dir / "map_setting_round_trip_manifest.json").resolve()

    ensure_evidence_path_is_outside_repo(output_path)
    ensure_evidence_path_is_outside_repo(manifest_path)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    data = input_path.read_bytes()
    if expected_sha256 and sha256_bytes(data).lower() != expected_sha256.lower():
        raise SystemExit(
            f"Input SHA-256 {sha256_bytes(data)} does not match expected {expected_sha256}; refusing to round-trip."
        )

    document = decode_map_setting(data)
    encoded = encode_map_setting(document)
    output_path.write_bytes(encoded)

    manifest = build_manifest(input_path, output_path, data, encoded, document)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    if not manifest["byte_identical"]:
        diff = manifest["first_difference"]
        raise SystemExit(
            "map_setting round-trip is not byte-identical: "
            f"first difference at offset {diff['offset']} "
            f"(input_size={diff['input_size']}, output_size={diff['output_size']})"
        )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode and re-encode map_setting without field edits.")
    parser.add_argument("--input", type=Path, required=True, help="Local original map_setting binary. Never commit it.")
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        required=True,
        help="Repository-external directory for the re-encoded output and manifest.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional repository-external re-encoded output path.")
    parser.add_argument("--manifest", type=Path, default=None, help="Optional repository-external manifest path.")
    parser.add_argument(
        "--expected-sha256",
        default=MAP_SETTING_SHA256,
        help="Expected SHA-256 for the known local map_setting baseline. Pass an empty string to skip.",
    )
    args = parser.parse_args()

    expected_sha256 = args.expected_sha256 or None
    manifest = round_trip_file(
        input_path=args.input,
        evidence_dir=args.evidence_dir,
        output_path=args.output,
        manifest_path=args.manifest,
        expected_sha256=expected_sha256,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
