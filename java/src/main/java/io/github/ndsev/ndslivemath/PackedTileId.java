// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

/**
 * Represents a tile in the hierarchical NDS.Live tiling system.
 *
 * <p>
 * Per the NDS.Live standard, tile IDs are signed 32-bit integers. For levels
 * 0-14, values are positive. For level 15, values are negative
 * ({@code -2147483648} to {@code -1}) because the level bit (bit 31) is the
 * sign bit in signed int32 representation.
 * </p>
 *
 * <p>
 * Internally values are stored as unsigned 32-bit integers (in a {@code long}
 * masked to {@code 0xFFFFFFFF}) to enable clean bit operations. Conversion
 * between signed and unsigned happens only at the API boundary: the constructor
 * accepts both representations and {@link #value()} returns the signed int32
 * per the standard.
 * </p>
 *
 * <p>
 * Faithful port of {@code python/src/ndslive/math/tileid.py}.
 * </p>
 */
public final class PackedTileId {

	private static final long TWO_POW_32 = 1L << 32;
	private static final long TWO_POW_31 = 1L << 31;

	/** Internal unsigned 32-bit storage, held in a long masked to 0xFFFFFFFF. */
	private final long value;

	/** Construct from tile id value 0 (invalid; provided for symmetry only). */
	// No default constructor: a value of 0 is always invalid, so we omit it.

	/**
	 * Construct a PackedTileId from a tile ID value.
	 *
	 * <p>
	 * Accepts both signed and unsigned 32-bit integer representations. Level 15
	 * tiles have negative signed values ({@code -2147483648} to {@code -1}); levels
	 * 0-14 have positive values.
	 * </p>
	 *
	 * @param value
	 *            tile ID as signed int32 (negative for level 15) or unsigned
	 * @throws IllegalArgumentException
	 *             if the tile ID is invalid
	 */
	public PackedTileId(long value) {
		long v;
		if (value < 0) {
			// Convert signed int32 to unsigned (e.g. -2147483648 -> 2147483648).
			v = value + TWO_POW_32;
		} else if (value >= TWO_POW_32) {
			// Mask values outside 32-bit range to 32 bits.
			v = value & 0xFFFFFFFFL;
		} else {
			v = value;
		}
		this.value = v;
		validate();
	}

	/**
	 * Get the tile ID value as signed int32 per the NDS.Live standard. Level 15
	 * tiles return negative values; levels 0-14 return positive values.
	 *
	 * @return the signed int32 tile id value
	 */
	public int value() {
		if (this.value >= TWO_POW_31) {
			return (int) (this.value - TWO_POW_32);
		}
		return (int) this.value;
	}

	/**
	 * Create a PackedTileId directly from a tile morton number and level, without
	 * any coordinate conversion.
	 *
	 * @param mortonNumber
	 *            the tile's morton number ({@code 0} to {@code 2^(2*level+1) - 1})
	 * @param level
	 *            tile level (0-15)
	 * @return the PackedTileId with the given morton number at the given level
	 * @throws IllegalArgumentException
	 *             if level or mortonNumber are out of range
	 */
	public static PackedTileId fromTileIndex(long mortonNumber, int level) {
		if (level < 0 || level > 15) {
			throw new IllegalArgumentException("Invalid level " + level + " (must be 0-15)");
		}
		long maxMorton = (1L << (2 * level + 1)) - 1;
		if (mortonNumber < 0 || mortonNumber > maxMorton) {
			throw new IllegalArgumentException("Invalid morton number " + mortonNumber + " for level " + level
					+ " (allowed: 0-" + maxMorton + ")");
		}
		long value = mortonNumber + (1L << (16 + level));
		return new PackedTileId(value);
	}

	/**
	 * Create a PackedTileId for the tile at {@code level} that contains the
	 * full-precision NDS coordinates encoded in {@code mortonCode}.
	 *
	 * @param mortonCode
	 *            a MortonCode representing full-precision NDS coordinates
	 * @param level
	 *            tile level (0-15)
	 * @return the PackedTileId of the tile containing the encoded point
	 * @throws IllegalArgumentException
	 *             if level is out of range
	 */
	public static PackedTileId fromMortonAndLevel(MortonCode mortonCode, int level) {
		if (level < 0 || level > 15) {
			throw new IllegalArgumentException("Invalid level " + level + " (must be 0-15)");
		}

		long[] coords = mortonCode.toNdsCoordinates();
		long xCoord = coords[0];
		long yCoord = coords[1];

		if (xCoord < 0) {
			xCoord += TWO_POW_32;
		}
		if (yCoord < 0) {
			yCoord += TWO_POW_31;
		}

		int nLevel = 31 - level;
		long nX = xCoord >>> nLevel;
		long nY = yCoord >>> nLevel;

		MortonCode temp = MortonCode.fromNdsCoordinates(nX, nY);
		long value = temp.value() + (1L << (16 + level));
		return new PackedTileId(value);
	}

	/**
	 * @return the level of the tile (0-15)
	 */
	public int level() {
		int level = 0;
		long tileId = this.value >>> 16;
		while (tileId > 1) {
			tileId >>>= 1;
			level += 1;
		}
		return level;
	}

	/**
	 * @return the size of the tile in NDS coordinate units
	 */
	public long size() {
		return 1L << (31 - level());
	}

	/**
	 * Get tile dimensions in meters at the tile's center latitude.
	 *
	 * @return a {@code double[]} of {@code {width_meters, height_meters}}
	 */
	public double[] dimensionsInMeters() {
		long[] center = center();
		Wgs84 centerWgs = Wgs84.fromNdsCoordinates(center[0], center[1]);
		long tileSize = size();
		return Wgs84.ndsDistanceToMeters(tileSize, tileSize, centerWgs.y);
	}

	/**
	 * @return the center of the tile in NDS coordinates as {@code {x, y}}
	 */
	public long[] center() {
		long[] sw = southWestCorner();
		long halfSize = size() / 2;
		return new long[]{sw[0] + halfSize, sw[1] + halfSize};
	}

	/**
	 * @return the south-west corner of the tile in NDS coordinates as {@code {x,
	 *         y}}
	 */
	public long[] southWestCorner() {
		long mortonNumber = mortonNumber();
		long shifted = mortonNumber << (63 - (2 * level() + 1));
		return new MortonCode(shifted).toNdsCoordinates();
	}

	/**
	 * Returns the north-east corner of the tile in NDS coordinates. This corner is
	 * <em>exclusive</em> (the first point outside the tile).
	 *
	 * @return the north-east corner as {@code {x, y}}
	 */
	public long[] northEastCorner() {
		long[] sw = southWestCorner();
		long size = size();
		return new long[]{sw[0] + size, sw[1] + size};
	}

	/**
	 * @return the Morton number of the tile (the value minus the level offset)
	 */
	public long mortonNumber() {
		int tileLevel = level();
		return this.value - (1L << (16 + tileLevel));
	}

	private void validate() {
		long minPackedTileId = 1L << 16;
		if (this.value < minPackedTileId) {
			throw new IllegalArgumentException("Invalid PackedTileId(" + value() + "): value must be >= "
					+ minPackedTileId + " or negative for level 15");
		}

		int tileLevel = level();
		long morton = mortonNumber();
		long maxMorton = (1L << (2 * tileLevel + 1)) - 1;

		if (morton < 0 || morton > maxMorton) {
			throw new IllegalArgumentException("Invalid PackedTileId(" + value() + "): morton number " + morton
					+ " exceeds valid range for level " + tileLevel + " (allowed: 0-" + maxMorton + ")");
		}
	}

	private static long[] deinterleaveMorton(long morton, int level) {
		long x = 0;
		long y = 0;
		for (int i = 0; i < level; i++) {
			if ((morton & (1L << (2 * i))) != 0) {
				x |= (1L << i);
			}
			if ((morton & (1L << (2 * i + 1))) != 0) {
				y |= (1L << i);
			}
		}
		if ((morton & (1L << (2 * level))) != 0) {
			x |= (1L << level);
		}
		return new long[]{x, y};
	}

	private static long interleaveCoords(long x, long y, int level) {
		long morton = 0;
		for (int i = 0; i < level; i++) {
			if ((x & (1L << i)) != 0) {
				morton |= (1L << (2 * i));
			}
			if ((y & (1L << i)) != 0) {
				morton |= (1L << (2 * i + 1));
			}
		}
		if ((x & (1L << level)) != 0) {
			morton |= (1L << (2 * level));
		}
		return morton;
	}

	/**
	 * @return the tile to the west at the same level, wrapping at the antimeridian
	 */
	public PackedTileId westNeighbour() {
		int level = level();
		long[] xy = deinterleaveMorton(mortonNumber(), level);
		long maxX = (1L << (level + 1)) - 1;
		long x = (xy[0] - 1) & maxX;
		long newMorton = interleaveCoords(x, xy[1], level);
		return fromTileIndex(newMorton, level);
	}

	/**
	 * @return the tile to the east at the same level, wrapping at the antimeridian
	 */
	public PackedTileId eastNeighbour() {
		int level = level();
		long[] xy = deinterleaveMorton(mortonNumber(), level);
		long maxX = (1L << (level + 1)) - 1;
		long x = (xy[0] + 1) & maxX;
		long newMorton = interleaveCoords(x, xy[1], level);
		return fromTileIndex(newMorton, level);
	}

	/**
	 * @return the tile to the south at the same level, wrapping at the south pole
	 */
	public PackedTileId southNeighbour() {
		int level = level();
		long[] xy = deinterleaveMorton(mortonNumber(), level);
		long maxY = (1L << level) - 1;
		long y = (xy[1] - 1) & maxY;
		long newMorton = interleaveCoords(xy[0], y, level);
		return fromTileIndex(newMorton, level);
	}

	/**
	 * @return the tile to the north at the same level, wrapping at the north pole
	 */
	public PackedTileId northNeighbour() {
		int level = level();
		long[] xy = deinterleaveMorton(mortonNumber(), level);
		long maxY = (1L << level) - 1;
		long y = (xy[1] + 1) & maxY;
		long newMorton = interleaveCoords(xy[0], y, level);
		return fromTileIndex(newMorton, level);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj) {
			return true;
		}
		if (!(obj instanceof PackedTileId)) {
			return false;
		}
		return this.value == ((PackedTileId) obj).value;
	}

	@Override
	public int hashCode() {
		return Long.hashCode(this.value);
	}

	@Override
	public String toString() {
		return "PackedTileId(value=" + value() + ")";
	}
}
