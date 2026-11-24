# ndslive-math

Python version of ndsmath, math utilities for NDS.Live.

## Installation

```bash
pip install ndslive-math
```

## Development

For development, install in editable mode with the version workaround since the Python package is in a subdirectory:

```bash
SETUPTOOLS_SCM_PRETEND_VERSION=$(cd .. && python -m setuptools_scm) pip install --config-settings editable-mode=strict -e .
```

This workaround is needed because the git repository is at the parent level, not in the `python/` directory.

## Usage

```python
from ndslive.math import Wgs84, PackedTileId, MortonCode

# Create WGS84 coordinates
coord = Wgs84(lon=13.404954, lat=52.520008)

# Convert to NDS coordinates
x_nds, y_nds = coord.to_nds_coordinates()

# Create packed tile ID
tile = PackedTileId(level=13, x=4567, y=2345)

# Create Morton code
morton = MortonCode.from_nds_coordinates(x_nds, y_nds)
```

## Polygon areas with holes

`valid_polygon_area`, `classify_polygon_rectangle`, and `PolygonAreaRelation` provide coverage classification.

Validate an exterior ring and all holes once, then classify closed rectangles as
outside (0), inside (1), or boundary (2). Inputs use raw planar coordinates; callers
must unwrap antimeridian geometry consistently. Either winding and an optional
repeated closing vertex are supported. Rings must be finite, simple and nondegenerate;
holes must lie strictly inside the exterior without touching, intersecting or nesting.
Exterior and hole edges are included in the covered area. Rectangle classification
requires validated rings and returns outside for nonfinite or inverted rectangles.

`polygon_areas_intersect` checks two validated polygon areas in the same unwrapped plane, including holes and boundary contact. Ring validity and contact use adaptive exact-sign orientation predicates: one-unit NDS polygons and tiny holes remain valid after translation. No coordinate rounding or broad epsilon is used.
