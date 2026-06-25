// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

import "math"

// Wgs84AABB is a WGS84 axis-aligned bounding box.
//
// Port of the C++ Wgs84AABB<T> (cpp/include/ndsmath/wgs84aabb.h), specialized
// to float64. The box is stored as a south-west corner (a Wgs84) plus a raw
// Vec2 size (a (dx, dy) extent that is NOT normalized).
//
// The geometry layer deliberately uses the power-of-two NDS deltas
// (LonNdsDeltaPow2 etc.) so antimeridian handling and tile-from-index
// construction match the C++ reference bit-for-bit.
type Wgs84AABB struct {
	sw   Wgs84
	size Vec2
}

// NewWgs84AABB constructs an AABB from a south-west corner and a size.
//
// After storing, if the box is valid, the height is clamped so the top never
// exceeds +90 degrees (the excessHeight correction). An invalid box stores size
// unmodified.
func NewWgs84AABB(sw Wgs84, size Vec2) Wgs84AABB {
	box := Wgs84AABB{sw: sw, size: size}
	if !box.Valid() {
		return box
	}
	excessHeight := 90.0 - box.sw.Latitude() - box.size.Y
	if excessHeight < 0 {
		box.size.Y += excessHeight
	}
	return box
}

// Wgs84AABBFromTile constructs an AABB covering a tile (Path A: via
// Wgs84FromMortonCode).
//
// Mirrors the C++ Wgs84AABB(PackedTileId) constructor: the SW/NE NDS corners
// are wrapped into a MortonCode and converted via Wgs84FromMortonCode, so both
// axes are scaled by 360 / 2^32 (NOT Wgs84FromNdsCoordinates, which scales
// latitude by 180 / 2^31 and would diverge from C++).
func Wgs84AABBFromTile(tileID PackedTileId) Wgs84AABB {
	swX, swY := tileID.SouthWestCorner()
	neX, neY := tileID.NorthEastCorner()

	swCorner := Wgs84FromMortonCode(MortonFromNdsCoordinates(int32(swX), int32(swY)))
	neCorner := Wgs84FromMortonCode(MortonFromNdsCoordinates(int32(neX), int32(neY)))

	size := Vec2{X: swCorner.Lon - neCorner.Lon, Y: swCorner.Lat - neCorner.Lat}.Abs()
	return NewWgs84AABB(swCorner, size)
}

// Wgs84AABBFromCenterAndTileLimit constructs an AABB from a center, a soft
// tile-count limit, and a level.
func Wgs84AABBFromCenterAndTileLimit(center Wgs84, softLimit uint32, level int) Wgs84AABB {
	const targetAspectRatio = 0.7 // approx. height / width
	tileWidth := 180.0 / float64(uint64(1)<<level)
	targetSize := math.Sqrt(float64(softLimit)) * tileWidth
	targetSizeVec := Vec2{X: targetSize / targetAspectRatio, Y: targetSize * targetAspectRatio}
	half := targetSizeVec.Scale(0.5)
	newSW := NewWgs84(center.Lon-half.X, center.Lat-half.Y, 0.0)
	return NewWgs84AABB(newSW, targetSizeVec)
}

// Valid reports whether the box size is within reasonable bounds:
// 0 <= size.X <= 360 and 0 <= size.Y <= 180.
func (b Wgs84AABB) Valid() bool {
	return b.size.X >= 0 && b.size.Y >= 0 && b.size.X <= 360.0 && b.size.Y <= 180.0
}

// SW returns the south-west corner.
func (b Wgs84AABB) SW() Wgs84 {
	return b.sw
}

// NE returns the north-east corner (sw + size, re-normalized).
func (b Wgs84AABB) NE() Wgs84 {
	return NewWgs84(b.sw.Lon+b.size.X, b.sw.Lat+b.size.Y, 0.0)
}

// NW returns the north-west corner.
func (b Wgs84AABB) NW() Wgs84 {
	return NewWgs84(b.sw.Lon, b.sw.Lat+b.size.Y, 0.0)
}

// SE returns the south-east corner.
func (b Wgs84AABB) SE() Wgs84 {
	return NewWgs84(b.sw.Lon+b.size.X, b.sw.Lat, 0.0)
}

// Vertices returns all four corners, CCW from SW: [sw, se, ne, nw].
func (b Wgs84AABB) Vertices() []Wgs84 {
	return []Wgs84{b.SW(), b.SE(), b.NE(), b.NW()}
}

// Size returns the raw (dx, dy) size of the box.
func (b Wgs84AABB) Size() Vec2 {
	return b.size
}

// ContainsAntiMeridian reports whether the horizontal extent crosses the
// anti-meridian (+/-180).
func (b Wgs84AABB) ContainsAntiMeridian() bool {
	return b.sw.Longitude()+b.size.X > LonMax+LonNdsDeltaPow2
}

// Center returns the center coordinate (sw + size * 0.5, re-normalized).
func (b Wgs84AABB) Center() Wgs84 {
	half := b.size.Scale(0.5)
	return NewWgs84(b.sw.Lon+half.X, b.sw.Lat+half.Y, 0.0)
}

// SplitOverAntiMeridian splits a box crossing the anti-meridian into a left and
// a right half.
//
// Only meaningful when ContainsAntiMeridian is true. Returns the two normalized
// boxes and ok=true, or two zero boxes and ok=false if the box does not
// actually extend past LonMax.
func (b Wgs84AABB) SplitOverAntiMeridian() (left, right Wgs84AABB, ok bool) {
	widthAfterAM := b.sw.Longitude() + b.size.X - LonMax
	if widthAfterAM > 0 {
		widthBeforeAM := b.size.X - widthAfterAM
		left = NewWgs84AABB(b.sw, Vec2{X: widthBeforeAM, Y: b.size.Y})
		right = NewWgs84AABB(
			NewWgs84(LonMin, b.sw.Latitude(), 0.0),
			Vec2{X: widthAfterAM, Y: b.size.Y},
		)
		return left, right, true
	}
	return Wgs84AABB{}, Wgs84AABB{}, false
}

// AvgMercatorStretch returns the Mercator-projection vertical stretch factor.
//
// Transcendental; not part of the cross-language parity vectors (asserted only
// for finiteness in unit tests).
func (b Wgs84AABB) AvgMercatorStretch() float64 {
	latTop := degToRad(b.sw.Latitude() + b.size.Y)
	latBottom := degToRad(b.sw.Latitude())
	radToMercatorLat := func(wgs84Lat float64) float64 {
		return math.Atanh(math.Sin(wgs84Lat - math.Pi/2.0))
	}
	return (radToMercatorLat(latTop) - radToMercatorLat(latBottom)) / degToRad(b.size.Y)
}

// NumTileIds returns the approximate number of tiles at level lv contained in
// this box.
//
// Mirrors the C++ numTileIds: tileWidth = 180 / float32(2^lv) and a
// component-wise ceil of size / tileWidth. The C++ code casts 1u<<lv to a
// 32-bit float; for lv <= 31 that cast is exact for powers of two. The product
// is truncated toward zero to an integer (matching the reference int() cast),
// so it can be negative for invalid (negative-size) boxes; that is preserved.
func (b Wgs84AABB) NumTileIds(lv int) int {
	tileWidth := 180.0 / float64(float32(uint64(1)<<lv))
	tilesPerDimX := math.Ceil(b.size.X / tileWidth)
	tilesPerDimY := math.Ceil(b.size.Y / tileWidth)
	return int(tilesPerDimX * tilesPerDimY)
}

// TileLevel returns the first level (0..15) whose tile count is at least
// minNumTiles. Returns 15 if no level in 0..15 reaches the threshold.
func (b Wgs84AABB) TileLevel(minNumTiles int) int {
	for resultTileLevel := 0; resultTileLevel <= 15; resultTileLevel++ {
		if b.NumTileIds(resultTileLevel) >= minNumTiles {
			return resultTileLevel
		}
	}
	return 15
}

// Contains reports whether point lies within the box (inclusive on all edges).
func (b Wgs84AABB) Contains(point Wgs84) bool {
	return point.Longitude() >= b.sw.Longitude() &&
		point.Longitude() <= b.sw.Longitude()+b.size.X &&
		point.Latitude() >= b.sw.Latitude() &&
		point.Latitude() <= b.sw.Latitude()+b.size.Y
}

// Intersects is the axis-aligned interval-overlap test against another box.
//
// This is the fixed test: a pure interval overlap on longitude and latitude.
// Edge-touching counts as intersecting; it correctly detects cross-shaped
// overlaps and never recurses on disjoint boxes.
func (b Wgs84AABB) Intersects(other Wgs84AABB) bool {
	aMaxX := b.sw.Longitude() + b.size.X
	aMaxY := b.sw.Latitude() + b.size.Y
	bMaxX := other.sw.Longitude() + other.size.X
	bMaxY := other.sw.Latitude() + other.size.Y
	return b.sw.Longitude() <= bMaxX &&
		aMaxX >= other.sw.Longitude() &&
		b.sw.Latitude() <= bMaxY &&
		aMaxY >= other.sw.Latitude()
}
