# ndslive-math (Go)

Go port of [`ndslive-math`](../), a small math library for NDS.Live geographic
tiling. It provides WGS84 coordinate handling, Morton (Z-order) codes, packed
tile IDs, and NDS-coordinate bounding boxes.

The C++ and Python implementations are the reference; this Go package mirrors
their behaviour and is validated against the shared golden parity vectors in
[`../test-vectors/parity_vectors.json`](../test-vectors/parity_vectors.json).

## Installation

```bash
go get github.com/ndsev/ndslive-math/go
```

```go
import ndslivemath "github.com/ndsev/ndslive-math/go"
```

## Versioning / release tags (important)

Because this module lives in the `go/` **subdirectory** of the repository (not
at the repo root), Go's module tooling requires version tags to be **prefixed
with the module subdirectory path**:

```
go/vX.Y.Z      ✅  correct — e.g. go/v0.5.2
vX.Y.Z         ❌  will NOT be picked up for this module
```

So to release `v0.5.2` of the Go module, create and push the tag `go/v0.5.2`.
Plain `vX.Y.Z` tags (used by other parts of the repo) are ignored by `go get`
for this module.

## Usage

```go
package main

import (
	"fmt"

	ndslivemath "github.com/ndsev/ndslive-math/go"
)

func main() {
	// WGS84 -> NDS integer coordinates (uses floor, not truncation).
	berlin := ndslivemath.NewWgs84(13.404954, 52.520008, 0)
	x, y := berlin.ToNdsCoordinates()
	fmt.Println("NDS:", x, y) // 159927330 626588102

	// Round-trip back to degrees.
	back := ndslivemath.Wgs84FromNdsCoordinates(x, y)
	fmt.Printf("Lon=%.6f Lat=%.6f\n", back.Lon, back.Lat)

	// Morton codes.
	m := ndslivemath.MortonFromNdsCoordinates(x, y)
	fmt.Println("Morton:", m.Value())

	// Packed tile IDs. Level 15 tiles have negative signed values.
	tile, err := ndslivemath.PackedTileIdFromMortonAndLevel(m, 13)
	if err != nil {
		panic(err)
	}
	fmt.Println("Tile value:", tile.Value())
	fmt.Println("Level:", tile.Level(), "Morton#:", tile.MortonNumber())
	swX, swY := tile.SouthWestCorner()
	neX, neY := tile.NorthEastCorner() // NE corner is EXCLUSIVE
	fmt.Println("SW:", swX, swY, "NE(excl):", neX, neY)

	// Distance and bearing.
	munich := ndslivemath.NewWgs84(11.585, 48.137, 0)
	fmt.Printf("Distance: %.1f m\n", berlin.DistanceTo(munich))
	fmt.Printf("Bearing: %.6f rad\n", berlin.BearingFrom(munich))

	// Tiles covering a bounding box (NDS coords, floor division for negatives).
	tiles := ndslivemath.GetTileIdsForBoundingBox(0, 0, 268435456, 268435456, 3)
	fmt.Println("tiles:", len(tiles))

	// Bounding box ops.
	bbox := ndslivemath.NdsBoundingBoxFromTile(tile)
	_ = bbox
}
```

## Semantic notes / correctness

The Go port carefully preserves behaviours where Go's semantics differ from
Python's:

- **WGS84 → NDS uses `math.Floor`**, not truncation; negative coordinates floor
  toward −∞.
- **`PackedTileId.Value()` is a signed `int32`** (negative for level 15);
  internally the value is stored unsigned (`uint32`).
- **`MortonCode` is a `uint64`**; the encoder masks off bit 63.
- **`NorthEastCorner` is EXCLUSIVE**, and `BoundingBoxFromTileIds` subtracts 1
  from the maxima.
- **Floor division** is used for bounding-box tile indexing (Go's `/` truncates
  toward zero for negatives; an explicit `floorDiv` helper is used instead).

Invalid tiles return an `error` (idiomatic Go) rather than panicking.

## Testing

```bash
cd go
go test ./...
```

The tests load the shared golden vectors and assert every section, plus
hand-written unit tests.

## License

MIT — see [LICENSE](LICENSE).
