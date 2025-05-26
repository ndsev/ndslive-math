# ndslive-math

Python version of ndsmath, math utilities for NDS.Live.

## Installation

```bash
pip install ndslive-math
```

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