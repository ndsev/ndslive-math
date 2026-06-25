// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

/**
 * A plain 2D vector that is <em>not</em> WGS84-normalized.
 *
 * <p>
 * The geometry layer ({@link Wgs84Aabb} in particular) needs a raw
 * {@code (dx, dy)} extent that can legitimately exceed {@code 360} /
 * {@code 180} degrees or be negative — unlike {@link Wgs84}, whose constructor
 * wraps longitude and clamps latitude. Reusing {@code Wgs84} for a size/extent
 * would silently corrupt those values via normalization, so this small struct
 * is used instead.
 * </p>
 *
 * <p>
 * It mirrors the role of {@code glm::dvec2} (used as {@code Wgs84<T>::vec2_t})
 * in the C++ reference ({@code cpp/include/ndsmath/wgs84aabb.h}).
 * </p>
 */
public final class Vec2 {

	/** The longitude / horizontal component. */
	public double x;

	/** The latitude / vertical component. */
	public double y;

	/** Construct a zero vector {@code (0, 0)}. */
	public Vec2() {
		this(0.0, 0.0);
	}

	/**
	 * Construct a vector {@code (x, y)}.
	 *
	 * @param x
	 *            the longitude / horizontal component
	 * @param y
	 *            the latitude / vertical component
	 */
	public Vec2(double x, double y) {
		this.x = x;
		this.y = y;
	}

	/**
	 * Component-wise addition.
	 *
	 * @param other
	 *            the vector to add
	 * @return a new vector
	 */
	public Vec2 add(Vec2 other) {
		return new Vec2(this.x + other.x, this.y + other.y);
	}

	/**
	 * Component-wise subtraction.
	 *
	 * @param other
	 *            the vector to subtract
	 * @return a new vector
	 */
	public Vec2 sub(Vec2 other) {
		return new Vec2(this.x - other.x, this.y - other.y);
	}

	/**
	 * Scalar multiplication.
	 *
	 * @param scalar
	 *            the factor to multiply both components by
	 * @return a new vector
	 */
	public Vec2 mul(double scalar) {
		return new Vec2(this.x * scalar, this.y * scalar);
	}

	/**
	 * @return the component-wise absolute value
	 */
	public Vec2 abs() {
		return new Vec2(Math.abs(this.x), Math.abs(this.y));
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj) {
			return true;
		}
		if (!(obj instanceof Vec2)) {
			return false;
		}
		Vec2 other = (Vec2) obj;
		return Double.compare(this.x, other.x) == 0 && Double.compare(this.y, other.y) == 0;
	}

	@Override
	public int hashCode() {
		return Double.hashCode(this.x) * 31 + Double.hashCode(this.y);
	}

	@Override
	public String toString() {
		return "Vec2(x=" + this.x + ", y=" + this.y + ")";
	}
}
