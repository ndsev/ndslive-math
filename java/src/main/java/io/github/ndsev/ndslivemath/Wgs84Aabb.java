// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

import java.util.Arrays;
import java.util.List;
import java.util.Optional;

/**
 * A WGS84 axis-aligned bounding box defined by a south-west corner and a size.
 *
 * <p>
 * Port of the C++ {@code Wgs84AABB<T>}
 * ({@code cpp/include/ndsmath/wgs84aabb.h}), specialized to {@code double}. The
 * box is stored as a south-west corner ({@link Wgs84}) plus a raw {@link Vec2}
 * size (a {@code (dx, dy)} extent that is <em>not</em> normalized).
 * </p>
 *
 * <p>
 * The geometry layer deliberately uses the power-of-two NDS deltas
 * ({@link Wgs84#LON_NDS_DELTA_POW2} etc.) so antimeridian handling and
 * tile-from-index construction match the C++ reference bit-for-bit.
 * </p>
 */
public final class Wgs84Aabb {

	private final Wgs84 sw;
	private final Vec2 size;

	/** Construct a default box: {@code sw = (0, 0)}, {@code size = (0, 0)}. */
	public Wgs84Aabb() {
		this(new Wgs84(0.0, 0.0), new Vec2(0.0, 0.0));
	}

	/**
	 * Construct an AABB from a south-west corner and a size.
	 *
	 * <p>
	 * After storing, if the box is {@link #valid()}, the height is clamped so the
	 * top never exceeds +90 degrees (the {@code excessHeight} correction). An
	 * invalid box stores {@code size} unmodified.
	 * </p>
	 *
	 * @param sw
	 *            the south-west corner
	 * @param size
	 *            the raw {@code (dx, dy)} extent
	 */
	public Wgs84Aabb(Wgs84 sw, Vec2 size) {
		this.sw = sw;
		this.size = new Vec2(size.x, size.y);

		if (!valid()) {
			return;
		}

		double excessHeight = 90.0 - this.sw.latitude() - this.size.y;
		if (excessHeight < 0) {
			this.size.y += excessHeight;
		}
	}

	/**
	 * Construct an AABB covering a tile (Path A: via {@link Wgs84#fromMortonCode}).
	 *
	 * <p>
	 * Mirrors the C++ {@code Wgs84AABB(PackedTileId)} constructor: the SW/NE NDS
	 * corners are wrapped into a {@link MortonCode} and converted via
	 * {@link Wgs84#fromMortonCode}, so both axes are scaled by {@code 360 / 2^32}
	 * (NOT {@link Wgs84#fromNdsCoordinates}, which scales latitude by
	 * {@code 180 / 2^31} and would diverge from C++).
	 * </p>
	 *
	 * @param tileId
	 *            the tile whose extent the AABB should cover
	 */
	public Wgs84Aabb(PackedTileId tileId) {
		this(swCornerOf(tileId), sizeOf(tileId));
	}

	private static Wgs84 swCornerOf(PackedTileId tileId) {
		long[] sw = tileId.southWestCorner();
		return Wgs84.fromMortonCode(MortonCode.fromNdsCoordinates(sw[0], sw[1]));
	}

	private static Vec2 sizeOf(PackedTileId tileId) {
		long[] sw = tileId.southWestCorner();
		long[] ne = tileId.northEastCorner();
		Wgs84 swCorner = Wgs84.fromMortonCode(MortonCode.fromNdsCoordinates(sw[0], sw[1]));
		Wgs84 neCorner = Wgs84.fromMortonCode(MortonCode.fromNdsCoordinates(ne[0], ne[1]));
		return new Vec2(swCorner.x - neCorner.x, swCorner.y - neCorner.y).abs();
	}

	/**
	 * Construct an AABB from a center, a soft tile-count limit, and a level.
	 *
	 * @param center
	 *            the center coordinate of the box
	 * @param softLimit
	 *            approximate maximum number of tiles to cover (unsigned 32-bit)
	 * @param level
	 *            NDS tile level
	 * @return a new {@link Wgs84Aabb} centered on {@code center}
	 */
	public static Wgs84Aabb fromCenterAndTileLimit(Wgs84 center, long softLimit, int level) {
		double targetAspectRatio = 0.7; // approx. height / width
		double tileWidth = 180.0 / (double) (1L << level);
		double targetSize = Math.sqrt(softLimit) * tileWidth;
		Vec2 targetSizeVec = new Vec2(targetSize / targetAspectRatio, targetSize * targetAspectRatio);
		Vec2 half = targetSizeVec.mul(0.5);
		Wgs84 newSw = new Wgs84(center.x - half.x, center.y - half.y);
		return new Wgs84Aabb(newSw, targetSizeVec);
	}

	/**
	 * Whether the box size is within reasonable bounds.
	 *
	 * @return {@code 0 <= size.x <= 360 && 0 <= size.y <= 180}
	 */
	public boolean valid() {
		return this.size.x >= 0 && this.size.y >= 0 && this.size.x <= 360.0 && this.size.y <= 180.0;
	}

	/**
	 * @return the south-west corner
	 */
	public Wgs84 sw() {
		return this.sw;
	}

	/**
	 * @return the north-east corner ({@code sw + size}, re-normalized)
	 */
	public Wgs84 ne() {
		return new Wgs84(this.sw.x + this.size.x, this.sw.y + this.size.y);
	}

	/**
	 * @return the north-west corner
	 */
	public Wgs84 nw() {
		return new Wgs84(this.sw.x, this.sw.y + this.size.y);
	}

	/**
	 * @return the south-east corner
	 */
	public Wgs84 se() {
		return new Wgs84(this.sw.x + this.size.x, this.sw.y);
	}

	/**
	 * @return all four corners, CCW from SW: {@code [sw, se, ne, nw]}
	 */
	public List<Wgs84> vertices() {
		return Arrays.asList(sw(), se(), ne(), nw());
	}

	/**
	 * @return the raw {@code (dx, dy)} size of the box
	 */
	public Vec2 size() {
		return this.size;
	}

	/**
	 * @return whether the horizontal extent crosses the anti-meridian (+/-180)
	 */
	public boolean containsAntiMeridian() {
		return this.sw.longitude() + this.size.x > Wgs84.LON_MAX + Wgs84.LON_NDS_DELTA_POW2;
	}

	/**
	 * @return the center coordinate ({@code sw + size * 0.5}, re-normalized)
	 */
	public Wgs84 center() {
		Vec2 half = this.size.mul(0.5);
		return new Wgs84(this.sw.x + half.x, this.sw.y + half.y);
	}

	/**
	 * Split a box crossing the anti-meridian into a left and right half.
	 *
	 * <p>
	 * Only meaningful when {@link #containsAntiMeridian()} is true.
	 * </p>
	 *
	 * @return an {@code Optional} of {@code (left, right)} (as a 2-element array),
	 *         or empty if the box does not actually extend past {@code LON_MAX}
	 */
	public Optional<Wgs84Aabb[]> splitOverAntiMeridian() {
		double widthAfterAm = this.sw.longitude() + this.size.x - Wgs84.LON_MAX;
		if (widthAfterAm > 0) {
			double widthBeforeAm = this.size.x - widthAfterAm;
			Wgs84Aabb left = new Wgs84Aabb(this.sw, new Vec2(widthBeforeAm, this.size.y));
			Wgs84Aabb right = new Wgs84Aabb(new Wgs84(Wgs84.LON_MIN, this.sw.latitude()),
					new Vec2(widthAfterAm, this.size.y));
			return Optional.of(new Wgs84Aabb[]{left, right});
		}
		return Optional.empty();
	}

	/**
	 * The Mercator-projection vertical stretch factor.
	 *
	 * <p>
	 * Transcendental; not part of the cross-language parity vectors (asserted only
	 * for finiteness in unit tests).
	 * </p>
	 *
	 * @return the average Mercator vertical stretch over the box's latitude span
	 */
	public double avgMercatorStretch() {
		double latTop = Math.toRadians(this.sw.latitude() + this.size.y);
		double latBottom = Math.toRadians(this.sw.latitude());
		return (radToMercatorLat(latTop) - radToMercatorLat(latBottom)) / Math.toRadians(this.size.y);
	}

	private static double radToMercatorLat(double wgs84Lat) {
		// atanh(z) = 0.5 * ln((1 + z) / (1 - z)); Java has no Math.atanh.
		double z = Math.sin(wgs84Lat - Math.PI / 2.0);
		return 0.5 * Math.log((1.0 + z) / (1.0 - z));
	}

	/**
	 * Approximate number of tiles at level {@code lv} contained in this box.
	 *
	 * <p>
	 * Mirrors the C++ {@code numTileIds}: {@code tileWidth = 180 / float(2^lv)} and
	 * a component-wise {@code ceil} of {@code size / tileWidth}.
	 * </p>
	 *
	 * @param lv
	 *            the tile level
	 * @return the number of tiles (may be negative for an invalid, negative-size
	 *         box, matching the reference)
	 */
	public long numTileIds(int lv) {
		double tileWidth = 180.0 / (float) (1L << lv);
		double tilesPerDimX = Math.ceil(this.size.x / tileWidth);
		double tilesPerDimY = Math.ceil(this.size.y / tileWidth);
		return (long) (tilesPerDimX * tilesPerDimY);
	}

	/**
	 * First level (0..15) whose tile count is at least {@code minNumTiles}.
	 *
	 * @param minNumTiles
	 *            the threshold tile count
	 * @return the first qualifying level, or 15 if none in {@code 0..15} reaches
	 *         the threshold
	 */
	public int tileLevel(long minNumTiles) {
		for (int resultTileLevel = 0; resultTileLevel < 16; resultTileLevel++) {
			if (numTileIds(resultTileLevel) >= minNumTiles) {
				return resultTileLevel;
			}
		}
		return 15;
	}

	/**
	 * First level (0..15) whose tile count is at least 8.
	 *
	 * @return the first qualifying level, or 15
	 */
	public int tileLevel() {
		return tileLevel(8);
	}

	/**
	 * Whether {@code point} lies within the box (inclusive on all edges).
	 *
	 * @param point
	 *            the point to test
	 * @return {@code true} if the point is inside or on the boundary
	 */
	public boolean contains(Wgs84 point) {
		return point.longitude() >= this.sw.longitude() && point.longitude() <= this.sw.longitude() + this.size.x
				&& point.latitude() >= this.sw.latitude() && point.latitude() <= this.sw.latitude() + this.size.y;
	}

	/**
	 * Axis-aligned interval-overlap test against another box.
	 *
	 * <p>
	 * This is the <em>fixed</em> test: a pure interval overlap on longitude and
	 * latitude. Edge-touching counts as intersecting; it correctly detects
	 * cross-shaped overlaps and never recurses on disjoint boxes.
	 * </p>
	 *
	 * @param other
	 *            the box to test against
	 * @return {@code true} if the two boxes overlap (edge-touching included)
	 */
	public boolean intersects(Wgs84Aabb other) {
		double aMaxX = this.sw.longitude() + this.size.x;
		double aMaxY = this.sw.latitude() + this.size.y;
		double bMaxX = other.sw.longitude() + other.size.x;
		double bMaxY = other.sw.latitude() + other.size.y;
		return this.sw.longitude() <= bMaxX && aMaxX >= other.sw.longitude() && this.sw.latitude() <= bMaxY
				&& aMaxY >= other.sw.latitude();
	}
}
