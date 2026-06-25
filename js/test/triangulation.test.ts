// SPDX-License-Identifier: BSD-3-Clause

import { describe, it, expect } from 'vitest';
import { Wgs84, Wgs84Polygon, PolygonTriangulation, PolygonType } from '../src/index.js';

/**
 * Triangulation unit tests.
 *
 * Triangulation output is NOT part of the cross-language parity vectors: the
 * ordering of triangles and the rotation of each triangle's three vertices are
 * implementation-specific. These tests assert only the structural contract
 * (result type, vertex count = `3 * (n - 2)`, and that the emitted vertices are
 * drawn from the input set).
 */

function poly(verts: Array<[number, number]>, type = PolygonType.SIMPLE_POLYGON): Wgs84Polygon {
  return new Wgs84Polygon(
    type,
    verts.map(([lon, lat]) => new Wgs84(lon, lat)),
  );
}

/** Assert every output vertex coincides with one of the input vertices. */
function verticesDrawnFromInput(result: Wgs84Polygon, input: Wgs84Polygon): void {
  const inputVerts = input.vertices();
  for (const rv of result.vertices()) {
    const found = inputVerts.some((iv) => iv.x === rv.x && iv.y === rv.y);
    expect(found).toBe(true);
  }
}

describe('PolygonTriangulation', () => {
  const tri = new PolygonTriangulation();

  it('passes a single triangle through unchanged (3 vertices)', () => {
    const input = poly([
      [0, 0],
      [4, 0],
      [0, 4],
    ]);
    const result = tri.triangulateByEarClipping(input);

    expect(result.type()).toBe(PolygonType.TRIANGLE_LIST);
    expect(result.vertices().length).toBe(3);
    // 3 * (3 - 2) == 3.
    expect(result.vertices().length).toBe(3 * (input.vertices().length - 2));
    // Order is unchanged for the exactly-3-vertex fast path.
    expect(result.vertices()[0].equals(input.vertices()[0])).toBe(true);
    expect(result.vertices()[1].equals(input.vertices()[1])).toBe(true);
    expect(result.vertices()[2].equals(input.vertices()[2])).toBe(true);
  });

  it('triangulates a convex quad into two triangles (6 vertices)', () => {
    const input = poly([
      [0, 0],
      [4, 0],
      [4, 4],
      [0, 4],
    ]);
    const result = tri.triangulateByEarClipping(input);

    expect(result.type()).toBe(PolygonType.TRIANGLE_LIST);
    expect(result.vertices().length).toBe(6);
    expect(result.vertices().length).toBe(3 * (input.vertices().length - 2));
    verticesDrawnFromInput(result, input);
  });

  it('triangulates a concave polygon with a reflex vertex (9 vertices)', () => {
    // An arrow / chevron shape: vertex (2, 2) is reflex (points inward).
    const input = poly([
      [0, 0],
      [4, 0],
      [2, 2],
      [4, 4],
      [0, 4],
    ]);
    const result = tri.triangulateByEarClipping(input);

    expect(result.type()).toBe(PolygonType.TRIANGLE_LIST);
    expect(result.vertices().length).toBe(9);
    expect(result.vertices().length).toBe(3 * (input.vertices().length - 2));
    verticesDrawnFromInput(result, input);
  });

  it('returns UNKNOWN for too few vertices', () => {
    const input = poly([
      [0, 0],
      [4, 0],
    ]);
    const result = tri.triangulateByEarClipping(input);

    expect(result.type()).toBe(PolygonType.UNKNOWN);
    expect(result.vertices().length).toBe(0);
  });

  it('returns UNKNOWN for the wrong polygon type', () => {
    const input = poly(
      [
        [0, 0],
        [4, 0],
        [4, 4],
        [0, 4],
      ],
      PolygonType.TRIANGLE_LIST,
    );
    const result = tri.triangulateByEarClipping(input);

    expect(result.type()).toBe(PolygonType.UNKNOWN);
    expect(result.vertices().length).toBe(0);
  });

  it('triangulates a larger convex polygon (hexagon -> 12 vertices)', () => {
    const input = poly([
      [0, 0],
      [2, -1],
      [4, 0],
      [4, 3],
      [2, 4],
      [0, 3],
    ]);
    const result = tri.triangulateByEarClipping(input);

    expect(result.type()).toBe(PolygonType.TRIANGLE_LIST);
    expect(result.vertices().length).toBe(12);
    expect(result.vertices().length).toBe(3 * (input.vertices().length - 2));
    verticesDrawnFromInput(result, input);
  });

  it('triangulates an irregular convex polygon with unequal ear angles', () => {
    // Vertices have visibly different interior angles, so the "most extruded
    // ear" selection must replace its running best with a later, flatter ear
    // (exercising the angle tie-break-replacement branch).
    const input = poly([
      [0, 0],
      [10, 0],
      [12, 1],
      [11, 6],
      [5, 8],
      [1, 5],
    ]);
    const result = tri.triangulateByEarClipping(input);

    expect(result.type()).toBe(PolygonType.TRIANGLE_LIST);
    expect(result.vertices().length).toBe(3 * (input.vertices().length - 2));
    verticesDrawnFromInput(result, input);
  });

  it('triangulates a polygon containing duplicate (coincident) vertices', () => {
    // A repeated vertex makes one edge length zero, so the internal vector
    // normalization hits its zero-length fallback. The result should still be a
    // valid TRIANGLE_LIST of the right size.
    const input = poly([
      [0, 0],
      [4, 0],
      [4, 0],
      [4, 4],
      [0, 4],
    ]);
    const result = tri.triangulateByEarClipping(input);

    expect(result.type()).toBe(PolygonType.TRIANGLE_LIST);
    expect(result.vertices().length).toBe(3 * (input.vertices().length - 2));
  });

  it('returns UNKNOWN for a clockwise polygon with no clippable ear', () => {
    // Ear clipping requires CCW winding; a clockwise polygon has no convex ear,
    // so the search bails out and returns UNKNOWN. Five vertices ensure the
    // clip loop runs at least one iteration before failing.
    const input = poly([
      [0, 0],
      [0, 4],
      [2, 6],
      [4, 4],
      [4, 0],
    ]);
    const result = tri.triangulateByEarClipping(input);
    expect(result.type()).toBe(PolygonType.UNKNOWN);
    expect(result.vertices().length).toBe(0);
  });
});
