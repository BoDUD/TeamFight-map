# TeamFight-map

Graybox implementation of the Teamfight Manager 2 LOL-like map refactor.

This repository stores the first playable design layer as data plus validators:

- `data/map/tfm2_lol_like_map.json` is the normalized map layout.
- `tools/validate_map_design.py` checks the design-book constraints.
- `tools/build_graybox_map.py` renders the layout and topology preview.
- `docs/design_compliance.md` maps the implementation back to the design book.

## Build And Validate

```powershell
python .\tools\validate_map_design.py
python .\tools\build_graybox_map.py
python -m unittest discover -s tests
```

Generated previews are written to `assets/graybox/`.

## Scope

The current PR implements the MVP/graybox layer:

1. Keep the square outer frame, base anchors, three lane identity, and two pit centers.
2. Convert the northwest to southeast water band into a continuous tactical river axis.
3. Limit each major objective pit to two entrances.
4. Convert each half jungle into one main loop with two clear exits.
5. Reduce functional brush to 12 groups.
6. Keep Serpen as permanent growth and Morgard as timed pushing pressure.
