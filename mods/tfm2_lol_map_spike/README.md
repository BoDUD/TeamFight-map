# TFM2 LOL Map Runtime Spike

This is a visual-only Teamfight Manager 2 mod package for the LOL-like map skin route.

It is not a gameplay map replacement, not a collision or pathing change, and not a `map_setting` change.

## Active Visual Skin

The package remaps exactly three runtime visual assets:

| Base asset | Probe asset |
| --- | --- |
| `asset/base/aseprite_resources/ingame/5v5/background_5v5` | `asset/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/background_5v5` |
| `asset/base/aseprite_resources/ingame/5v5/wall_5v5` | `asset/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/wall_5v5` |
| `asset/base/aseprite_resources/ingame/5v5/wall_5v5_front` | `asset/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/wall_5v5_front` |

The skin image is normalized from a project-local image-gen bitmap source into the native `1280x1280` background. It visually suggests a LOL-like terrain language while preserving the native Teamfight Manager 2 gameplay data.

The wall and front-wall layers are position-locked to the native wall alpha coverage. They are visual-only replacements and do not change collision, pathing, spawns, brush gameplay, objectives, or `map_setting`.

`minimap_5v5_bg` is not remapped in this package. It has optional installed-copy QA, but default enablement still requires a separate decision and default-package QA pass.

## Smoke Test

1. From the repository root, run `python .\tools\install_runtime_spike_mod.py --clean --enable-exclusive`.
2. Restart Teamfight Manager 2 if it was already running.
3. Start Teamfight Manager 2 and verify the mod appears in the mod UI.
4. Enter a 5v5 match.
5. Confirm the match background changes to the visual skin while units, minions, towers, jungle monsters, and AI routes continue to behave like the native 5v5 map.

## Success Criteria

- The game recognizes the mod metadata from `mod.mod_info`.
- The game enters a match without asset loading errors.
- The `background_5v5`, `wall_5v5`, and `wall_5v5_front` visual skins are visible in the match map.
- Native units, minion waves, towers, jungle camps, and AI pathing remain stable.

## Guardrails

- Do not add `asset/base/setting/map_setting` to this repository package. Q2S records that gameplay `map_setting` editing is blocked pending runtime anchor and semantic proof.
- If testing an equivalent `map_setting` remap, use `tools/install_runtime_spike_mod.py --stage-map-setting-equivalent`; it stages the binary and temporary override only in the installed game copy.
- Do not commit original game resources or Workshop resources here.
- Do not treat this skin as gameplay map editing. It is a non-gameplay cosmetic override.
- Do not expand this package into collision, spawn, brush gameplay, objective, pathing, or navigation export until `docs/runtime_map_loading_spike.md` has green answers for the runtime questions.
