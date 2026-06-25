from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any

try:
    from .validate_map_design import DEFAULT_LAYOUT, load_layout
except ImportError:
    from validate_map_design import DEFAULT_LAYOUT, load_layout


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SVG = REPO_ROOT / "assets" / "graybox" / "tfm2_lol_like_map.svg"
DEFAULT_TOPOLOGY = REPO_ROOT / "assets" / "graybox" / "tfm2_lol_like_map_topology.mmd"


def point_text(point: list[float]) -> str:
    return f"{point[0]},{point[1]}"


def attr_text(attrs: dict[str, str]) -> str:
    return " ".join(f'{key.replace("_", "-")}="{html.escape(value)}"' for key, value in attrs.items())


def polyline(points: list[list[float]], **attrs: str) -> str:
    return f'<polyline points="{" ".join(point_text(point) for point in points)}" {attr_text(attrs)} />'


def circle(center: list[float], radius: float, **attrs: str) -> str:
    return f'<circle cx="{center[0]}" cy="{center[1]}" r="{radius}" {attr_text(attrs)} />'


def rect(center: list[float], size: list[float], **attrs: str) -> str:
    x = center[0] - size[0] / 2
    y = center[1] - size[1] / 2
    return f'<rect x="{x}" y="{y}" width="{size[0]}" height="{size[1]}" {attr_text(attrs)} />'


def label(text: str, center: list[float], size: float = 3, color: str = "#1d2433") -> str:
    return (
        f'<text x="{center[0]}" y="{center[1]}" font-size="{size}" '
        f'font-family="Arial, sans-serif" text-anchor="middle" fill="{color}">'
        f'{html.escape(text)}</text>'
    )


def build_svg(layout: dict[str, Any]) -> str:
    parts: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="1200" height="1200">',
        '<rect x="0" y="0" width="100" height="100" fill="#edf0e5" stroke="#28313f" stroke-width="0.8" />',
        '<rect x="2" y="2" width="96" height="96" fill="none" stroke="#6d7888" stroke-width="0.4" stroke-dasharray="1 1" />'
    ]

    parts.append(polyline(layout["river"]["main_axis"], fill="none", stroke="#65aeda", stroke_width="9", stroke_linecap="round", opacity="0.7"))
    parts.append(polyline(layout["river"]["main_axis"], fill="none", stroke="#2f77a5", stroke_width="1.2", stroke_dasharray="2 1", opacity="0.85"))

    lane_styles = {
        "LANE_TOP": "#b58642",
        "LANE_MID": "#c06554",
        "LANE_BOTTOM": "#7d9140"
    }
    for lane in layout["lanes"]:
        parts.append(polyline(lane["centerline"], fill="none", stroke=lane_styles[lane["id"]], stroke_width="2.2", stroke_linejoin="round", opacity="0.9"))
        mid = lane["centerline"][len(lane["centerline"]) // 2]
        parts.append(label(lane["name_zh"], [mid[0], mid[1] - 2], 3))

    for half in layout["jungle"]["half_jungles"]:
        loop = half["main_loop"]
        if loop[0] != loop[-1]:
            loop = loop + [loop[0]]
        color = "#4d8b57" if half["team"] == "blue" else "#9c5c55"
        parts.append(polyline(loop, fill="none", stroke=color, stroke_width="1.4", stroke_dasharray="2 1", opacity="0.9"))
        parts.append(label(half["name_zh"], half["center"], 2, color))

    for gate in layout["gates"]:
        color = {
            "lane_to_river": "#ffffff",
            "jungle_lane_exit": "#f0c36b",
            "jungle_to_river": "#9fe0ff",
            "pit_entry": "#fff07a"
        }[gate["kind"]]
        parts.append(circle(gate["center"], 0.75, fill=color, stroke="#313844", stroke_width="0.2", opacity="0.9"))

    for objective in layout["objectives"]:
        fill = "#8ab6d8" if objective["id"] == "PIT_MORGARD" else "#90b66f"
        parts.append(circle(objective["center"], 5.3, fill=fill, stroke="#26313d", stroke_width="0.6", opacity="0.92"))
        parts.append(label(objective["name_zh"], [objective["center"][0], objective["center"][1] + 0.8], 2.4))
        for entrance in objective["entrances"]:
            parts.append(circle(entrance["center"], 1.2, fill="#fff9c9", stroke="#4c5565", stroke_width="0.3"))

    for brush in layout["functional_brush"]:
        parts.append(rect(brush["center"], brush["size"], fill="#286d3b", stroke="#173d23", stroke_width="0.25", opacity="0.82"))

    for slot in layout["vision_slots"]:
        parts.append(circle(slot["center"], 1.35, fill="#f3d45b", stroke="#7a5c00", stroke_width="0.25", opacity="0.95"))

    for camp in layout["jungle"]["camps"]:
        fill = {
            "economy": "#deb65b",
            "combat_core": "#d66855",
            "spirit_core": "#8d6bd1"
        }[camp["kind"]]
        parts.append(circle(camp["center"], 1.8, fill=fill, stroke="#3a3140", stroke_width="0.35"))

    for tower in layout["towers"]:
        if tower["tier"] == "base_guard":
            size = [2.5, 2.5]
            fill = "#3f65a6" if tower["team"] == "blue" else "#b04444"
        elif tower["tier"] == 1:
            size = [2.2, 2.2]
            fill = "#6f8fc9" if tower["team"] == "blue" else "#cf7771"
        else:
            size = [2.8, 2.8]
            fill = "#496aa8" if tower["team"] == "blue" else "#a54949"
        parts.append(rect(tower["center"], size, fill=fill, stroke="#272c33", stroke_width="0.3"))

    for anchor_id in ("BASE_BLUE", "BASE_RED"):
        anchor = layout["anchors"][anchor_id]
        fill = "#315aa4" if anchor_id == "BASE_BLUE" else "#a23636"
        parts.append(circle(anchor["center"], 4.2, fill=fill, stroke="#111820", stroke_width="0.5", opacity="0.9"))
        parts.append(label(anchor["name_zh"], [anchor["center"][0], anchor["center"][1] + 0.8], 2.3, "#ffffff"))

    parts.extend(
        [
            label("功能草丛 12 组", [18, 4.5], 2.5),
            label("河道入口 8 个", [50, 4.5], 2.5),
            label("双坑各 2 入口", [82, 4.5], 2.5),
            "</svg>"
        ]
    )
    return "\n".join(parts)


def build_topology(layout: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    labels = {code: code for code in layout["region_codes"]}
    labels["BRIDGE_MID"] = "BRIDGE_MID"
    labels.update({gate["id"]: gate["id"] for gate in layout["gates"]})
    for edge in layout["topology"]["edges"]:
        a, b = edge
        lines.append(f"    {a}[{labels[a]}] --- {b}[{labels[b]}]")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build graybox previews for the LOL-like map data.")
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    parser.add_argument("--svg", type=Path, default=DEFAULT_SVG)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    args = parser.parse_args()

    layout = load_layout(args.layout)
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.topology.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text(build_svg(layout), encoding="utf-8", newline="\n")
    args.topology.write_text(build_topology(layout), encoding="utf-8", newline="\n")
    print(f"Wrote {args.svg}")
    print(f"Wrote {args.topology}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
