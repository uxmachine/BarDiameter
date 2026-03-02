# BarDiameter MVP Tool

This repository now includes an MVP Rhino Python tool that automates:

1. pick 2 points on a mesh rebar segment,
2. generate section stations along the local mesh path,
3. compute equivalent diameters from section areas,
4. return robust summary statistics and confidence.

## Files
- `src/rhino_rebar_diameter_mvp.py`: Rhino-runner script.
- `src/diameter_stats.py`: Robust stats helpers (pure Python).
- `tests/test_diameter_stats.py`: Unit tests for helper math.

## Rhino usage
In Rhino's Python editor:

```python
import sys
sys.path.append(r"<repo_path>/src")
import rhino_rebar_diameter_mvp as tool
tool.run_mvp()
```

Then:
- select mesh,
- pick point 1,
- pick point 2,
- read results in Rhino command history.

## Current MVP behavior
- Uses mesh-topology shortest path between picks.
- Samples orthogonal planes every 25 mm (configurable in `Settings`).
- Uses largest closed mesh-plane section loop per station.
- Rejects likely fused stations with multiple similar-size loops.
- Aggregates valid station diameters with robust median + IQR.

## Known limitations
- Meant for local single-bar windows; heavy merges still fail.
- Confidence is a heuristic based on invalid station ratio.
- No UI panel yet; output is command-line text.
