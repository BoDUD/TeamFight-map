# TFM2 LOL Map Runtime Spike

This is a diagnostic-only Teamfight Manager 2 mod package for testing whether the game loader accepts map asset overrides from this repository.

It is not the LOL-like map, not final map art, and not a collision or pathing change.

## Active Probe

The package remaps exactly one runtime asset:

| Base asset | Probe asset |
| --- | --- |
| `asset/base/aseprite_resources/ingame/5v5/background_5v5` | `asset/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/background_5v5` |

The probe image is a generated solid-color PNG sized to the native `1280x1280` background. It exists only to make a successful override unmistakable in a live match.

## Smoke Test

1. From the repository root, run `python .\tools\install_runtime_spike_mod.py --clean --enable-exclusive`.
2. Restart Teamfight Manager 2 if it was already running.
3. Start Teamfight Manager 2 and verify the mod appears in the mod UI.
4. Enter a 5v5 match.
5. Confirm the match background changes to the probe color while units, minions, towers, jungle monsters, and AI routes continue to behave like the native 5v5 map.

## Success Criteria

- The game recognizes the mod metadata from `mod.mod_info`.
- The game enters a match without asset loading errors.
- The `background_5v5` probe color is visible in the match map.
- Native units, minion waves, towers, jungle camps, and AI pathing remain stable.

## Guardrails

- Do not add `asset/base/setting/map_setting` to this repository package. Q2a proves local installed-copy read takeover, and Q2b proves byte-identical structural round-trip, but neither proves safe gameplay-field mutation.
- If testing an equivalent `map_setting` remap, use `tools/install_runtime_spike_mod.py --stage-map-setting-equivalent`; it stages the binary and temporary override only in the installed game copy.
- Do not commit original game resources or Workshop resources here.
- Do not treat this probe as final map art. Its PNG is intentionally diagnostic.
- Do not expand this package into full texture, collision, spawn, or navigation export until `docs/runtime_map_loading_spike.md` has green answers for the runtime questions.
