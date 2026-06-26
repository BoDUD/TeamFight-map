from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME_ROOT = REPO_ROOT.parent
DEFAULT_SDK_DIR = DEFAULT_GAME_ROOT / "mod-sdk"
DEFAULT_ADJACENT_RIFT_SOURCE = DEFAULT_GAME_ROOT / "TeamFightManger2-Map" / "rift_manager" / "src" / "lib.rs"


@dataclass(frozen=True)
class Surface:
    name: str
    patterns: tuple[str, ...]
    anchor_data_type: str
    read_only_note: str
    enough_note: str


SURFACES: tuple[Surface, ...] = (
    Surface(
        "ModExtension::post_update",
        (r"\bfn\s+post_update\b", r"\bimpl\s+ModExtension\b"),
        "callback",
        "usable as a read-only entrypoint if the implementation does not mutate its &mut parameters",
        "not enough by itself; it only proves a DLL can run",
    ),
    Surface(
        "Scene",
        (r"\bScene\b",),
        "opaque runtime scene parameter",
        "can be received by reference",
        "not enough unless public fields or methods expose world anchors",
    ),
    Surface(
        "GameUI",
        (r"\bGameUI\b",),
        "opaque UI parameter",
        "can be received by reference",
        "not enough unless public draw/text/screen transform methods exist",
    ),
    Surface(
        "Assets",
        (r"\bAssets\b",),
        "opaque assets parameter",
        "can be received by reference",
        "not enough for node/world anchoring",
    ),
    Surface(
        "ServerModContext",
        (r"\bServerModContext\b",),
        "server context",
        "unknown",
        "not enough unless it exposes map/world data read-only",
    ),
    Surface(
        "database.map_setting",
        (r"\bdatabase\s*\.\s*map_setting\b", r"\bdatabase\s*\(\)\s*\.\s*map_setting\b"),
        "map setting data",
        "unknown",
        "potentially enough only if coordinates or node tables are readable",
    ),
    Surface(
        "map_setting.visible_view",
        (r"\bvisible_view\b",),
        "rectangle/bounds",
        "unknown",
        "could be enough only if tied to world/camera coordinates",
    ),
    Surface(
        "map_setting.path",
        (r"\bmap_setting\s*\.\s*path\b", r"\bmap_setting\s*\(\)\s*\.\s*path\b"),
        "grid/table",
        "unknown",
        "could be enough only if dimensions and world transform are exposed",
    ),
    Surface(
        "camera / viewport",
        (r"\bcamera\b", r"\bviewport\b"),
        "view bounds",
        "unknown",
        "could help align background UV and world coordinates",
    ),
    Surface(
        "world_to_screen / screen_to_world",
        (r"\bworld_to_screen\b", r"\bscreen_to_world\b"),
        "coordinate transform",
        "unknown",
        "strong anchor surface if public and callable read-only",
    ),
    Surface(
        "draw / text / debug overlay",
        (r"\bdraw\b", r"\btext\b", r"\bdebug\b", r"\boverlay\b"),
        "screen/world marker output",
        "unknown",
        "strong validation surface only if it can draw/log anchors without mutation",
    ),
    Surface(
        "logging",
        (r"\blog\b", r"\bprintln!\b", r"\beprintln!\b"),
        "diagnostic output",
        "safe if external-only",
        "not enough unless logged values include independent anchors",
    ),
    Surface(
        "tower / nexus / actor position",
        (r"\btower\b", r"\bnexus\b", r"\bactor\b", r"\bposition\b", r"\bpos\b"),
        "known world entity position",
        "unknown",
        "strong anchor surface if exposed with world coordinates",
    ),
)


TEXT_GLOBS = ("*.rs", "*.toml", "*.ps1", "*.bat", "*.txt", "*.md")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files(sdk_dir: Path, extra_sources: list[Path]) -> list[Path]:
    files: list[Path] = []
    for pattern in TEXT_GLOBS:
        files.extend(path for path in sdk_dir.rglob(pattern) if path.is_file())
    for extra in extra_sources:
        if extra.is_file():
            files.append(extra)
    return sorted(set(files))


def relative_label(path: Path, roots: list[Path]) -> str:
    for root in roots:
        try:
            return str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            continue
    return str(path)


def collect_hits(files: list[Path], surface: Surface, roots: list[Path], limit: int = 8) -> list[dict[str, Any]]:
    compiled = [re.compile(pattern) for pattern in surface.patterns]
    hits: list[dict[str, Any]] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in compiled):
                hits.append(
                    {
                        "file": relative_label(path, roots),
                        "line": lineno,
                        "snippet": line.strip()[:160],
                    }
                )
                if len(hits) >= limit:
                    return hits
    return hits


def audit_sdk(sdk_dir: Path, extra_sources: list[Path]) -> dict[str, Any]:
    sdk_dir = sdk_dir.resolve()
    extra_sources = [source.resolve() for source in extra_sources if source.exists()]
    files = source_files(sdk_dir, extra_sources)
    roots = [sdk_dir, *[source.parent for source in extra_sources]]
    rows = []
    for surface in SURFACES:
        hits = collect_hits(files, surface, roots)
        public = bool(hits)
        enough = public and surface.name in {
            "world_to_screen / screen_to_world",
            "tower / nexus / actor position",
        }
        rows.append(
            {
                "api_surface": surface.name,
                "public_in_checked_sources": public,
                "read_only_usable": public and surface.name in {"ModExtension::post_update", "Scene", "GameUI", "Assets"},
                "anchor_data_type": surface.anchor_data_type,
                "enough_for_anchor": enough,
                "read_only_note": surface.read_only_note,
                "enough_note": surface.enough_note,
                "hits": hits,
            }
        )

    anchor_ready = any(row["enough_for_anchor"] for row in rows)
    return {
        "schema": "tfm2.runtime_node_anchor_api_audit.v1",
        "sdk_dir": str(sdk_dir),
        "sdk_source_file_count": len(files),
        "source_files": [
            {
                "path": relative_label(path, roots),
                "sha256": sha256_file(path),
            }
            for path in files
        ],
        "surfaces": rows,
        "result": {
            "runtime_node_anchor_api": "candidate_surface_found" if anchor_ready else "unavailable_in_checked_public_sdk_sources",
            "map_setting_node_world_transform": "unproven",
            "candidate_369_370": "blocked",
        },
    }


def is_inside_repo(path: Path) -> bool:
    resolved = path.resolve()
    repo = REPO_ROOT.resolve()
    return resolved == repo or repo in resolved.parents


def paths_are_same_existing_file(left: Path, right: Path) -> bool:
    try:
        return left.exists() and right.exists() and left.samefile(right)
    except OSError:
        return False


def ensure_audit_output_is_safe(output: Path, sdk_dir: Path, extra_sources: list[Path]) -> Path:
    resolved = output.resolve()
    sdk = sdk_dir.resolve()
    if is_inside_repo(resolved):
        raise SystemExit(f"Refusing to write SDK audit evidence inside the repository: {resolved}")
    if resolved == sdk or sdk in resolved.parents:
        raise SystemExit(f"Refusing to write SDK audit evidence inside the checked SDK directory: {resolved}")
    for source in source_files(sdk, extra_sources):
        checked_source = source.resolve()
        if resolved == checked_source or paths_are_same_existing_file(resolved, checked_source):
            raise SystemExit(f"Refusing to overwrite checked source file: {resolved}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit public SDK/source surfaces for read-only runtime node anchoring.")
    parser.add_argument("--sdk-dir", type=Path, default=DEFAULT_SDK_DIR)
    parser.add_argument(
        "--include-adjacent-rift-source",
        action="store_true",
        help="Include the adjacent old rift_manager Rust skeleton as a local reference if present.",
    )
    parser.add_argument("--extra-source", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    extra_sources = list(args.extra_source)
    if args.include_adjacent_rift_source:
        extra_sources.append(DEFAULT_ADJACENT_RIFT_SOURCE)
    output = ensure_audit_output_is_safe(args.output, args.sdk_dir, extra_sources) if args.output else None
    audit = audit_sdk(args.sdk_dir, extra_sources)
    text = json.dumps(audit, indent=2, ensure_ascii=False) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
