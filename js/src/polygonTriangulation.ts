// SPDX-License-Identifier: BSD-3-Clause

import { PolygonType } from './polygon.js';
import { Wgs84 } from './wgs84.js';
import { Wgs84Polygon } from './wgs84Polygon.js';

/**
 * Ear-clipping polygon triangulation.
 *
 * Port of the C++ `PolygonTriangulation` (`cpp/include/ndsmath/
 * polygontriangulation.h` and `.cpp`). The C++ implementation uses a
 * pointer-linked ring of partition vertices; this port uses an index-linked
 * array of {@link PartitionVertex} (`previous` / `next` integer indices) to
 * avoid manual memory management while reproducing the same traversal.
 *
 * NOTE: the *set* of output triangles is deterministic, but the ordering of
 * triangles and the rotation of each triangle's three vertices are
 * implementation-specific (driven by the "most extruded ear" tie-break and
 * floating-point `angle` comparisons). Triangulation output is therefore
 * **not** part of the cross-language parity vectors; tests assert structure
 * (type and vertex count) only.
 */

/** A node in the ear-clipping ring (index-linked replacement for pointers). */
interface PartitionVertex {
  isActive: boolean;
  isConvex: boolean;
  isEar: boolean;
  p: Wgs84;
  angle: number;
  previous: number;
  next: number;
}

/** Triangulates simple polygons by ear clipping (O(n^2)). */
export class PolygonTriangulation {
  /**
   * Triangulate a CCW simple polygon into a `TRIANGLE_LIST`.
   *
   * @param polygon A `SIMPLE_POLYGON` with at least 3 vertices, in
   *   counter-clockwise order.
   * @returns A {@link Wgs84Polygon} of type `TRIANGLE_LIST` on success
   *   (`3 * (n - 2)` vertices), or a polygon of type `UNKNOWN` on failure
   *   (wrong type, too few vertices, or no ear found).
   */
  triangulateByEarClipping(polygon: Wgs84Polygon): Wgs84Polygon {
    const result = new Wgs84Polygon(PolygonType.TRIANGLE_LIST);

    if (polygon.type() !== PolygonType.SIMPLE_POLYGON || polygon.vertices().length < 3) {
      return new Wgs84Polygon(PolygonType.UNKNOWN);
    }

    const numVertices = polygon.vertices().length;

    // Nothing to do for a single triangle.
    if (numVertices === 3) {
      result.addVertices([...polygon.vertices()]);
      return result;
    }

    const vertices: PartitionVertex[] = [];
    for (let i = 0; i < numVertices; i++) {
      vertices.push({
        isActive: true,
        isConvex: false,
        isEar: false,
        p: polygon.get(i),
        angle: 0.0,
        next: i === numVertices - 1 ? 0 : i + 1,
        previous: i === 0 ? numVertices - 1 : i - 1,
      });
    }

    for (let i = 0; i < numVertices; i++) {
      this.updateVertex(i, vertices, numVertices);
    }

    let ear = -1;
    for (let i = 0; i < numVertices - 3; i++) {
      let earFound = false;

      // Find the most extruded ear (largest angle; first wins ties).
      for (let j = 0; j < numVertices; j++) {
        if (!vertices[j].isActive || !vertices[j].isEar) {
          continue;
        }
        if (!earFound) {
          earFound = true;
          ear = j;
        } else if (vertices[j].angle > vertices[ear].angle) {
          ear = j;
        }
      }

      if (!earFound) {
        return new Wgs84Polygon(PolygonType.UNKNOWN);
      }

      const earV = vertices[ear];
      result.addVertex(vertices[earV.previous].p);
      result.addVertex(earV.p);
      result.addVertex(vertices[earV.next].p);

      earV.isActive = false;
      vertices[earV.previous].next = earV.next;
      vertices[earV.next].previous = earV.previous;

      if (i === numVertices - 4) {
        break;
      }

      this.updateVertex(earV.previous, vertices, numVertices);
      this.updateVertex(earV.next, vertices, numVertices);
    }

    for (let i = 0; i < numVertices; i++) {
      if (vertices[i].isActive) {
        result.addVertex(vertices[vertices[i].previous].p);
        result.addVertex(vertices[i].p);
        result.addVertex(vertices[vertices[i].next].p);
        break;
      }
    }

    return result;
  }

  /**
   * Vector-normalize `p`; `(0, 0)` if it has zero length.
   *
   * Mirrors the C++ `normalize`: the unit vector is wrapped back into a
   * {@link Wgs84} (which re-normalizes as a coordinate). Odd, but part of the
   * reference behavior.
   */
  private normalize(p: Wgs84): Wgs84 {
    const n = Math.sqrt(p.x * p.x + p.y * p.y);
    if (n !== 0.0) {
      return new Wgs84(p.x / n, p.y / n);
    }
    return new Wgs84(0.0, 0.0);
  }

  /** Whether the turn `p1 -> p2 -> p3` is convex (positive cross product). */
  private isConvex(p1: Wgs84, p2: Wgs84, p3: Wgs84): boolean {
    return (p3.y - p1.y) * (p2.x - p1.x) - (p3.x - p1.x) * (p2.y - p1.y) > 0.0;
  }

  /** Whether point `p` lies inside triangle `(p1, p2, p3)`. */
  private isInside(p1: Wgs84, p2: Wgs84, p3: Wgs84, p: Wgs84): boolean {
    return !this.isConvex(p1, p, p2) && !this.isConvex(p2, p, p3) && !this.isConvex(p3, p, p1);
  }

  /** Recompute convexity, ear status, and angle of vertex `vIdx`. */
  private updateVertex(vIdx: number, vertices: PartitionVertex[], numVertices: number): void {
    const v = vertices[vIdx];
    const v1 = vertices[v.previous];
    const v3 = vertices[v.next];
    v.isConvex = this.isConvex(v1.p, v.p, v3.p);

    // The subtraction goes through Wgs84 `sub` which re-normalizes.
    const vec1 = this.normalize(v1.p.sub(v.p));
    const vec3 = this.normalize(v3.p.sub(v.p));

    v.angle = vec1.x * vec3.x + vec1.y * vec3.y;

    if (v.isConvex) {
      v.isEar = true;
      for (let i = 0; i < numVertices; i++) {
        if (vertices[i].p.x === v.p.x && vertices[i].p.y === v.p.y) {
          continue;
        }
        if (vertices[i].p.x === v1.p.x && vertices[i].p.y === v1.p.y) {
          continue;
        }
        if (vertices[i].p.x === v3.p.x && vertices[i].p.y === v3.p.y) {
          continue;
        }
        if (this.isInside(v1.p, v.p, v3.p, vertices[i].p)) {
          v.isEar = false;
          break;
        }
      }
    } else {
      v.isEar = false;
    }
  }
}
