# @ndsev/ndslive-math

Coordinate math, packed tile IDs, Morton codes, and bounding boxes for
[NDS.Live](https://nds.live) geographic tiling — the TypeScript/JavaScript port
of the C++ and Python `ndslive-math` libraries.

It provides WGS84 ↔ NDS coordinate conversion, NDS Packed Tile IDs (Morton +
level), standalone Morton (Z-order) encoding/decoding, and bounding boxes in NDS
coordinate space. No runtime dependencies.

## Install

```bash
npm install @ndsev/ndslive-math
```

## Usage

```ts
import {
  Wgs84,
  MortonCode,
  PackedTileId,
  NdsBoundingBox,
  getTileIdsForBoundingBox,
  boundingBoxFromTileIds,
} from "@ndsev/ndslive-math";

// WGS84 <-> NDS coordinates
const munich = new Wgs84(11.585, 48.137); // lon, lat (degrees)
const [ndsX, ndsY] = munich.toNdsCoordinates(); // [138214433, 574296779]
const back = Wgs84.fromNdsCoordinates(ndsX, ndsY);

// Morton (Z-order) codes are 64-bit, returned as a BigInt
const morton = MortonCode.fromNdsCoordinates(ndsX, ndsY);
console.log(morton.value()); // bigint

// Packed tile IDs (signed int32; level-15 tiles are negative)
const tile = PackedTileId.fromMortonAndLevel(morton, 13);
console.log(tile.value, tile.level(), tile.mortonNumber());
const sw = tile.southWestCorner(); // [x, y] in NDS coords
const ne = tile.northEastCorner(); // exclusive corner
const east = tile.eastNeighbour(); // neighbour traversal (wraps at antimeridian)

// Bounding boxes in NDS space
const bbox = NdsBoundingBox.fromWgs84Corners(
  new Wgs84(11.5, 48.1),
  new Wgs84(11.7, 48.2),
);
const tiles = getTileIdsForBoundingBox(
  bbox.minX,
  bbox.minY,
  bbox.maxX,
  bbox.maxY,
  13,
);
const [minX, minY, maxX, maxY] = boundingBoxFromTileIds(tiles);
```

## API

- `Wgs84` — WGS84 lon/lat/alt point. Constructor normalizes (wraps longitude
  into `[-180, 180)`, clamps latitude to `[-90, 90 - LAT_NDS_DELTA]`).
  `toNdsCoordinates()` (uses `Math.floor`), `fromNdsCoordinates(x, y)`,
  `degreesToMeters(...)`, `ndsDistanceToMeters(...)`, `distanceTo(other)`
  (haversine), `bearingFrom(other)`, `toDegreeMinutesSeconds()`, plus
  component-wise `add`/`sub`/`mul`/`div` and `equals`.
- `MortonCode` — 64-bit Z-order code held as a `bigint`.
  `fromNdsCoordinates(x, y)`, `toNdsCoordinates()`, `value()`.
- `PackedTileId` — NDS Packed Tile ID. `value` (signed int32),
  `fromTileIndex(mortonNumber, level)`, `fromMortonAndLevel(mortonCode, level)`,
  `level()`, `size()`, `center()`, `southWestCorner()`, `northEastCorner()`
  (exclusive), `mortonNumber()`, `dimensionsInMeters()`, and
  `west`/`east`/`south`/`northNeighbour()`.
- `getTileIdsForBoundingBox(swX, swY, neX, neY, level)`,
  `boundingBoxFromTileIds(tiles)` — bulk tile enumeration helpers.
- `NdsBoundingBox` — `minX`/`minY`/`maxX`/`maxY` with `intersects`, `contains`,
  `fromTile`, `fromWgs84Corners`.

## Notes

- NDS coordinates: X (longitude) is a signed 32-bit integer, Y (latitude) is a
  signed 31-bit integer.
- Morton codes exceed `Number.MAX_SAFE_INTEGER`, so they are returned as
  `bigint`.
- `PackedTileId.value` follows the NDS.Live standard: level-15 tiles have
  negative values (bit 31 is the sign bit).

## Development

```bash
npm install
npm run build      # tsc -> dist/
npm test           # vitest
npm run coverage   # vitest + v8 coverage
```

The test suite loads the shared golden vectors from
`../test-vectors/parity_vectors.json` and asserts parity with the Python
reference implementation.

## License

MIT — see [LICENSE](./LICENSE).
```
