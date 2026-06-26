// SPDX-License-Identifier: BSD-3-Clause

import { Wgs84 } from './wgs84.js';

/**
 * Generic polygon container with orientation, mirroring the C++ `Polygon`.
 *
 * Port of `cpp/include/ndsmath/polygon.h`. The C++ class is a template over a
 * vertex container; here it is specialized directly to a list of {@link Wgs84}
 * vertices. Orientation is computed on the raw `(lon, lat)` plane (no WGS84
 * normalization, no antimeridian handling).
 */

/** Winding order of a polygon. Integer values match the C++ enum. */
export enum Orientation {
  CLOCKWISE = -1,
  INVALID_ORIENTATION = 0,
  COUNTERCLOCKWISE = 1,
}

/** Polygon topology. Integer values match the C++ enum. */
export enum PolygonType {
  /**
   * A simple polygon with an arbitrary number of vertices and no holes; the
   * last vertex connects back to the first.
   */
  SIMPLE_POLYGON = 0,
  /** A triangle strip. */
  TRIANGLE_STRIP = 1,
  /** A triangle fan. */
  TRIANGLE_FAN = 2,
  /** A set of independent triangles; three consecutive vertices form one. */
  TRIANGLE_LIST = 3,
  /** Illegal polygon type, used to signal failure. */
  UNKNOWN = 4,
}

/**
 * A set of vertices with a topology type and orientation query.
 *
 * Mirrors the C++ `Polygon<Vector>` template. The base {@link Polygon.isValid}
 * requires at least one vertex; subclasses (e.g. {@link Wgs84Polygon}) may
 * override it.
 */
export class Polygon {
  protected polygonType: PolygonType;
  protected verts: Wgs84[];

  /**
   * Construct a polygon.
   *
   * @param polygonType The polygon topology. Defaults to `UNKNOWN`.
   * @param vertices Optional initial vertices (copied).
   */
  constructor(polygonType: PolygonType = PolygonType.UNKNOWN, vertices?: readonly Wgs84[]) {
    this.polygonType = polygonType;
    this.verts = vertices !== undefined ? [...vertices] : [];
  }

  /** Append a single vertex. */
  addVertex(position: Wgs84): void {
    this.verts.push(position);
  }

  /** Append a list of vertices, in order. */
  addVertices(vertices: readonly Wgs84[]): void {
    this.verts.push(...vertices);
  }

  /** Array subscript access to a vertex (no bounds check, like C++). */
  get(index: number): Wgs84 {
    return this.verts[index];
  }

  /** Replace the vertex at `index`. */
  set(index: number, value: Wgs84): void {
    this.verts[index] = value;
  }

  /** Number of vertices. */
  get length(): number {
    return this.verts.length;
  }

  /** Get the polygon type. */
  type(): PolygonType {
    return this.polygonType;
  }

  /** Set the polygon type. */
  setType(polygonType: PolygonType): void {
    this.polygonType = polygonType;
  }

  /**
   * Whether this is a valid polygon.
   *
   * Base implementation: at least one vertex. Overridden by
   * {@link Wgs84Polygon} to require >= 3.
   */
  isValid(): boolean {
    return this.verts.length > 0;
  }

  /** Get the (mutable) list of vertices. */
  vertices(): Wgs84[] {
    return this.verts;
  }

  /**
   * Compute the winding order via the signed shoelace formula.
   *
   * Only works for `SIMPLE_POLYGON` and a single-triangle `TRIANGLE_LIST`
   * (exactly 3 vertices). All other types return `INVALID_ORIENTATION` without
   * computing area. Collinear vertices (zero area) also return
   * `INVALID_ORIENTATION`.
   *
   * Uses raw `(lon, lat)` doubles; no normalization.
   */
  orientation(): Orientation {
    if (
      this.polygonType !== PolygonType.SIMPLE_POLYGON &&
      !(this.polygonType === PolygonType.TRIANGLE_LIST && this.verts.length === 3)
    ) {
      return Orientation.INVALID_ORIENTATION;
    }

    const n = this.verts.length;
    let area = 0.0;
    for (let i = 0; i < n; i++) {
      let j = i + 1;
      if (j === n) {
        j = 0;
      }
      area += this.verts[i].x * this.verts[j].y;
      area -= this.verts[i].y * this.verts[j].x;
    }

    if (area > 0) {
      return Orientation.COUNTERCLOCKWISE;
    } else if (area < 0) {
      return Orientation.CLOCKWISE;
    } else {
      return Orientation.INVALID_ORIENTATION;
    }
  }
}
