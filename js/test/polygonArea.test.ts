// SPDX-License-Identifier: BSD-3-Clause
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import {
  Vec2,
  validPolygonArea,
  polygonAreasIntersect,
  classifyPolygonRectangle,
  PolygonAreaRelation,
} from '../src/index.js';
interface Case {
  name: string;
  exterior: number[][];
  holes: number[][][];
  valid: boolean;
  intersections: Array<{ exterior: number[][]; holes: number[][][]; intersects: boolean }>;
  queries: Array<{ minimum: number[]; maximum: number[]; relation: number }>;
}
const rows = (
  JSON.parse(
    readFileSync(new URL('../../test-vectors/parity_vectors.json', import.meta.url), 'utf8'),
  ) as { polygon_area: Case[] }
).polygon_area;
const point = (p: number[]): Vec2 => new Vec2(p[0], p[1]);
describe('closed polygon areas', () => {
  for (const row of rows)
    it(row.name, () => {
      const exterior = row.exterior.map(point),
        holes = row.holes.map((r) => r.map(point));
      expect(validPolygonArea(exterior, holes)).toBe(row.valid);
      for (const other of row.intersections)
        expect(
          polygonAreasIntersect(
            exterior,
            holes,
            other.exterior.map(point),
            other.holes.map((r) => r.map(point)),
          ),
        ).toBe(other.intersects);
      for (const q of row.queries)
        expect(classifyPolygonRectangle(exterior, holes, point(q.minimum), point(q.maximum))).toBe(
          q.relation,
        );
    });
  it('rejects nonfinite input', () => {
    expect(validPolygonArea([new Vec2(0, 0), new Vec2(1, 0), new Vec2(NaN, 1)])).toBe(false);
    expect(
      classifyPolygonRectangle(
        [new Vec2(0, 0), new Vec2(1, 0), new Vec2(0, 1)],
        [],
        new Vec2(Infinity, 0),
        new Vec2(1, 1),
      ),
    ).toBe(PolygonAreaRelation.OUTSIDE);
  });
});
