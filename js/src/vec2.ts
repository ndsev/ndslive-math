// SPDX-License-Identifier: BSD-3-Clause

/**
 * A plain 2D vector that is *not* WGS84-normalized.
 *
 * The geometry layer ({@link Wgs84Aabb} in particular) needs a raw `(dx, dy)`
 * extent that can legitimately exceed `360` / `180` degrees or be negative —
 * unlike {@link Wgs84}, whose constructor wraps longitude and clamps latitude.
 * Reusing `Wgs84` for a size/extent would silently corrupt those values via
 * normalization, so this small struct is used instead.
 *
 * It mirrors the role of `glm::dvec2` (used as `Wgs84<T>::vec2_t`) in the C++
 * reference (`cpp/include/ndsmath/wgs84aabb.h`).
 */
export class Vec2 {
  /** The longitude/horizontal component. */
  x: number;
  /** The latitude/vertical component. */
  y: number;

  constructor(x = 0.0, y = 0.0) {
    this.x = x;
    this.y = y;
  }

  /** Component-wise addition (returns a new vector). */
  add(other: Vec2): Vec2 {
    return new Vec2(this.x + other.x, this.y + other.y);
  }

  /** Component-wise subtraction (returns a new vector). */
  sub(other: Vec2): Vec2 {
    return new Vec2(this.x - other.x, this.y - other.y);
  }

  /** Scalar multiplication (returns a new vector). */
  mul(scalar: number): Vec2 {
    return new Vec2(this.x * scalar, this.y * scalar);
  }

  /** Component-wise absolute value (returns a new vector). */
  abs(): Vec2 {
    return new Vec2(Math.abs(this.x), Math.abs(this.y));
  }

  toString(): string {
    return `Vec2(x=${this.x}, y=${this.y})`;
  }
}
