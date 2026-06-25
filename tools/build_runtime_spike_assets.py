from __future__ import annotations

import argparse
import binascii
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "mods"
    / "tfm2_lol_map_spike"
    / "aseprite_resources"
    / "ingame"
    / "5v5"
    / "background_5v5.png"
)


def png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    checksum = binascii.crc32(chunk_type)
    checksum = binascii.crc32(payload, checksum) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", checksum)


def build_solid_png(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    pixel = bytes(rgba)
    row = b"\x00" + pixel * width
    raw = row * height
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", header),
            png_chunk(b"IDAT", zlib.compress(raw, level=9)),
            png_chunk(b"IEND", b""),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic diagnostic assets for the runtime map spike.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--size", type=int, default=1280)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(build_solid_png(args.size, args.size, (24, 210, 196, 255)))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
