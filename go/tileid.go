// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

import (
	"fmt"
	"math"
)

// PackedTileId represents a tile in the hierarchical NDS.Live tiling system.
//
// Per the NDS.Live standard, tile IDs are signed 32-bit integers. For levels
// 0-14 the values are positive; for level 15 the values are negative
// (-2147483648 to -1) because the level bit (bit 31) coincides with the sign
// bit of a signed int32.
//
// Internally the value is stored as an unsigned 32-bit integer so that all bit
// operations are free of sign-bit complications. Conversion between signed and
// unsigned happens only at the API boundary: constructors accept either
// representation, and Value returns the signed int32 mandated by the standard.
type PackedTileId struct {
	value uint32 // internal unsigned storage
}

// NewPackedTileId constructs a PackedTileId from a signed int32 tile ID value.
//
// Per the NDS.Live standard, level 15 tiles have negative values
// (-2147483648 to -1) while levels 0-14 have positive values. This accepts the
// signed representation directly; for unsigned input use
// NewPackedTileIdFromUnsigned.
//
// It returns an error if the resulting tile ID is invalid.
func NewPackedTileId(value int32) (PackedTileId, error) {
	// Convert signed int32 to unsigned storage. uint32(value) performs the
	// two's-complement reinterpretation, so e.g. -2147483648 -> 2147483648.
	t := PackedTileId{value: uint32(value)}
	if err := t.validate(); err != nil {
		return PackedTileId{}, err
	}
	return t, nil
}

// NewPackedTileIdFromUnsigned constructs a PackedTileId from an unsigned tile
// ID value. Values outside the 32-bit range are masked to 32 bits, mirroring
// the Python constructor. It returns an error if the tile ID is invalid.
func NewPackedTileIdFromUnsigned(value uint64) (PackedTileId, error) {
	t := PackedTileId{value: uint32(value & 0xFFFFFFFF)}
	if err := t.validate(); err != nil {
		return PackedTileId{}, err
	}
	return t, nil
}

// PackedTileIdFromValue constructs a PackedTileId from the signed NDS.Live
// public value.
func PackedTileIdFromValue(value int32) (PackedTileId, error) {
	return NewPackedTileId(value)
}

// PackedTileIdFromTileIndex creates a PackedTileId directly from a tile morton
// number and level, without any coordinate conversion.
//
// mortonNumber must be in [0, 2^(2*level+1) - 1] and level in [0, 15];
// otherwise an error is returned.
func PackedTileIdFromTileIndex(mortonNumber uint32, level int) (PackedTileId, error) {
	if level < 0 || level > 15 {
		return PackedTileId{}, fmt.Errorf("invalid level %d (must be 0-15)", level)
	}
	maxMorton := (uint64(1) << (2*level + 1)) - 1
	if uint64(mortonNumber) > maxMorton {
		return PackedTileId{}, fmt.Errorf(
			"invalid morton number %d for level %d (allowed: 0-%d)",
			mortonNumber, level, maxMorton)
	}
	value := uint64(mortonNumber) + (uint64(1) << (16 + level))
	t := PackedTileId{value: uint32(value)}
	if err := t.validate(); err != nil {
		return PackedTileId{}, err
	}
	return t, nil
}

// PackedTileIdFromTileXY creates a PackedTileId from tile-grid coordinates at
// the given level. X is in [0, 2^(level+1)-1], Y is in [0, 2^level-1].
// Coordinates use the NDS Morton tile-grid order and are inverse to X and Y.
func PackedTileIdFromTileXY(x, y uint32, level int) (PackedTileId, error) {
	if level < 0 || level > 15 {
		return PackedTileId{}, fmt.Errorf("invalid level %d (must be 0-15)", level)
	}
	maxX := (uint32(1) << (level + 1)) - 1
	maxY := (uint32(1) << level) - 1
	if x > maxX || y > maxY {
		return PackedTileId{}, fmt.Errorf(
			"invalid tile coordinates (%d, %d) for level %d (allowed x: 0-%d, y: 0-%d)",
			x, y, level, maxX, maxY)
	}
	return PackedTileIdFromTileIndex(interleaveCoords(x, y, level), level)
}

// PackedTileIdFromNdsCoordinates returns the tile at level that contains the
// given NDS integer coordinate.
func PackedTileIdFromNdsCoordinates(x, y int32, level int) (PackedTileId, error) {
	return PackedTileIdFromMortonAndLevel(MortonFromNdsCoordinates(x, y), level)
}

// PackedTileIdFromWgs84 returns the tile at level that contains the given
// WGS84 coordinate.
func PackedTileIdFromWgs84(longitude, latitude float64, level int) (PackedTileId, error) {
	x, y := NewWgs84(longitude, latitude, 0).ToNdsCoordinates()
	return PackedTileIdFromNdsCoordinates(x, y, level)
}

// PackedTileIdFromMortonAndLevel creates the PackedTileId of the tile at the
// given level that contains the full-precision NDS point encoded by mortonCode.
//
// The resulting tile's MortonNumber will NOT generally equal
// mortonCode.Value(); use PackedTileIdFromTileIndex if you need a specific
// morton number. level must be in [0, 15].
func PackedTileIdFromMortonAndLevel(mortonCode MortonCode, level int) (PackedTileId, error) {
	if level < 0 || level > 15 {
		return PackedTileId{}, fmt.Errorf("invalid level %d (must be 0-15)", level)
	}

	xCoord, yCoord := mortonCode.ToNdsCoordinates()

	// Promote to unsigned magnitudes by adding the wrap-around offsets for
	// negative coordinates (matching the Python reference).
	xu := int64(xCoord)
	yu := int64(yCoord)
	if xu < 0 {
		xu += 1 << 32
	}
	if yu < 0 {
		yu += 1 << 31
	}

	nLevel := 31 - level
	nX := xu >> nLevel
	nY := yu >> nLevel

	temp := MortonFromNdsCoordinates(int32(nX), int32(nY))

	value := temp.Value() + (uint64(1) << (16 + level))
	t := PackedTileId{value: uint32(value)}
	if err := t.validate(); err != nil {
		return PackedTileId{}, err
	}
	return t, nil
}

// Value returns the tile ID as a signed int32 per the NDS.Live standard.
// Level 15 tiles return negative values; levels 0-14 return positive values.
func (t PackedTileId) Value() int32 {
	// int32(uint32) reinterprets the bits, so values with bit 31 set become
	// negative exactly as the standard requires.
	return int32(t.value)
}

// Level returns the level of the tile (0..15).
func (t PackedTileId) Level() int {
	level := 0
	tileID := t.value >> 16
	for tileID > 1 {
		tileID >>= 1
		level++
	}
	return level
}

// Size returns the tile's edge length in NDS coordinate units.
func (t PackedTileId) Size() uint32 {
	return uint32(1) << (31 - t.Level())
}

// MortonNumber returns the tile's Morton number (the value with the
// level-specific offset removed).
func (t PackedTileId) MortonNumber() uint32 {
	tileLevel := t.Level()
	return t.value - (uint32(1) << (16 + tileLevel))
}

// X returns the tile-grid X coordinate at this tile's level.
func (t PackedTileId) X() uint32 {
	x, _ := deinterleaveMorton(t.MortonNumber(), t.Level())
	return x
}

// Y returns the tile-grid Y coordinate at this tile's level.
func (t PackedTileId) Y() uint32 {
	_, y := deinterleaveMorton(t.MortonNumber(), t.Level())
	return y
}

// Center returns the center of the tile in NDS coordinates.
//
// Returned as int64 because, although the center always fits in int32 for
// valid tiles, the corner arithmetic it derives from can exceed int32.
func (t PackedTileId) Center() (int64, int64) {
	x, y := t.SouthWestCorner()
	halfSize := int64(t.Size() / 2)
	return x + halfSize, y + halfSize
}

// PackedTileIdWgs84FromNdsCoordinates converts NDS integer coordinates to
// lon/lat degrees without WGS84 edge normalization.
func PackedTileIdWgs84FromNdsCoordinates(x, y int64) (float64, float64) {
	return float64(x) * 360.0 / math.Exp2(32), float64(y) * 180.0 / math.Exp2(31)
}

// CenterWgs84 returns the center of the tile in lon/lat degrees.
func (t PackedTileId) CenterWgs84() (float64, float64) {
	x, y := t.Center()
	return PackedTileIdWgs84FromNdsCoordinates(x, y)
}

// SouthWestWgs84 returns the south-west tile corner in lon/lat degrees.
func (t PackedTileId) SouthWestWgs84() (float64, float64) {
	x, y := t.SouthWestCorner()
	return PackedTileIdWgs84FromNdsCoordinates(x, y)
}

// NorthEastWgs84 returns the exclusive north-east tile corner in lon/lat
// degrees.
func (t PackedTileId) NorthEastWgs84() (float64, float64) {
	x, y := t.NorthEastCorner()
	return PackedTileIdWgs84FromNdsCoordinates(x, y)
}

// Wgs84Size returns the tile width/height in lon/lat degrees.
func (t PackedTileId) Wgs84Size() (float64, float64) {
	tileSize := float64(t.Size())
	return tileSize * 360.0 / math.Exp2(32), tileSize * 180.0 / math.Exp2(31)
}

// SouthWestCorner returns the south-west (inclusive) corner of the tile in NDS
// coordinates. Returned as int64 for a uniform corner API; SW values always
// fit in int32.
func (t PackedTileId) SouthWestCorner() (int64, int64) {
	mortonNumber := uint64(t.MortonNumber())
	shift := uint(63 - (2*t.Level() + 1))
	x, y := NewMortonCode(mortonNumber << shift).ToNdsCoordinates()
	return int64(x), int64(y)
}

// NorthEastCorner returns the north-east (EXCLUSIVE) corner of the tile in NDS
// coordinates: the first coordinate outside the tile, i.e. SW + size.
//
// Returned as int64 because for low levels (e.g. level 0) the exclusive corner
// is 2^31, which exceeds the signed int32 range.
func (t PackedTileId) NorthEastCorner() (int64, int64) {
	x, y := t.SouthWestCorner()
	size := int64(t.Size())
	return x + size, y + size
}

// DimensionsInMeters returns the tile's (width, height) in meters, computed at
// the tile's center latitude. Width varies with cos(latitude); height is
// constant.
func (t PackedTileId) DimensionsInMeters() (float64, float64) {
	centerX, centerY := t.Center()
	centerWgs := Wgs84FromNdsCoordinates(int32(centerX), int32(centerY))
	tileSize := float64(t.Size())
	return NdsDistanceToMeters(tileSize, tileSize, centerWgs.Lat)
}

// validate checks this PackedTileId's internal (unsigned) value. Error
// messages report the signed API value for clarity.
func (t PackedTileId) validate() error {
	const minPackedTileID = uint32(1) << 16
	if t.value < minPackedTileID {
		return fmt.Errorf(
			"invalid PackedTileId(%d): value must be >= %d or negative for level 15",
			t.Value(), minPackedTileID)
	}

	tileLevel := t.Level()
	morton := uint64(t.MortonNumber())
	maxMorton := (uint64(1) << (2*tileLevel + 1)) - 1
	if morton > maxMorton {
		return fmt.Errorf(
			"invalid PackedTileId(%d): morton number %d exceeds valid range for level %d (allowed: 0-%d)",
			t.Value(), morton, tileLevel, maxMorton)
	}
	return nil
}

// deinterleaveMorton extracts X and Y coordinates from a tile morton number.
// X has (level+1) bits and Y has level bits.
func deinterleaveMorton(morton uint32, level int) (uint32, uint32) {
	var x, y uint32
	for i := 0; i < level; i++ {
		if morton&(1<<(2*i)) != 0 {
			x |= 1 << i
		}
		if morton&(1<<(2*i+1)) != 0 {
			y |= 1 << i
		}
	}
	if morton&(1<<(2*level)) != 0 {
		x |= 1 << level
	}
	return x, y
}

// interleaveCoords builds a tile morton number from X and Y coordinates.
// X has (level+1) bits and Y has level bits.
func interleaveCoords(x, y uint32, level int) uint32 {
	var morton uint32
	for i := 0; i < level; i++ {
		if x&(1<<i) != 0 {
			morton |= 1 << (2 * i)
		}
		if y&(1<<i) != 0 {
			morton |= 1 << (2*i + 1)
		}
	}
	if x&(1<<level) != 0 {
		morton |= 1 << (2 * level)
	}
	return morton
}

// Neighbour returns the same-level tile at a relative grid offset, with
// wrap-around at the respective limits.
func (t PackedTileId) Neighbour(dx, dy int) PackedTileId {
	return t.neighbour(dx, dy)
}

// Neighbor is an American-English alias for Neighbour.
func (t PackedTileId) Neighbor(dx, dy int) PackedTileId {
	return t.Neighbour(dx, dy)
}

// neighbour returns the same-level neighbour after applying dx to X and dy to
// Y, with wrap-around at the respective limits.
func (t PackedTileId) neighbour(dx, dy int) PackedTileId {
	level := t.Level()
	morton := t.MortonNumber()
	x, y := deinterleaveMorton(morton, level)

	if dx != 0 {
		maxX := (uint32(1) << (level + 1)) - 1
		x = uint32(int(x)+dx) & maxX
	}
	if dy != 0 {
		maxY := (uint32(1) << level) - 1
		y = uint32(int(y)+dy) & maxY
	}

	newMorton := interleaveCoords(x, y, level)
	// PackedTileIdFromTileIndex cannot fail here: level and newMorton are
	// within range by construction, so the error is ignored deliberately.
	tile, _ := PackedTileIdFromTileIndex(newMorton, level)
	return tile
}

// WestNeighbour returns the tile to the west at the same level, wrapping at the
// antimeridian.
func (t PackedTileId) WestNeighbour() PackedTileId { return t.neighbour(-1, 0) }

// EastNeighbour returns the tile to the east at the same level, wrapping at the
// antimeridian.
func (t PackedTileId) EastNeighbour() PackedTileId { return t.neighbour(+1, 0) }

// SouthNeighbour returns the tile to the south at the same level, wrapping at
// the south pole.
func (t PackedTileId) SouthNeighbour() PackedTileId { return t.neighbour(0, -1) }

// NorthNeighbour returns the tile to the north at the same level, wrapping at
// the north pole.
func (t PackedTileId) NorthNeighbour() PackedTileId { return t.neighbour(0, +1) }

// String implements fmt.Stringer.
func (t PackedTileId) String() string {
	return fmt.Sprintf("PackedTileId(value=%d)", t.Value())
}

// floorDiv performs floor division (rounding toward negative infinity), which
// differs from Go's built-in integer division (which truncates toward zero)
// for negative operands. divisor is assumed positive (tile sizes always are).
//
// This is critical for parity with Python's // operator used in
// GetTileIdsForBoundingBox.
func floorDiv(a, b int64) int64 {
	q := a / b
	if (a%b != 0) && ((a < 0) != (b < 0)) {
		q--
	}
	return q
}

// GetTileIdsForBoundingBox returns all tile IDs that intersect the bounding box
// defined by the south-west and north-east corners in NDS coordinates, at the
// given level.
//
// Floor division is used for the corner-to-tile-index mapping (matching
// Python's // operator), which matters for negative coordinates.
func GetTileIdsForBoundingBox(swX, swY, neX, neY int32, level int) []PackedTileId {
	var tileIDs []PackedTileId

	tileSize := int64(1) << (31 - level)

	startTileX := floorDiv(int64(swX), tileSize)
	startTileY := floorDiv(int64(swY), tileSize)
	endTileX := floorDiv(int64(neX), tileSize)
	endTileY := floorDiv(int64(neY), tileSize)

	for tileY := startTileY; tileY <= endTileY; tileY++ {
		for tileX := startTileX; tileX <= endTileX; tileX++ {
			tileSwX := tileX * tileSize
			tileSwY := tileY * tileSize

			morton := MortonFromNdsCoordinates(int32(tileSwX), int32(tileSwY))
			// from-morton-and-level cannot fail for a valid level; ignore err.
			tileID, _ := PackedTileIdFromMortonAndLevel(morton, level)
			tileIDs = append(tileIDs, tileID)
		}
	}

	return tileIDs
}

// BoundingBoxFromTileIds computes the minimal NDS bounding box covering all the
// given tiles. It returns (minX, minY, maxX, maxY) where the NE corner has been
// decremented by 1 so that the box is inclusive (the NorthEastCorner of a tile
// is exclusive). It returns an error if tiles is empty.
//
// Values are int64 because the intermediate (exclusive) maxima may exceed
// int32; the decremented results returned here are always within int32 range
// for valid tiles. A single-tile box round-trips: passing the result back
// through GetTileIdsForBoundingBox at the same level yields exactly that tile.
func BoundingBoxFromTileIds(tiles []PackedTileId) (int64, int64, int64, int64, error) {
	if len(tiles) == 0 {
		return 0, 0, 0, 0, fmt.Errorf("tiles list cannot be empty")
	}

	minX, minY := tiles[0].SouthWestCorner()
	maxX, maxY := tiles[0].NorthEastCorner()

	for _, tile := range tiles[1:] {
		swX, swY := tile.SouthWestCorner()
		neX, neY := tile.NorthEastCorner()
		if swX < minX {
			minX = swX
		}
		if swY < minY {
			minY = swY
		}
		if neX > maxX {
			maxX = neX
		}
		if neY > maxY {
			maxY = neY
		}
	}

	return minX, minY, maxX - 1, maxY - 1, nil
}
