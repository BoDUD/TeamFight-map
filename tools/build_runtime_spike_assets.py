from __future__ import annotations

import argparse
import binascii
import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw


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


def npoint(x: float, y: float, size: int) -> tuple[int, int]:
    return int(round(x / 100 * size)), int(round(y / 100 * size))


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


def add_layer(base: Image.Image, layer: Image.Image) -> None:
    base.alpha_composite(layer)


def draw_polyline(
    layer: Image.Image,
    points: list[tuple[float, float]],
    size: int,
    width: int,
    fill: tuple[int, int, int, int],
    joint: str = "curve",
) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    draw.line([npoint(x, y, size) for x, y in points], fill=fill, width=width, joint=joint)


def draw_ring(
    layer: Image.Image,
    center: tuple[float, float],
    size: int,
    radius: int,
    fill: tuple[int, int, int, int],
    width: int,
) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    cx, cy = npoint(center[0], center[1], size)
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(box, outline=fill, width=width)


def base_terrain(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    pixels = image.load()
    for y in range(size):
        vertical = y / max(1, size - 1)
        for x in range(size):
            diagonal = (x + y) / max(1, size * 2 - 2)
            ripple = (
                math.sin((x * 0.031) + (y * 0.017))
                + math.sin((x * 0.011) - (y * 0.029))
                + math.cos((x + y) * 0.021)
            ) / 3
            noise = ((x * 37 + y * 19 + (x // 13) * 11 + (y // 17) * 7) % 29) - 14
            r = int(39 + 15 * diagonal + 8 * ripple + noise * 0.28)
            g = int(77 + 24 * (1 - vertical) + 9 * ripple + noise * 0.35)
            b = int(65 + 17 * vertical + 7 * ripple + noise * 0.24)
            pixels[x, y] = (
                max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)),
                255,
            )
    return image


def draw_lanes(image: Image.Image, size: int) -> None:
    lane_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    lane_outer = (120, 98, 68, 132)
    lane_inner = (174, 145, 88, 102)
    lane_highlight = (224, 193, 116, 48)
    lanes = [
        [(8, 92), (8, 8), (92, 8)],
        [(8, 92), (50, 50), (92, 8)],
        [(8, 92), (92, 92), (92, 8)],
    ]
    for lane in lanes:
        draw_polyline(lane_layer, lane, size, 112, lane_outer)
        draw_polyline(lane_layer, lane, size, 76, lane_inner)
        draw_polyline(lane_layer, lane, size, 18, lane_highlight)
    add_layer(image, lane_layer)


def draw_river(image: Image.Image, size: int) -> None:
    river = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_polyline(river, [(16, 15), (50, 50), (84, 85)], size, 176, (19, 105, 116, 164))
    draw_polyline(river, [(16, 15), (50, 50), (84, 85)], size, 118, (34, 162, 166, 132))
    draw_polyline(river, [(16, 15), (50, 50), (84, 85)], size, 34, (105, 224, 216, 58))
    draw = ImageDraw.Draw(river, "RGBA")
    for offset in range(-5, 6):
        alpha = max(0, 34 - abs(offset) * 5)
        draw_polyline(
            river,
            [(16 + offset * 0.8, 15 - offset * 0.5), (50, 50), (84 + offset * 0.8, 85 - offset * 0.5)],
            size,
            5,
            (157, 239, 230, alpha),
        )
    for center in ((37, 37), (63, 63)):
        cx, cy = npoint(center[0], center[1], size)
        draw.ellipse((cx - 86, cy - 52, cx + 86, cy + 52), fill=(25, 131, 144, 68))
    add_layer(image, river)


def draw_jungle_and_objectives(image: Image.Image, size: int) -> None:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    regions = [
        ([(13, 74), (18, 55), (35, 48), (42, 63), (28, 76)], (34, 103, 60, 82)),
        ([(30, 88), (46, 72), (61, 78), (57, 91), (40, 96)], (47, 121, 63, 78)),
        ([(40, 22), (55, 10), (70, 14), (54, 28), (45, 28)], (46, 113, 64, 76)),
        ([(59, 37), (83, 24), (88, 45), (66, 52), (61, 47)], (33, 102, 60, 82)),
    ]
    for points, color in regions:
        draw.polygon([npoint(x, y, size) for x, y in points], fill=color)
    for x in range(0, size, 36):
        for y in range(0, size, 36):
            if (x * 3 + y * 5) % 11 in (0, 1, 2):
                draw.ellipse((x - 8, y - 5, x + 21, y + 13), fill=(96, 142, 75, 22))
    for center, tint in [((28, 28), (149, 120, 82, 118)), ((72, 72), (112, 92, 146, 105))]:
        draw_ring(layer, center, size, 92, tint, 9)
        draw_ring(layer, center, size, 56, (219, 202, 146, 48), 4)
    add_layer(image, layer)


def draw_bases_and_frame(image: Image.Image, size: int) -> None:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    for center, color in [((8, 92), (72, 142, 232, 78)), ((92, 8), (226, 80, 96, 70))]:
        cx, cy = npoint(center[0], center[1], size)
        for radius, alpha_scale in ((132, 0.35), (88, 0.55), (46, 0.82)):
            fill = (color[0], color[1], color[2], int(color[3] * alpha_scale))
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=fill)
    draw.rectangle((18, 18, size - 19, size - 19), outline=(215, 195, 132, 52), width=5)
    draw.rectangle((34, 34, size - 35, size - 35), outline=(17, 48, 45, 82), width=7)
    add_layer(image, layer)


def draw_subtle_tilework(image: Image.Image, size: int) -> None:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    step = size // 16
    for index in range(1, 16):
        alpha = 14 if index % 4 else 22
        pos = index * step
        draw.line((pos, 0, pos, size), fill=(227, 215, 155, alpha), width=1)
        draw.line((0, pos, size, pos), fill=(4, 25, 25, alpha), width=1)
    add_layer(image, layer)


def build_lol_like_background(size: int = 1280) -> Image.Image:
    image = base_terrain(size)
    draw_jungle_and_objectives(image, size)
    draw_river(image, size)
    draw_lanes(image, size)
    draw_bases_and_frame(image, size)
    draw_subtle_tilework(image, size)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the visual-only LOL-like runtime map skin background.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--size", type=int, default=1280)
    args = parser.parse_args()

    if args.size <= 0:
        raise SystemExit("--size must be positive.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(png_bytes(build_lol_like_background(args.size)))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
