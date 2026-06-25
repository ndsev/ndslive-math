// SPDX-License-Identifier: BSD-3-Clause

import { describe, it, expect } from 'vitest';
import {
  Wgs84,
  MortonCode,
  PackedTileId,
  Vec2,
  Polygon,
  Orientation,
  PolygonType,
  Wgs84Aabb,
  Wgs84Polygon,
} from '../src/index.js';

describe('Wgs84 geometry support', () => {
  it('exposes the power-of-two NDS deltas and bounds', () => {
    expect(Wgs84.LON_NDS_DELTA_POW2).toBe(360 / 2 ** 32);
    expect(Wgs84.LAT_NDS_DELTA_POW2).toBe(180 / 2 ** 31);
    expect(Wgs84.LON_MIN).toBe(-180);
    expect(Wgs84.LON_MAX).toBe(180 - 360 / 2 ** 32);
    expect(Wgs84.LON_MAX).toBeCloseTo(179.99999991618097, 9);
    expect(Wgs84.LAT_MIN).toBe(-90);
    expect(Wgs84.LAT_MAX).toBe(90 - 180 / 2 ** 31);
  });

  it('these differ from the (2^32 - 1) deltas in the 13th significant digit', () => {
    expect(Wgs84.LON_NDS_DELTA_POW2).not.toBe(Wgs84.LON_NDS_DELTA);
  });

  it('accessors return the x/y components', () => {
    const p = new Wgs84(11.5, 48.1);
    expect(p.longitude()).toBe(p.x);
    expect(p.latitude()).toBe(p.y);
    expect(p.dx()).toBe(p.x);
    expect(p.dy()).toBe(p.y);
  });

  it('fromMortonCode scales BOTH axes by 360/2^32', () => {
    const morton = MortonCode.fromNdsCoordinates(0, 0);
    const w = Wgs84.fromMortonCode(morton);
    expect(w.x).toBe(0);
    expect(w.y).toBe(0);
  });

  it('fromMortonCode scales latitude by 360/2^32 (== 180/2^31 numerically)', () => {
    // fromMortonCode uses bitScaling = 360/2^32 for BOTH axes. Because
    // 360/2^32 === 180/2^31 as IEEE doubles, the latitude it produces happens
    // to coincide with fromNdsCoordinates for the same NDS coords; the
    // distinction in the reference is in the formula, not the bit pattern.
    expect(360 / 2 ** 32).toBe(180 / 2 ** 31);

    const x = 1 << 20;
    const y = 1 << 20;
    const morton = MortonCode.fromNdsCoordinates(x, y);
    const [dx, dy] = morton.toNdsCoordinates();
    const fromMorton = Wgs84.fromMortonCode(morton);
    expect(fromMorton.x).toBeCloseTo(dx * (360 / 2 ** 32), 9);
    expect(fromMorton.y).toBeCloseTo(dy * (360 / 2 ** 32), 9);
  });
});

describe('Vec2', () => {
  it('supports component-wise add / sub / scalar mul / abs', () => {
    const a = new Vec2(3, 4);
    const b = new Vec2(1, 2);
    expect(a.add(b)).toMatchObject({ x: 4, y: 6 });
    expect(a.sub(b)).toMatchObject({ x: 2, y: 2 });
    expect(a.mul(2)).toMatchObject({ x: 6, y: 8 });
    expect(new Vec2(-3, -4).abs()).toMatchObject({ x: 3, y: 4 });
  });

  it('defaults to (0, 0) and stringifies', () => {
    const v = new Vec2();
    expect(v.x).toBe(0);
    expect(v.y).toBe(0);
    expect(v.toString()).toBe('Vec2(x=0, y=0)');
  });
});

describe('Polygon (base)', () => {
  it('defaults to UNKNOWN with no vertices', () => {
    const p = new Polygon();
    expect(p.type()).toBe(PolygonType.UNKNOWN);
    expect(p.length).toBe(0);
    expect(p.isValid()).toBe(false);
  });

  it('add/get/set/length/setType work', () => {
    const p = new Polygon(PolygonType.SIMPLE_POLYGON);
    p.addVertex(new Wgs84(0, 0));
    p.addVertices([new Wgs84(1, 0), new Wgs84(0, 1)]);
    expect(p.length).toBe(3);
    expect(p.isValid()).toBe(true);
    expect(p.get(1).x).toBe(1);
    p.set(1, new Wgs84(2, 0));
    expect(p.get(1).x).toBe(2);
    expect(p.vertices().length).toBe(3);
    p.setType(PolygonType.TRIANGLE_FAN);
    expect(p.type()).toBe(PolygonType.TRIANGLE_FAN);
  });

  it('orientation: CCW / CW / collinear / unsupported type', () => {
    const ccw = new Polygon(PolygonType.SIMPLE_POLYGON, [
      new Wgs84(0, 0),
      new Wgs84(1, 0),
      new Wgs84(0, 1),
    ]);
    expect(ccw.orientation()).toBe(Orientation.COUNTERCLOCKWISE);

    const cw = new Polygon(PolygonType.SIMPLE_POLYGON, [
      new Wgs84(0, 0),
      new Wgs84(0, 1),
      new Wgs84(1, 0),
    ]);
    expect(cw.orientation()).toBe(Orientation.CLOCKWISE);

    const collinear = new Polygon(PolygonType.SIMPLE_POLYGON, [
      new Wgs84(0, 0),
      new Wgs84(1, 1),
      new Wgs84(2, 2),
    ]);
    expect(collinear.orientation()).toBe(Orientation.INVALID_ORIENTATION);

    const strip = new Polygon(PolygonType.TRIANGLE_STRIP, [
      new Wgs84(0, 0),
      new Wgs84(1, 0),
      new Wgs84(0, 1),
    ]);
    expect(strip.orientation()).toBe(Orientation.INVALID_ORIENTATION);

    const singleTriList = new Polygon(PolygonType.TRIANGLE_LIST, [
      new Wgs84(0, 0),
      new Wgs84(1, 0),
      new Wgs84(0, 1),
    ]);
    expect(singleTriList.orientation()).toBe(Orientation.COUNTERCLOCKWISE);
  });
});

describe('Wgs84Aabb', () => {
  it('default box is valid with zero size', () => {
    const box = new Wgs84Aabb();
    expect(box.valid()).toBe(true);
    expect(box.size().x).toBe(0);
    expect(box.size().y).toBe(0);
    expect(box.sw().x).toBe(0);
  });

  it('clamps excess height for valid boxes', () => {
    const box = new Wgs84Aabb(new Wgs84(0, 85), new Vec2(10, 10));
    expect(box.size().y).toBeCloseTo(5, 9);
    expect(box.ne().y).toBeCloseTo(90 - Wgs84.LAT_NDS_DELTA_POW2, 6);
  });

  it('leaves invalid (negative-size) boxes unclamped', () => {
    const box = new Wgs84Aabb(new Wgs84(0, 85), new Vec2(-1, 10));
    expect(box.valid()).toBe(false);
    expect(box.size().y).toBe(10);
  });

  it('fromTile (Path A) covers a level-10 origin tile', () => {
    const tile = PackedTileId.fromTileIndex(0, 10);
    const box = Wgs84Aabb.fromTile(tile);
    expect(box.valid()).toBe(true);
    expect(box.sw().x).toBeCloseTo(0, 9);
    expect(box.sw().y).toBeCloseTo(0, 9);
    // tile width = 2^21 * 360/2^32 = 0.17578125 degrees.
    expect(box.size().x).toBeCloseTo(0.17578125, 9);
    expect(box.size().y).toBeCloseTo(0.17578125, 9);
  });

  it('fromCenterAndTileLimit builds a box around a center', () => {
    const box = Wgs84Aabb.fromCenterAndTileLimit(new Wgs84(10, 20), 16, 10);
    expect(box.valid()).toBe(true);
    // Center is preserved (re-normalized arithmetic) approximately.
    expect(box.center().x).toBeCloseTo(10, 6);
    expect(box.center().y).toBeCloseTo(20, 6);
  });

  it('avgMercatorStretch is finite', () => {
    const box = new Wgs84Aabb(new Wgs84(0, 10), new Vec2(20, 10));
    expect(Number.isFinite(box.avgMercatorStretch())).toBe(true);
  });

  it('splitOverAntiMeridian returns null for a non-crossing box', () => {
    const box = new Wgs84Aabb(new Wgs84(0, 0), new Vec2(20, 10));
    expect(box.splitOverAntiMeridian()).toBeNull();
  });
});

describe('Wgs84Polygon', () => {
  it('defaults to a SIMPLE_POLYGON', () => {
    const p = new Wgs84Polygon();
    expect(p.type()).toBe(PolygonType.SIMPLE_POLYGON);
    expect(p.isValid()).toBe(false);
  });

  it('isValid requires >= 3 vertices', () => {
    expect(new Wgs84Polygon(undefined, [new Wgs84(0, 0), new Wgs84(1, 0)]).isValid()).toBe(false);
    expect(
      new Wgs84Polygon(undefined, [new Wgs84(0, 0), new Wgs84(1, 0), new Wgs84(0, 1)]).isValid(),
    ).toBe(true);
  });

  it('aaBb returns a default box for an invalid polygon', () => {
    const bb = new Wgs84Polygon(undefined, [new Wgs84(0, 0), new Wgs84(1, 0)]).aaBb();
    expect(bb.size().x).toBe(0);
    expect(bb.size().y).toBe(0);
  });

  it('median preserves the lon/lat swap quirk for asymmetric polygons', () => {
    const p = new Wgs84Polygon(undefined, [new Wgs84(0, 0), new Wgs84(30, 0), new Wgs84(0, 60)]);
    const med = p.median();
    // mean_lon = 10, mean_lat = 20, but the result swaps them.
    expect(med.longitude()).toBeCloseTo(20, 9);
    expect(med.latitude()).toBeCloseTo(10, 9);
  });

  it('equals is order-sensitive and length-sensitive', () => {
    const a = new Wgs84Polygon(undefined, [new Wgs84(0, 0), new Wgs84(1, 0), new Wgs84(0, 1)]);
    const b = new Wgs84Polygon(undefined, [new Wgs84(0, 0), new Wgs84(1, 0), new Wgs84(0, 1)]);
    const reordered = new Wgs84Polygon(undefined, [
      new Wgs84(1, 0),
      new Wgs84(0, 0),
      new Wgs84(0, 1),
    ]);
    const shorter = new Wgs84Polygon(undefined, [new Wgs84(0, 0), new Wgs84(1, 0)]);
    expect(a.equals(b)).toBe(true);
    expect(a.equals(reordered)).toBe(false);
    expect(a.equals(shorter)).toBe(false);
  });

  it('earthWrappingPoly collides with any polygon (both directions)', () => {
    const earth = Wgs84Polygon.earthWrappingPoly();
    const tri = new Wgs84Polygon(undefined, [new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(0, 4)]);
    expect(earth.collidesWith(tri)).toBe(true);
    expect(tri.collidesWith(earth)).toBe(true);
  });

  it('separation detected only by the second (other-axis) SAT test', () => {
    // `diamond` has diagonal edges (its edge normals are diagonal axes); `box`
    // is axis-aligned. They are disjoint, but the diamond's diagonal axes do
    // NOT separate them — only the box's axis-aligned edge normals do. So the
    // first `areSeparate(other, this)` returns false and the second
    // `areSeparate(other, other)` returns true, exercising that branch.
    const diamond = new Wgs84Polygon(undefined, [
      new Wgs84(0, 0),
      new Wgs84(3, 3),
      new Wgs84(6, 0),
      new Wgs84(3, -3),
    ]);
    const box = new Wgs84Polygon(undefined, [
      new Wgs84(6.5, -1),
      new Wgs84(9, -1),
      new Wgs84(9, 2),
      new Wgs84(6.5, 2),
    ]);
    expect(diamond.collidesWith(box)).toBe(false);
    expect(box.collidesWith(diamond)).toBe(false);
  });
});
