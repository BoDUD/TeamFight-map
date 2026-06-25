from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MOD_ID = "tfm2_lol_map_spike"
SOURCE_MOD = REPO_ROOT / "mods" / MOD_ID


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
    args = parser.parse_args()

    game_root = args.game_root.resolve() if args.game_root else infer_game_root().resolve()
    if not (game_root / "TeamfightManager2.exe").exists():
        raise SystemExit(f"Not a Teamfight Manager 2 root: {game_root}")

    installed = copy_mod(game_root, clean=args.clean)
    print(f"Installed {MOD_ID} to {installed}")

    if args.enable or args.enable_exclusive:
        config_path = enable_mod(game_root, exclusive=args.enable_exclusive)
        mode = "exclusively enabled" if args.enable_exclusive else "enabled"
        print(f"{mode} {MOD_ID} in {config_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
