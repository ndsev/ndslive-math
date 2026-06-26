# ndslive-math (Java)

Java port of **ndslive-math**, a small library of NDS.Live geographic-tiling math
utilities. It is a faithful port of the Python reference implementation and is
verified against the language-neutral golden vectors in
[`test-vectors/parity_vectors.json`](../test-vectors/parity_vectors.json).

It provides:

- `Wgs84` — WGS84 coordinates with normalization, NDS-coordinate conversion
  (using floor), distance/bearing (haversine), and DMS formatting.
- `MortonCode` — 64-bit Z-order (Morton) encode/decode for NDS coordinates.
- `PackedTileId` — NDS.Live packed tile IDs (signed int32 at the API boundary,
  level 15 negative), corners, center, size, neighbours, dimensions in meters.
- `NdsBoundingBox` — axis-aligned bounding box in NDS coordinates with
  `intersects` / `contains` and factory methods.
- `TileIds` — `getTileIdsForBoundingBox(...)` and `boundingBoxFromTileIds(...)`.

## Requirements

- Java 17 or newer.

## Install

The artifact is published under the Maven coordinates
`live.nds:ndslive-math`.

### Maven

```xml
<dependency>
    <groupId>live.nds</groupId>
    <artifactId>ndslive-math</artifactId>
    <version>1.0.0</version>
</dependency>
```

### Gradle

```groovy
implementation 'live.nds:ndslive-math:1.0.0'
```

## Usage

```java
import io.github.ndsev.ndslivemath.*;
import java.util.List;

// WGS84 -> NDS integer coordinates (floor-based conversion).
Wgs84 berlin = new Wgs84(13.404954, 52.520008); // lon, lat
long[] nds = berlin.toNdsCoordinates();          // { nds_x, nds_y }

// Round-trip back to degrees.
Wgs84 back = Wgs84.fromNdsCoordinates(nds[0], nds[1]);

// Great-circle distance and bearing.
Wgs84 munich = new Wgs84(11.585, 48.137);
double meters = berlin.distanceTo(munich);
double bearingRad = berlin.bearingFrom(munich);

// Morton encode / decode.
MortonCode code = MortonCode.fromNdsCoordinates(nds[0], nds[1]);
long raw = code.value();                  // unsigned bit pattern in a long
long[] decoded = code.toNdsCoordinates(); // { x, y }

// Packed tile IDs.
PackedTileId tile = PackedTileId.fromMortonAndLevel(code, 13);
int tileValue = tile.value();             // signed int32 (negative for level 15)
int level = tile.level();
long[] sw = tile.southWestCorner();       // inclusive
long[] ne = tile.northEastCorner();       // exclusive
PackedTileId east = tile.eastNeighbour(); // wraps at the antimeridian

// Tiles covering a bounding box (NDS coords), and a tight box back.
List<PackedTileId> tiles =
    TileIds.getTileIdsForBoundingBox(sw[0], sw[1], ne[0], ne[1], 13);
long[] box = TileIds.boundingBoxFromTileIds(tiles); // { sw_x, sw_y, ne_x, ne_y }

// NDS bounding box operations.
NdsBoundingBox a = NdsBoundingBox.fromTile(tile);
NdsBoundingBox b = NdsBoundingBox.fromWgs84Corners(munich, berlin);
boolean overlap = a.intersects(b);
```

## Building from source

This module uses Gradle (a wrapper is included):

```bash
cd java
./gradlew build          # compile, run tests, and verify ≥95% coverage
./gradlew test           # run the JUnit 5 + parity-vector tests
./gradlew jacocoTestReport   # coverage report at build/reports/jacoco/test/html
```

The publication version is taken from the `ndslivemathVersion` Gradle property
(defaults to `0.1.0-SNAPSHOT`):

```bash
./gradlew publishToMavenLocal -PndslivemathVersion=0.1.0
```

## License

BSD-3-Clause — see [`LICENSE`](LICENSE).
