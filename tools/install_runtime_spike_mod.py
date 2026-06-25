from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MOD_ID = "tfm2_lol_map_spike"
SOURCE_MOD = REPO_ROOT / "mods" / MOD_ID
BASE_BACKGROUND_ASSET = "asset/base/aseprite_resources/ingame/5v5/background_5v5"
MAP_SETTING_ASSET = "asset/base/setting/map_setting"
MAP_SETTING_REMAP = f"asset/{MOD_ID}/setting/map_setting"
MAP_SETTING_STAGED_RELATIVE_PATH = Path("setting") / "map_setting.map_setting"


def infer_game_root() -> Path:
    candidate = REPO_ROOT.parent
    if (candidate / "TeamfightManager2.exe").exists() and (candidate / "mods").exists():
        return candidate
    raise SystemExit("Could not infer game root. Pass --game-root explicitly.")


def ensure_target_is_safe(game_root: Path, target: Path) -> None:
    resolved_root = game_root.resolve()
    resolved_target = target.resolve()
    expected_parent = (resolved_root / "mods").resolve()
    if resolved_target.name != MOD_ID or resolved_target.parent != expected_parent:
        raise SystemExit(f"Refusing to modify unexpected target: {resolved_target}")


def copy_mod(game_root: Path, clean: bool) -> Path:
    if not SOURCE_MOD.exists():
        raise SystemExit(f"Missing source mod package: {SOURCE_MOD}")

    target = game_root / "mods" / MOD_ID
    ensure_target_is_safe(game_root, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if clean and target.exists():
        shutil.rmtree(target)
    shutil.copytree(SOURCE_MOD, target, dirs_exist_ok=True)
    return target


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files_are_byte_equal(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as left_handle, right.open("rb") as right_handle:
        while True:
            left_chunk = left_handle.read(1024 * 1024)
            right_chunk = right_handle.read(1024 * 1024)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return True


def load_override_table(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        table = json.load(handle)
    if MAP_SETTING_ASSET in table:
        raise SystemExit("Installed override already contains map_setting; run with --clean to reset before staging.")
    if BASE_BACKGROUND_ASSET not in table:
        raise SystemExit(f"Installed override is missing required background probe: {BASE_BACKGROUND_ASSET}")
    return table


def stage_map_setting_equivalent(game_root: Path, installed_mod: Path, source: Path) -> Path:
    source = source.resolve()
    if not source.is_file():
        raise SystemExit(f"map_setting source is not a file: {source}")

    target = installed_mod / MAP_SETTING_STAGED_RELATIVE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

    source_size = source.stat().st_size
    target_size = target.stat().st_size
    source_sha = sha256_file(source)
    target_sha = sha256_file(target)
    byte_equal = files_are_byte_equal(source, target)

    if source_size != target_size or source_sha != target_sha or not byte_equal:
        raise SystemExit("Copied map_setting failed byte-equivalence checks; refusing to stage override.")

    override_path = installed_mod / "mod.override_info"
    overrides = load_override_table(override_path)
    overrides[MAP_SETTING_ASSET] = {"remapping": MAP_SETTING_REMAP, "type": "override"}
    override_path.write_text(json.dumps(overrides, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    manifest_dir = game_root / "stage_runtime_spike_evidence" / "runtime_map_loading_spike"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "map_setting_equivalent_manifest.json"
    base_version_path = game_root / "mod-sdk" / "base_version.txt"
    game_exe = game_root / "TeamfightManager2.exe"
    manifest = {
        "probe": "map_setting_equivalent",
        "mod_id": MOD_ID,
        "game_root": str(game_root),
        "game_exe": str(game_exe),
        "game_exe_size": game_exe.stat().st_size if game_exe.exists() else None,
        "game_exe_sha256": sha256_file(game_exe) if game_exe.exists() else None,
        "base_version": base_version_path.read_text(encoding="utf-8").strip() if base_version_path.exists() else None,
        "source_path": str(source),
        "target_path": str(target),
        "override_path": str(override_path),
        "asset_key": MAP_SETTING_ASSET,
        "remapping": MAP_SETTING_REMAP,
        "source_size": source_size,
        "target_size": target_size,
        "source_sha256": source_sha,
        "target_sha256": target_sha,
        "byte_equal": byte_equal,
        "committed_to_repository": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Staged byte-equivalent map_setting override in installed mod only: {target}")
    print(f"Wrote evidence manifest: {manifest_path}")
    return manifest_path


def load_mod_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "enabled_mods": [],
            "known_workshop_mods": [],
            "accepted_code_mod_warnings": [],
            "accepted_save_mod_mismatch_warnings": [],
        }
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def enable_mod(game_root: Path, exclusive: bool) -> Path:
    config_path = game_root / "config" / "game" / "mods.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = load_mod_config(config_path)
    enabled = [MOD_ID] if exclusive else list(dict.fromkeys([*config.get("enabled_mods", []), MOD_ID]))
    config["enabled_mods"] = enabled
    for key in ("known_workshop_mods", "accepted_code_mod_warnings", "accepted_save_mod_mismatch_warnings"):
        config.setdefault(key, [])
    config_path.write_text(json.dumps(config, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    return config_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the runtime map spike into a local TFM2 game folder.")
    parser.add_argument("--game-root", type=Path, default=None)
    parser.add_argument("--clean", action="store_true", help="Replace the existing installed spike folder after safety checks.")
    parser.add_argument("--enable", action="store_true", help="Add tfm2_lol_map_spike to config/game/mods.json.")
    parser.add_argument("--enable-exclusive", action="store_true", help="Enable only tfm2_lol_map_spike for isolated runtime QA.")
    parser.add_argument(
        "--stage-map-setting-equivalent",
        action="store_true",
        help="Stage an unmodified map_setting remap in the installed game mod only.",
    )
    parser.add_argument(
        "--map-setting-source",
        type=Path,
        default=None,
        help="Path to the local extracted original map_setting binary. Never committed to the repository.",
    )
    args = parser.parse_args()

    game_root = args.game_root.resolve() if args.game_root else infer_game_root().resolve()
    if not (game_root / "TeamfightManager2.exe").exists():
        raise SystemExit(f"Not a Teamfight Manager 2 root: {game_root}")

    installed = copy_mod(game_root, clean=args.clean)
    print(f"Installed {MOD_ID} to {installed}")

    if args.stage_map_setting_equivalent:
        if args.map_setting_source is None:
            raise SystemExit("--stage-map-setting-equivalent requires --map-setting-source")
        stage_map_setting_equivalent(game_root, installed, args.map_setting_source)

    if args.enable or args.enable_exclusive:
        config_path = enable_mod(game_root, exclusive=args.enable_exclusive)
        mode = "exclusively enabled" if args.enable_exclusive else "enabled"
        print(f"{mode} {MOD_ID} in {config_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
