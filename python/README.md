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
