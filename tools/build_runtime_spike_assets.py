from __future__ import annotations

import argparse
import binascii
import struct
from pathlib import Path

from PIL import Image


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
DEFAULT_SOURCE = REPO_ROOT / "assets" / "visual" / "lol_skin" / "background_5v5_imagegen_source.png"


def png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    checksum = binascii.crc32(chunk_type)
    checksum = binascii.crc32(payload, checksum) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", checksum)


def adler32(data: bytes) -> int:
    modulus = 65521
    a = 1
    b = 0
    for offset in range(0, len(data), 5552):
        chunk = data[offset : offset + 5552]
        for value in chunk:
            a = (a + value) % modulus
            b = (b + a) % modulus
    return (b << 16) | a


def zlib_stored_stream(data: bytes) -> bytes:
    parts = [b"\x78\x01"]
    for offset in range(0, len(data), 65535):
        block = data[offset : offset + 65535]
        final = offset + 65535 >= len(data)
        parts.append(bytes([1 if final else 0]))
        parts.append(struct.pack("<HH", len(block), 0xFFFF - len(block)))
        parts.append(block)
    parts.append(struct.pack(">I", adler32(data)))
    return b"".join(parts)


def png_bytes(image: Image.Image) -> bytes:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    raw_pixels = rgba.tobytes()
    stride = width * 4
    raw = b"".join(b"\x00" + raw_pixels[y * stride : (y + 1) * stride] for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", header),
            png_chunk(b"IDAT", zlib_stored_stream(raw)),
            png_chunk(b"IEND", b""),
        ]
    )


def tone_for_runtime_readability(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = bytearray(rgba.tobytes())
    for offset in range(0, len(pixels), 4):
        r = pixels[offset]
        g = pixels[offset + 1]
        b = pixels[offset + 2]
        gray = (r * 30 + g * 59 + b * 11) // 100
        pixels[offset] = max(0, min(255, (r * 76 + gray * 24) // 100 - 12))
        pixels[offset + 1] = max(0, min(255, (g * 78 + gray * 22) // 100 - 10))
        pixels[offset + 2] = max(0, min(255, (b * 82 + gray * 18) // 100 - 8))
        pixels[offset + 3] = 255
    return Image.frombytes("RGBA", rgba.size, bytes(pixels))


def build_lol_like_background(size: int = 1280, source: Path = DEFAULT_SOURCE) -> Image.Image:
    if not source.is_file():
        raise SystemExit(f"Missing image-gen source asset: {source}")
    with Image.open(source) as original:
        image = original.convert("RGBA")
        if image.size != (size, size):
            image = image.resize((size, size), Image.Resampling.LANCZOS)
    return tone_for_runtime_readability(image)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the visual-only LOL-like runtime map skin background.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--size", type=int, default=1280)
    args = parser.parse_args()

    if args.size <= 0:
        raise SystemExit("--size must be positive.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(png_bytes(build_lol_like_background(args.size, args.source)))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
