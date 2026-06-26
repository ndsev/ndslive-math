// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

import java.util.Arrays;
import java.util.List;

/**
 * A simple polygon of WGS84 vertices with collision and bounding-box helpers.
 *
 * <p>
 * Port of the C++ {@code HighPrecWgs84Polygon}
 * ({@code cpp/include/ndsmath/wgs84polygon.h}). A {@link Polygon} of
 * {@link Wgs84} vertices, defaulting to {@code SIMPLE_POLYGON}, with:
 * </p>
 *
 * <ul>
 * <li>{@link #aaBb()} — the axis-aligned bounding box,</li>
 * <li>{@link #median()} — the centroid (with a <em>deliberately preserved</em>
 * lon/lat swap quirk from the C++ reference),</li>
 * <li>{@link #collidesWith(Wgs84Polygon)} — Separating-Axis-Theorem collision
 * detection.</li>
 * </ul>
 *
 * <p>
 * The collision math runs on raw {@code (lon, lat)} doubles: no normalization,
 * no antimeridian handling.
 * </p>
 */
public final class Wgs84Polygon extends Polygon {

	/** Construct an empty simple polygon. */
	public Wgs84Polygon() {
		super(PolygonType.SIMPLE_POLYGON, null);
	}

	/**
	 * Construct a simple polygon with the given vertices.
	 *
	 * @param vertices
	 *            the polygon vertices (copied)
	 */
	public Wgs84Polygon(List<Wgs84> vertices) {
		super(PolygonType.SIMPLE_POLYGON, vertices);
	}

	/**
	 * Construct an empty polygon of the given type.
	 *
	 * @param polygonType
	 *            the polygon topology
	 */
	public Wgs84Polygon(PolygonType polygonType) {
		super(polygonType, null);
	}

	/**
	 * Construct a polygon of the given type with the given vertices.
	 *
	 * @param polygonType
	 *            the polygon topology
	 * @param vertices
	 *            the polygon vertices (copied)
	 */
	public Wgs84Polygon(PolygonType polygonType, List<Wgs84> vertices) {
		super(polygonType, vertices);
	}

	/**
	 * The 4-vertex sentinel polygon wrapping the whole Earth.
	 *
	 * <p>
	 * Constructed from {@code (-180,-90), (-180,90), (180,-90), (180,90)}. These
	 * coordinates pass through {@link Wgs84} normalization, so the stored values
	 * are not exactly those literals. This polygon is only used as an identity
	 * sentinel in {@link #collidesWith(Wgs84Polygon)} via {@code equals}; its exact
	 * normalized coordinates are not part of cross-language parity.
	 * </p>
	 *
	 * @return the Earth-wrapping sentinel polygon
	 */
	public static Wgs84Polygon earthWrappingPoly() {
		return new Wgs84Polygon(Arrays.asList(new Wgs84(-180.0, -90.0), new Wgs84(-180.0, 90.0),
				new Wgs84(180.0, -90.0), new Wgs84(180.0, 90.0)));
	}

	/**
	 * Whether this is a valid polygon: at least 3 vertices.
	 *
	 * @return {@code true} if there are 3 or more vertices
	 */
	@Override
	public boolean isValid() {
		return this.vertices.size() >= 3;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj) {
			return true;
		}
		if (!(obj instanceof Wgs84Polygon)) {
			return false;
		}
		Wgs84Polygon other = (Wgs84Polygon) obj;
		if (this.vertices.size() != other.vertices.size()) {
			return false;
		}
		for (int i = 0; i < this.vertices.size(); i++) {
			if (!this.vertices.get(i).equals(other.vertices.get(i))) {
				return false;
			}
		}
		return true;
	}

	@Override
	public int hashCode() {
		int h = 1;
		for (Wgs84 v : this.vertices) {
			h = 31 * h + v.hashCode();
		}
		return h;
	}

	/**
	 * The axis-aligned bounding box of this polygon.
	 *
	 * <p>
	 * Returns a default (empty) {@link Wgs84Aabb} if the polygon is invalid (fewer
	 * than 3 vertices). The size is computed as raw coordinate differences (not
	 * normalized), then handed to the {@link Wgs84Aabb} constructor, which still
	 * applies the excess-height clamp.
	 * </p>
	 *
	 * @return the bounding box
	 */
	public Wgs84Aabb aaBb() {
		if (!isValid()) {
			return new Wgs84Aabb();
		}

		double minLon = Double.POSITIVE_INFINITY;
		double maxLon = Double.NEGATIVE_INFINITY;
		double minLat = Double.POSITIVE_INFINITY;
		double maxLat = Double.NEGATIVE_INFINITY;
		for (Wgs84 v : this.vertices) {
			minLon = Math.min(minLon, v.longitude());
			maxLon = Math.max(maxLon, v.longitude());
			minLat = Math.min(minLat, v.latitude());
			maxLat = Math.max(maxLat, v.latitude());
		}

		return new Wgs84Aabb(new Wgs84(minLon, minLat), new Vec2(maxLon - minLon, maxLat - minLat));
	}

	/**
	 * The centroid (mean longitude, mean latitude) of the polygon vertices.
	 *
	 * <p>
	 * The means are accumulated as {@code sum(coord / n)} (not
	 * {@code sum(coord) / n}) to match the C++ reference's floating-point rounding.
	 * </p>
	 *
	 * @return the centroid point
	 */
	public Wgs84 median() {
		int n = this.vertices.size();
		double medLat = 0.0;
		for (Wgs84 p : this.vertices) {
			medLat += p.latitude() / n;
		}
		double medLon = 0.0;
		for (Wgs84 p : this.vertices) {
			medLon += p.longitude() / n;
		}
		return new Wgs84(medLon, medLat);
	}

	/**
	 * Whether this polygon collides with {@code other} (Separating-Axis Theorem).
	 *
	 * <p>
	 * The earth-wrapping sentinel collides with everything. Otherwise the SAT axis
	 * sets are taken from this polygon's edges (first test) and from
	 * {@code other}'s edges (second test); if no separating axis is found on
	 * either, the polygons collide.
	 * </p>
	 *
	 * @param other
	 *            the polygon to test against
	 * @return {@code true} if the polygons collide
	 */
	public boolean collidesWith(Wgs84Polygon other) {
		Wgs84Polygon earth = earthWrappingPoly();
		if (this.equals(earth) || other.equals(earth)) {
			return true;
		}
		if (areSeparate(other, this)) {
			return false;
		}
		// NOTE: the C++ reference passes (other, other) here — axes come from
		// `other`'s edges, projecting both `this` and `other`. Preserved exactly.
		if (areSeparate(other, other)) {
			return false;
		}
		return true;
	}

	private static Vec2 projectOnAxis(Wgs84Polygon poly, Vec2 axis) {
		double minimum = Double.POSITIVE_INFINITY;
		double maximum = Double.NEGATIVE_INFINITY;

		List<Wgs84> vs = poly.vertices;
		int n = vs.size();
		for (int i = 0; i < n; i++) {
			int ni = (i + 1 == n) ? 0 : i + 1;
			double begX = vs.get(i).longitude();
			double begY = vs.get(i).latitude();
			double endX = vs.get(ni).longitude();
			double endY = vs.get(ni).latitude();

			double x0 = begX * axis.x + begY * axis.y;
			minimum = Math.min(minimum, x0);
			maximum = Math.max(maximum, x0);

			double x1 = x0 + (endX - begX) * axis.x + (endY - begY) * axis.y;
			minimum = Math.min(minimum, x1);
			maximum = Math.max(maximum, x1);
		}

		return new Vec2(minimum, maximum);
	}

	private static boolean areSeparate1d(Vec2 minMax1, Vec2 minMax2) {
		return (minMax1.x < minMax2.x && minMax1.y < minMax2.x) || (minMax1.x > minMax2.y && minMax1.y > minMax2.y);
	}

	private boolean areSeparate(Wgs84Polygon other, Wgs84Polygon refForAxis) {
		List<Wgs84> vs = refForAxis.vertices;
		int n = vs.size();
		for (int i = 0; i < n; i++) {
			int ni = (i + 1 == n) ? 0 : i + 1;
			double dx = vs.get(ni).longitude() - vs.get(i).longitude();
			double dy = vs.get(ni).latitude() - vs.get(i).latitude();
			Vec2 normal = new Vec2(dy, -dx);

			Vec2 minMaxPoly1 = projectOnAxis(this, normal);
			Vec2 minMaxPoly2 = projectOnAxis(other, normal);

			if (areSeparate1d(minMaxPoly1, minMaxPoly2)) {
				return true;
			}
		}
		return false;
	}
}
