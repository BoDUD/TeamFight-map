from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME_ROOT = REPO_ROOT.parent
MOD_ID = "tfm2_lol_anchor_probe"
SOURCE_MOD = REPO_ROOT / "mods" / MOD_ID
DLL_NAME = f"{MOD_ID}.dll"
DEFAULT_EVIDENCE_DIR = DEFAULT_GAME_ROOT / "stage_runtime_node_anchor_evidence" / "runtime_node_anchor_probe"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def is_inside_repo(path: Path) -> bool:
    resolved = path.resolve()
    repo = REPO_ROOT.resolve()
    return resolved == repo or repo in resolved.parents


def ensure_evidence_dir_outside_repo(path: Path) -> Path:
    resolved = path.resolve()
    if is_inside_repo(resolved):
        raise SystemExit(f"Refusing to write runtime anchor evidence inside the repository: {resolved}")
    return resolved


def paths_are_same_existing_file(left: Path, right: Path) -> bool:
    try:
        return left.exists() and right.exists() and left.samefile(right)
    except OSError:
        return False


def validate_source_mod() -> None:
    if not SOURCE_MOD.is_dir():
        raise SystemExit(f"Missing source mod package: {SOURCE_MOD}")
    metadata = read_json(SOURCE_MOD / "mod.mod_info")
    if metadata.get("mod_id") != MOD_ID:
        raise SystemExit(f"Source mod metadata has wrong mod_id: {metadata.get('mod_id')!r}")
    forbidden = [
        SOURCE_MOD / "mod.override_info",
        SOURCE_MOD / "setting" / "map_setting.map_setting",
        SOURCE_MOD / "aseprite_resources" / "ingame" / "5v5" / "background_5v5.png",
    ]
    present = [path for path in forbidden if path.exists()]
    if present:
        raise SystemExit(f"Source anchor probe contains forbidden runtime override files: {present}")


def target_mod_dir(game_root: Path) -> Path:
    return game_root / "mods" / MOD_ID


def ensure_delete_target_is_safe(game_root: Path, target: Path) -> None:
    resolved_target = target.resolve()
    expected_parent = (game_root / "mods").resolve()
    if resolved_target.parent != expected_parent or resolved_target.name != MOD_ID:
        raise SystemExit(f"Refusing to delete unexpected anchor probe path: {resolved_target}")
    if SOURCE_MOD.resolve() == resolved_target:
        raise SystemExit("Refusing to install over the repository source anchor probe package.")


def forbidden_installed_paths(installed_mod: Path) -> list[Path]:
    if not installed_mod.exists():
        return []
    forbidden: list[Path] = []
    for path in installed_mod.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(installed_mod).as_posix()
        if relative == "mod.override_info":
            forbidden.append(path)
        if relative == "setting/map_setting.map_setting":
            forbidden.append(path)
        if relative == "aseprite_resources/ingame/5v5/background_5v5.png":
            forbidden.append(path)
    return forbidden


def ensure_installed_package_has_no_overrides(installed_mod: Path) -> None:
    forbidden = forbidden_installed_paths(installed_mod)
    if forbidden:
        raise SystemExit(
            "Installed anchor probe contains forbidden override artifacts; rerun with --clean after inspection: "
            + ", ".join(str(path) for path in forbidden)
        )


def update_mod_config(game_root: Path, exclusive: bool) -> None:
    config_path = game_root / "config" / "game" / "mods.json"
    if not config_path.is_file():
        raise SystemExit(f"Missing mods config: {config_path}")
    config = read_json(config_path)
    if exclusive:
        config["enabled_mods"] = [MOD_ID]
    else:
        enabled = list(config.get("enabled_mods", []))
        if MOD_ID not in enabled:
            enabled.append(MOD_ID)
        config["enabled_mods"] = enabled
    accepted = list(config.get("accepted_code_mod_warnings", []))
    if MOD_ID not in accepted:
        accepted.append(MOD_ID)
    config["accepted_code_mod_warnings"] = accepted
    config_path.write_text(json.dumps(config, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def installed_files(installed_mod: Path) -> list[str]:
    return sorted(
        str(path.relative_to(installed_mod)).replace("\\", "/")
        for path in installed_mod.rglob("*")
        if path.is_file()
    )


def install_anchor_probe(
    game_root: Path,
    dll: Path,
    evidence_dir: Path,
    *,
    clean: bool = False,
    enable_exclusive: bool = False,
) -> dict[str, Any]:
    validate_source_mod()
    game_root = game_root.resolve()
    dll = dll.resolve()
    evidence_dir = ensure_evidence_dir_outside_repo(evidence_dir)
    if is_inside_repo(dll):
        raise SystemExit(f"Probe DLL source must be outside the repository: {dll}")
    if not (game_root / "TeamfightManager2.exe").is_file():
        raise SystemExit(f"Game root does not contain TeamfightManager2.exe: {game_root}")
    if not dll.is_file():
        raise SystemExit(f"Probe DLL is not a file: {dll}")
    if dll.suffix.lower() != ".dll":
        raise SystemExit(f"Probe binary must be a DLL: {dll}")

    target = target_mod_dir(game_root)
    ensure_delete_target_is_safe(game_root, target)
    if clean and target.exists():
        shutil.rmtree(target)
    ensure_installed_package_has_no_overrides(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_MOD, target, dirs_exist_ok=True)
    ensure_installed_package_has_no_overrides(target)

    target_dll = target / DLL_NAME
    if dll == target_dll.resolve() or paths_are_same_existing_file(dll, target_dll):
        raise SystemExit("Probe DLL source and installed target are the same file.")
    shutil.copy2(dll, target_dll)

    evidence_dir.mkdir(parents=True, exist_ok=True)
    (target / "probe_evidence_dir.txt").write_text(str(evidence_dir) + "\n", encoding="utf-8", newline="\n")
    ensure_installed_package_has_no_overrides(target)

    if enable_exclusive:
        update_mod_config(game_root, exclusive=True)

    source_size = dll.stat().st_size
    target_size = target_dll.stat().st_size
    source_sha = sha256_file(dll)
    target_sha = sha256_file(target_dll)
    byte_equal = dll.read_bytes() == target_dll.read_bytes()
    if source_size != target_size or source_sha != target_sha or not byte_equal:
        raise SystemExit("Installed DLL failed byte-equivalence checks.")

    manifest = {
        "probe": "runtime_node_anchor_read_only",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mod_id": MOD_ID,
        "game_root": str(game_root),
        "installed_mod": str(target),
        "dll_source": str(dll),
        "dll_target": str(target_dll),
        "probe_dll_size": target_size,
        "probe_dll_sha256": target_sha,
        "byte_equal": byte_equal,
        "map_setting_override_installed": False,
        "asset_overrides_installed": False,
        "mod_override_info_present": (target / "mod.override_info").exists(),
        "scene_mutated": False,
        "anchor_surface": "post_update_only_pending_runtime",
        "anchors": [],
        "candidate_transform": None,
        "map_setting_node_world_transform": "unproven",
        "installed_files": installed_files(target),
        "enable_exclusive": enable_exclusive,
    }
    write_json(evidence_dir / "probe_manifest.json", manifest)
    print(f"Installed read-only anchor probe: {target}")
    print(f"Wrote evidence manifest: {evidence_dir / 'probe_manifest.json'}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the read-only runtime node anchor probe mod.")
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--enable-exclusive", action="store_true")
    args = parser.parse_args()

    install_anchor_probe(
        args.game_root,
        args.dll,
        args.evidence_dir,
        clean=args.clean,
        enable_exclusive=args.enable_exclusive,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
