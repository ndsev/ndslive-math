// SPDX-License-Identifier: BSD-3-Clause

import { Polygon, PolygonType } from './polygon.js';
import { Vec2 } from './vec2.js';
import { Wgs84 } from './wgs84.js';
import { Wgs84Aabb } from './wgs84Aabb.js';

/**
 * WGS84 polygon with bounding box, median, and SAT collision.
 *
 * Port of the C++ `HighPrecWgs84Polygon` (`cpp/include/ndsmath/wgs84polygon.h`).
 * A {@link Polygon} of {@link Wgs84} vertices, defaulting to `SIMPLE_POLYGON`,
 * with:
 *
 * - {@link Wgs84Polygon.aaBb} — the axis-aligned bounding box,
 * - {@link Wgs84Polygon.median} — the centroid (with a *deliberately preserved*
 *   lon/lat swap quirk from the C++ reference),
 * - {@link Wgs84Polygon.collidesWith} — Separating-Axis-Theorem collision.
 *
 * The collision math runs on raw `(lon, lat)` doubles: no normalization, no
 * antimeridian handling.
 */
export class Wgs84Polygon extends Polygon {
  /**
   * Construct a WGS84 polygon.
   *
   * Defaults to `SIMPLE_POLYGON`. Both `polygonType` and `vertices` are
   * optional, mirroring the four C++ constructors:
   *
   * - `Wgs84Polygon()` — empty simple polygon,
   * - `Wgs84Polygon(undefined, vertices)` — simple polygon with vertices,
   * - `Wgs84Polygon(polygonType)` — empty polygon of the given type,
   * - `Wgs84Polygon(polygonType, vertices)` — given type and vertices.
   */
  constructor(polygonType?: PolygonType, vertices?: readonly Wgs84[]) {
    super(polygonType ?? PolygonType.SIMPLE_POLYGON, vertices);
  }

  /**
   * The 4-vertex sentinel polygon wrapping the whole Earth.
   *
   * Constructed from `(-180,-90), (-180,90), (180,-90), (180,90)`. These
   * coordinates pass through {@link Wgs84} normalization, so the stored values
   * are not exactly those literals. This polygon is only used as an identity
   * sentinel in {@link Wgs84Polygon.collidesWith} via `equals`; its exact
   * normalized coordinates are not part of cross-language parity.
   */
  static earthWrappingPoly(): Wgs84Polygon {
    return new Wgs84Polygon(undefined, [
      new Wgs84(-180.0, -90.0),
      new Wgs84(-180.0, 90.0),
      new Wgs84(180.0, -90.0),
      new Wgs84(180.0, 90.0),
    ]);
  }

  /** Whether this is a valid polygon: at least 3 vertices. */
  override isValid(): boolean {
    return this.verts.length >= 3;
  }

  /** Order-sensitive vertex-wise equality (via {@link Wgs84.equals}). */
  equals(other: Wgs84Polygon): boolean {
    const v = this.verts;
    const vo = other.verts;
    if (v.length !== vo.length) {
      return false;
    }
    for (let i = 0; i < v.length; i++) {
      if (!v[i].equals(vo[i])) {
        return false;
      }
    }
    return true;
  }

  /**
   * The axis-aligned bounding box of this polygon.
   *
   * Returns a default (empty) {@link Wgs84Aabb} if the polygon is invalid
   * (fewer than 3 vertices). The size is computed as raw coordinate differences
   * (not normalized), then handed to the `Wgs84Aabb` constructor, which still
   * applies the excess-height clamp.
   */
  aaBb(): Wgs84Aabb {
    if (!this.isValid()) {
      return new Wgs84Aabb();
    }

    let minLon = Infinity;
    let maxLon = -Infinity;
    let minLat = Infinity;
    let maxLat = -Infinity;
    for (const v of this.verts) {
      const lon = v.longitude();
      const lat = v.latitude();
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    }

    return new Wgs84Aabb(new Wgs84(minLon, minLat), new Vec2(maxLon - minLon, maxLat - minLat));
  }

  /**
   * The centroid of the polygon vertices.
   *
   * WARNING: this faithfully reproduces a bug in the C++ reference. The C++
   * `median()` returns `HighPrecWgs84(medLat, medLon)` while the
   * `Wgs84(longitude, latitude)` constructor takes longitude first — so the
   * **mean latitude is stored in the longitude slot and the mean longitude in
   * the latitude slot**. The returned point therefore has
   * `longitude() == mean_lat` and `latitude() == mean_lon`. For symmetric
   * polygons the swap is invisible; for asymmetric ones it is observable. It is
   * preserved here for cross-language parity.
   *
   * The means are accumulated as `sum(coord / n)` per the C++ code (not
   * `sum(coord) / n`), to match its floating-point rounding.
   */
  median(): Wgs84 {
    const n = this.verts.length;
    let medLat = 0.0;
    for (const p of this.verts) {
      medLat += p.latitude() / n;
    }
    let medLon = 0.0;
    for (const p of this.verts) {
      medLon += p.longitude() / n;
    }
    // NOTE: lon/lat swap preserved from the C++ reference (see docstring).
    return new Wgs84(medLat, medLon);
  }

  /**
   * Whether this polygon collides with `other` (Separating-Axis Theorem).
   *
   * The earth-wrapping sentinel collides with everything. Otherwise the SAT
   * axis sets are taken from this polygon's edges (first test) and from
   * `other`'s edges (second test); if no separating axis is found on either,
   * the polygons collide.
   */
  collidesWith(other: Wgs84Polygon): boolean {
    const earth = Wgs84Polygon.earthWrappingPoly();
    if (this.equals(earth) || other.equals(earth)) {
      return true;
    }
    if (this.areSeparate(other, this)) {
      return false;
    }
    // NOTE: the C++ reference passes (other, other) here — axes come from
    // `other`'s edges, projecting both `this` and `other`. Preserved exactly.
    if (this.areSeparate(other, other)) {
      return false;
    }
    return true;
  }

  /** Project `poly` onto `axis`, returning `Vec2(min, max)`. */
  private projectOnAxis(poly: Wgs84Polygon, axis: Vec2): Vec2 {
    let minimum = Infinity;
    let maximum = -Infinity;

    const vs = poly.verts;
    const n = vs.length;
    for (let i = 0; i < n; i++) {
      const ni = i + 1 === n ? 0 : i + 1;
      const begX = vs[i].longitude();
      const begY = vs[i].latitude();
      const endX = vs[ni].longitude();
      const endY = vs[ni].latitude();

      const x0 = begX * axis.x + begY * axis.y;
      if (x0 < minimum) minimum = x0;
      if (x0 > maximum) maximum = x0;

      const x1 = x0 + (endX - begX) * axis.x + (endY - begY) * axis.y;
      if (x1 < minimum) minimum = x1;
      if (x1 > maximum) maximum = x1;
    }

    return new Vec2(minimum, maximum);
  }

  /** Whether two 1D intervals `(min, max)` are disjoint. */
  private areSeparate1d(minMax1: Vec2, minMax2: Vec2): boolean {
    return (
      (minMax1.x < minMax2.x && minMax1.y < minMax2.x) ||
      (minMax1.x > minMax2.y && minMax1.y > minMax2.y)
    );
  }

  /** Whether a separating axis exists among `refForAxis`'s edge normals. */
  private areSeparate(other: Wgs84Polygon, refForAxis: Wgs84Polygon): boolean {
    const vs = refForAxis.verts;
    const n = vs.length;
    for (let i = 0; i < n; i++) {
      const ni = i + 1 === n ? 0 : i + 1;
      const dx = vs[ni].longitude() - vs[i].longitude();
      const dy = vs[ni].latitude() - vs[i].latitude();
      const normal = new Vec2(dy, -dx);

      const minMaxPoly1 = this.projectOnAxis(this, normal);
      const minMaxPoly2 = this.projectOnAxis(other, normal);

      if (this.areSeparate1d(minMaxPoly1, minMaxPoly2)) {
        return true;
      }
    }
    return false;
  }
}
