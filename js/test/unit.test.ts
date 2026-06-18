// SPDX-License-Identifier: MIT

import { describe, it, expect } from 'vitest';
import {
  Wgs84,
  MortonCode,
  PackedTileId,
  NdsBoundingBox,
  boundingBoxFromTileIds,
} from '../src/index.js';

describe('Wgs84 constants', () => {
  it('matches the reference constants', () => {
    expect(Wgs84.EARTH_RADIUS_IN_METERS).toBe(6371000.8);
    expect(Wgs84.LON_NDS_DELTA).toBe(360 / (2 ** 32 - 1));
    expect(Wgs84.LAT_NDS_DELTA).toBe(180 / (2 ** 31 - 1));
  });
});

describe('Wgs84 normalization', () => {
  it('defaults to origin', () => {
    const p = new Wgs84();
    expect(p.x).toBe(0);
    expect(p.y).toBe(0);
    expect(p.z).toBe(0);
  });

  it('wraps longitude > 180', () => {
    const p = new Wgs84(360.5, 0);
    expect(p.x).toBeCloseTo(0.5, 9);
  });

  it('wraps longitude < -180', () => {
    const p = new Wgs84(-360.5, 0);
    expect(p.x).toBeCloseTo(-0.5, 9);
  });

  it('wraps a longitude that lands at/above 180 after fmod', () => {
    // 181 stays 181 after fmod(181,360); the snap does not apply, so the
    // >= 180 branch wraps it to -179.
    const p = new Wgs84(181, 0);
    expect(p.x).toBeCloseTo(-179, 9);
  });

  it('wraps a longitude just below -180 after fmod', () => {
    // -181 stays -181 after fmod; the < -180 branch wraps it to 179.
    const p = new Wgs84(-181, 0);
    expect(p.x).toBeCloseTo(179, 9);
  });

  it('clamps latitude to the max representable value', () => {
    const p = new Wgs84(0, 90);
    expect(p.y).toBe(90 - Wgs84.LAT_NDS_DELTA);
  });

  it('clamps a latitude well above the max', () => {
    // 95 is far outside the snap window, so the explicit > clamp fires.
    const p = new Wgs84(0, 95);
    expect(p.y).toBe(90 - Wgs84.LAT_NDS_DELTA);
  });

  it('clamps latitude to -90', () => {
    const p = new Wgs84(0, -100);
    expect(p.y).toBe(-90);
  });

  it('snaps longitude near the max representable value', () => {
    const target = 180 - Wgs84.LON_NDS_DELTA;
    const p = new Wgs84(target + Wgs84.LON_NDS_DELTA * 0.4, 0);
    expect(p.x).toBe(target);
  });

  it('re-normalizes after direct mutation', () => {
    const p = new Wgs84(0, 0);
    p.x = 370;
    p.normalize();
    expect(p.x).toBeCloseTo(10, 9);
  });

  it('preserves altitude', () => {
    const p = new Wgs84(10, 20, 123.5);
    expect(p.z).toBe(123.5);
  });
});

describe('Wgs84 arithmetic and equality', () => {
  it('adds and subtracts component-wise', () => {
    const a = new Wgs84(10, 20);
    const b = new Wgs84(5, 5);
    expect(a.add(b).x).toBeCloseTo(15, 9);
    expect(a.add(b).y).toBeCloseTo(25, 9);
    expect(a.sub(b).x).toBeCloseTo(5, 9);
    expect(a.sub(b).y).toBeCloseTo(15, 9);
  });

  it('multiplies and divides component-wise', () => {
    const a = new Wgs84(10, 20);
    const b = new Wgs84(2, 4);
    expect(a.mul(b).x).toBeCloseTo(20, 9);
    expect(a.mul(b).y).toBeCloseTo(80, 9);
    expect(a.div(b).x).toBeCloseTo(5, 9);
    expect(a.div(b).y).toBeCloseTo(5, 9);
  });

  it('compares with a tolerance', () => {
    expect(new Wgs84(10, 20).equals(new Wgs84(10, 20))).toBe(true);
    expect(new Wgs84(10, 20).equals(new Wgs84(10.0001, 20))).toBe(false);
  });

  it('has a readable string form', () => {
    expect(new Wgs84(1, 2).toString()).toBe('Wgs84(lon=1, lat=2)');
  });
});

describe('Wgs84.toDegreeMinutesSeconds', () => {
  it('formats north/east', () => {
    const [lat, lon] = new Wgs84(13.404954, 52.520008).toDegreeMinutesSeconds();
    expect(lat).toMatch(/N$/);
    expect(lon).toMatch(/E$/);
    expect(lat.startsWith('52°')).toBe(true);
    expect(lon.startsWith('13°')).toBe(true);
  });

  it('formats south/west', () => {
    const [lat, lon] = new Wgs84(-43.1729, -22.9068).toDegreeMinutesSeconds();
    expect(lat).toMatch(/S$/);
    expect(lon).toMatch(/W$/);
  });
});

describe('Wgs84.degreesToMeters', () => {
  it('shrinks longitude toward the poles', () => {
    const [wEq] = Wgs84.degreesToMeters(1, 0, 0);
    const [wHigh] = Wgs84.degreesToMeters(1, 0, 60);
    expect(wEq).toBeCloseTo(111320, 6);
    expect(wHigh).toBeCloseTo(111320 * Math.cos((60 * Math.PI) / 180), 6);
  });

  it('keeps latitude distance constant', () => {
    const [, hEq] = Wgs84.degreesToMeters(0, 1, 0);
    const [, hHigh] = Wgs84.degreesToMeters(0, 1, 60);
    expect(hEq).toBe(hHigh);
  });
});

describe('Wgs84 floor (not truncation) for NDS conversion', () => {
  it('uses floor for negative coordinates', () => {
    // -1e-06 deg => floor of a small negative number => -12, not 0
    const [x, y] = new Wgs84(-1e-6, -1e-6).toNdsCoordinates();
    expect(x).toBe(-12);
    expect(y).toBe(-12);
  });
});

describe('MortonCode', () => {
  it('masks off the high bit / 64-bit range', () => {
    const huge = (1n << 70n) + 5n;
    const m = new MortonCode(huge);
    expect(m.value()).toBe(huge & ((1n << 64n) - 1n));
  });

  it('accepts a number in the constructor', () => {
    expect(new MortonCode(42).value()).toBe(42n);
  });

  it('defaults to 0', () => {
    expect(new MortonCode().value()).toBe(0n);
  });

  it('has a readable string form', () => {
    expect(new MortonCode(7n).toString()).toBe('MortonCode(value=7)');
  });

  it('masks bit 63 in the encoder', () => {
    // The encoder always clears bit 63, so the result never has it set.
    const m = MortonCode.fromNdsCoordinates(-2147483648, -1073741824);
    expect((m.value() >> 63n) & 1n).toBe(0n);
  });

  it('wraps out-of-range coordinates before encoding', () => {
    // x below -2^31 and y below -2^30 must wrap into range and match the
    // equivalent in-range coordinates.
    const x = -2147483648 - 5; // < -2^31
    const y = -1073741824 - 7; // < -2^30
    const wrapped = MortonCode.fromNdsCoordinates(x, y);
    const inRange = MortonCode.fromNdsCoordinates(x + 2 ** 32, y + 2 ** 31);
    expect(wrapped.value()).toBe(inRange.value());
  });

  it('wraps coordinates above the upper bound before encoding', () => {
    const x = 2147483648 + 3; // >= 2^31
    const y = 1073741824 + 9; // >= 2^30
    const wrapped = MortonCode.fromNdsCoordinates(x, y);
    const inRange = MortonCode.fromNdsCoordinates(x - 2 ** 32, y - 2 ** 31);
    expect(wrapped.value()).toBe(inRange.value());
  });
});

describe('PackedTileId construction & validation', () => {
  it('accepts both signed and unsigned level-15 representations', () => {
    const signed = new PackedTileId(-2147483648);
    const unsigned = new PackedTileId(2147483648);
    expect(signed.value).toBe(-2147483648);
    expect(unsigned.value).toBe(-2147483648);
    expect(signed.level()).toBe(15);
    expect(signed.mortonNumber()).toBe(0);
  });

  it('max level-15 tile has value -1', () => {
    const tile = PackedTileId.fromTileIndex(2 ** 31 - 1, 15);
    expect(tile.value).toBe(-1);
  });

  it('masks values outside 32 bits', () => {
    const tile = new PackedTileId(2 ** 32 + 65536);
    expect(tile.value).toBe(65536);
  });

  it('rejects values below the minimum', () => {
    expect(() => new PackedTileId(0)).toThrow();
    expect(() => new PackedTileId(65535)).toThrow();
  });

  it('rejects a value whose morton exceeds the level range', () => {
    // Level 0 allows morton 0..1; value 65538 => morton 2 (out of range).
    expect(() => new PackedTileId(65538)).toThrow(/morton number/);
  });

  it('rejects out-of-range level in fromTileIndex', () => {
    expect(() => PackedTileId.fromTileIndex(0, -1)).toThrow(RangeError);
    expect(() => PackedTileId.fromTileIndex(0, 16)).toThrow(RangeError);
  });

  it('rejects out-of-range morton in fromTileIndex', () => {
    expect(() => PackedTileId.fromTileIndex(-1, 1)).toThrow(RangeError);
    // level 1 allows morton 0..7
    expect(() => PackedTileId.fromTileIndex(8, 1)).toThrow(RangeError);
  });

  it('rejects out-of-range level in fromMortonAndLevel', () => {
    const m = MortonCode.fromNdsCoordinates(0, 0);
    expect(() => PackedTileId.fromMortonAndLevel(m, 16)).toThrow(RangeError);
  });

  it('equals compares internal value', () => {
    const a = PackedTileId.fromTileIndex(4, 2);
    const b = new PackedTileId(262148);
    expect(a.equals(b)).toBe(true);
    expect(a.equals(PackedTileId.fromTileIndex(5, 2))).toBe(false);
  });

  it('has a readable string form', () => {
    expect(PackedTileId.fromTileIndex(0, 0).toString()).toBe('PackedTileId(value=65536)');
  });

  it('dimensionsInMeters returns positive width/height', () => {
    const tile = PackedTileId.fromTileIndex(0, 13);
    const [w, h] = tile.dimensionsInMeters();
    expect(w).toBeGreaterThan(0);
    expect(h).toBeGreaterThan(0);
  });
});

describe('neighbour wrapping', () => {
  it('east of the easternmost wraps to westernmost (level 0)', () => {
    const east = PackedTileId.fromTileIndex(1, 0); // morton 1 at level 0
    expect(east.eastNeighbour().mortonNumber()).toBe(0);
    expect(east.westNeighbour().mortonNumber()).toBe(0);
  });

  it('north/south are identical at level 0 (single row)', () => {
    const t = PackedTileId.fromTileIndex(0, 0);
    expect(t.northNeighbour().value).toBe(t.southNeighbour().value);
  });
});

describe('boundingBoxFromTileIds', () => {
  it('throws on an empty list', () => {
    expect(() => boundingBoxFromTileIds([])).toThrow();
  });

  it('accepts PackedTileId objects', () => {
    const tile = PackedTileId.fromTileIndex(0, 1);
    const bbox = boundingBoxFromTileIds([tile]);
    expect(bbox).toEqual([0, 0, 1073741823, 1073741823]);
  });

  it('unions multiple tiles', () => {
    const t0 = PackedTileId.fromTileIndex(0, 1);
    const t3 = PackedTileId.fromTileIndex(3, 1);
    const bbox = boundingBoxFromTileIds([t0, t3]);
    // t0 covers [0,0]..[2^30,2^30); t3 covers SE quadrant below.
    expect(bbox[0]).toBe(0);
    expect(bbox[2]).toBe(2147483647);
  });
});

describe('NdsBoundingBox.fromTile', () => {
  it('builds from an integer tile id', () => {
    const bbox = NdsBoundingBox.fromTile(131072);
    expect(bbox.minX).toBe(0);
    expect(bbox.minY).toBe(0);
    expect(bbox.maxX).toBe(1073741824);
    expect(bbox.maxY).toBe(1073741824);
  });

  it('builds from a PackedTileId object', () => {
    const tile = PackedTileId.fromTileIndex(0, 1);
    const bbox = NdsBoundingBox.fromTile(tile);
    expect(bbox.maxX).toBe(1073741824);
  });
});

describe('distance/bearing edge cases', () => {
  it('distance to self is zero', () => {
    const p = new Wgs84(10, 20);
    expect(p.distanceTo(p)).toBeCloseTo(0, 6);
  });
});
