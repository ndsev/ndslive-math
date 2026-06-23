// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

// NdsBoundingBox is an axis-aligned bounding box in NDS coordinates.
//
// NDS coordinates use integers for fast comparisons:
//   - X (longitude): 32-bit signed integer
//   - Y (latitude):  31-bit signed integer
//
// MinX/MinY are the SW corner; MaxX/MaxY are the NE corner.
type NdsBoundingBox struct {
	MinX int32 // SW corner longitude (NDS coords)
	MinY int32 // SW corner latitude (NDS coords)
	MaxX int32 // NE corner longitude (NDS coords)
	MaxY int32 // NE corner latitude (NDS coords)
}

// Intersects reports whether this bounding box overlaps (shares any area with)
// other.
func (b NdsBoundingBox) Intersects(other NdsBoundingBox) bool {
	return !(b.MaxX < other.MinX ||
		b.MinX > other.MaxX ||
		b.MaxY < other.MinY ||
		b.MinY > other.MaxY)
}

// Contains reports whether other is completely inside this bounding box.
func (b NdsBoundingBox) Contains(other NdsBoundingBox) bool {
	return b.MinX <= other.MinX &&
		b.MaxX >= other.MaxX &&
		b.MinY <= other.MinY &&
		b.MaxY >= other.MaxY
}

// NdsBoundingBoxFromTile creates a bounding box covering the given tile's area.
//
// The NE corner is the tile's exclusive corner (SW + size); for low-level tiles
// this can exceed the int32 range, so the corner is narrowed via reinterpreting
// conversion exactly as the C++ reference does with int32_t.
func NdsBoundingBoxFromTile(tile PackedTileId) NdsBoundingBox {
	swX, swY := tile.SouthWestCorner()
	neX, neY := tile.NorthEastCorner()
	return NdsBoundingBox{
		MinX: int32(swX),
		MinY: int32(swY),
		MaxX: int32(neX),
		MaxY: int32(neY),
	}
}

// NdsBoundingBoxFromWgs84Corners creates a bounding box from WGS84 corner
// coordinates (sw = min lon/lat, ne = max lon/lat), converting each corner to
// NDS coordinates.
func NdsBoundingBoxFromWgs84Corners(sw, ne Wgs84) NdsBoundingBox {
	minX, minY := sw.ToNdsCoordinates()
	maxX, maxY := ne.ToNdsCoordinates()
	return NdsBoundingBox{MinX: minX, MinY: minY, MaxX: maxX, MaxY: maxY}
}
