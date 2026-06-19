// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

/**
 * Axis-aligned bounding box in NDS coordinates (integers).
 *
 * <p>
 * NDS coordinates use integers for fast comparisons: X (longitude) is a 32-bit
 * signed value and Y (latitude) is a 31-bit signed value. Values are held in
 * {@code long}s so the full signed range is representable.
 * </p>
 *
 * <p>
 * Faithful port of {@code python/src/ndslive/math/bounding_box.py}.
 * </p>
 */
public final class NdsBoundingBox {

	/** SW corner longitude (NDS coords). */
	public final long minX;
	/** SW corner latitude (NDS coords). */
	public final long minY;
	/** NE corner longitude (NDS coords). */
	public final long maxX;
	/** NE corner latitude (NDS coords). */
	public final long maxY;

	/**
	 * @param minX
	 *            SW corner longitude
	 * @param minY
	 *            SW corner latitude
	 * @param maxX
	 *            NE corner longitude
	 * @param maxY
	 *            NE corner latitude
	 */
	public NdsBoundingBox(long minX, long minY, long maxX, long maxY) {
		this.minX = minX;
		this.minY = minY;
		this.maxX = maxX;
		this.maxY = maxY;
	}

	/**
	 * Check whether this bbox intersects (overlaps) with another.
	 *
	 * @param other
	 *            another bounding box to check against
	 * @return {@code true} if the bounding boxes share any area
	 */
	public boolean intersects(NdsBoundingBox other) {
		return !(this.maxX < other.minX || this.minX > other.maxX || this.maxY < other.minY || this.minY > other.maxY);
	}

	/**
	 * Check whether this bbox fully contains another.
	 *
	 * @param other
	 *            another bounding box to check
	 * @return {@code true} if {@code other} is completely inside this bbox
	 */
	public boolean contains(NdsBoundingBox other) {
		return this.minX <= other.minX && this.maxX >= other.maxX && this.minY <= other.minY && this.maxY >= other.maxY;
	}

	/**
	 * Create a bounding box from a tile.
	 *
	 * @param tile
	 *            a PackedTileId
	 * @return an NdsBoundingBox covering the tile's area
	 */
	public static NdsBoundingBox fromTile(PackedTileId tile) {
		long[] sw = tile.southWestCorner();
		long[] ne = tile.northEastCorner();
		return new NdsBoundingBox(sw[0], sw[1], ne[0], ne[1]);
	}

	/**
	 * Create a bounding box from an integer tile id.
	 *
	 * @param tileId
	 *            a tile id value (signed int32 or unsigned)
	 * @return an NdsBoundingBox covering the tile's area
	 */
	public static NdsBoundingBox fromTile(long tileId) {
		return fromTile(new PackedTileId(tileId));
	}

	/**
	 * Create a bounding box from WGS84 corner coordinates.
	 *
	 * @param sw
	 *            south-west corner (min longitude, min latitude)
	 * @param ne
	 *            north-east corner (max longitude, max latitude)
	 * @return an NdsBoundingBox with corners converted to NDS coordinates
	 */
	public static NdsBoundingBox fromWgs84Corners(Wgs84 sw, Wgs84 ne) {
		long[] min = sw.toNdsCoordinates();
		long[] max = ne.toNdsCoordinates();
		return new NdsBoundingBox(min[0], min[1], max[0], max[1]);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj) {
			return true;
		}
		if (!(obj instanceof NdsBoundingBox)) {
			return false;
		}
		NdsBoundingBox o = (NdsBoundingBox) obj;
		return this.minX == o.minX && this.minY == o.minY && this.maxX == o.maxX && this.maxY == o.maxY;
	}

	@Override
	public int hashCode() {
		int result = Long.hashCode(minX);
		result = 31 * result + Long.hashCode(minY);
		result = 31 * result + Long.hashCode(maxX);
		result = 31 * result + Long.hashCode(maxY);
		return result;
	}

	@Override
	public String toString() {
		return "NdsBoundingBox(minX=" + minX + ", minY=" + minY + ", maxX=" + maxX + ", maxY=" + maxY + ")";
	}
}
