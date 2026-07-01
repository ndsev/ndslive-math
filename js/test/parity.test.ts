// SPDX-License-Identifier: BSD-3-Clause

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import {
  Wgs84,
  MortonCode,
  PackedTileId,
  NdsBoundingBox,
  getTileIdsForBoundingBox,
  boundingBoxFromTileIds,
  Vec2,
  Polygon,
  PolygonType,
  Wgs84Aabb,
  Wgs84Polygon,
} from '../src/index.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const vectorsPath = resolve(__dirname, '../../test-vectors/parity_vectors.json');

interface Vectors {
  _meta: { float_tolerance: number };
  wgs84_to_nds: Array<{
    lon: number;
    lat: number;
    normalized_lon: number;
    normalized_lat: number;
    nds_x: number;
    nds_y: number;
  }>;
  nds_to_wgs84: Array<{ x: number; y: number; lon: number; lat: number }>;
  morton: Array<{
    x: number;
    y: number;
    morton: string;
    decoded_x: number;
    decoded_y: number;
  }>;
  packed_tile_from_index: Array<{
    morton_number: number;
    level: number;
    value: number;
    computed_level: number;
    computed_morton_number: number;
    size: number;
    sw: [number, number];
    ne: [number, number];
    center: [number, number];
  }>;
  tile_neighbours: Array<{
    morton_number: number;
    level: number;
    west: number;
    east: number;
    south: number;
    north: number;
  }>;
  from_morton_and_level: Array<{
    x: number;
    y: number;
    level: number;
    value: number;
    computed_level: number;
    computed_morton_number: number;
  }>;
  tiles_for_bbox: Array<{
    sw_x: number;
    sw_y: number;
    ne_x: number;
    ne_y: number;
    level: number;
    tile_values: number[];
  }>;
  bbox_from_tiles: Array<{
    tile_values: number[];
    result: [number, number, number, number];
  }>;
  nds_bbox_ops: Array<{
    a: [number, number, number, number];
    b: [number, number, number, number];
    intersects: boolean;
    a_contains_b: boolean;
  }>;
  nds_bbox_from_wgs84: Array<{
    sw: [number, number];
    ne: [number, number];
    min_x: number;
    min_y: number;
    max_x: number;
    max_y: number;
  }>;
  distance_bearing: Array<{
    a: [number, number];
    b: [number, number];
    distance_m: number;
    bearing_rad: number;
  }>;
  nds_distance_to_meters: Array<{
    nds_x: number;
    nds_y: number;
    at_latitude: number;
    width_m: number;
    height_m: number;
  }>;
  wgs84_aabb: Array<{
    name: string;
    sw_lon: number;
    sw_lat: number;
    size_x: number;
    size_y: number;
    valid: boolean;
    stored_size: [number, number];
    sw: [number, number];
    se: [number, number];
    ne: [number, number];
    nw: [number, number];
    center: [number, number];
    vertices: Array<[number, number]>;
    contains_anti_meridian: boolean;
    split_over_anti_meridian: {
      left_sw: [number, number];
      left_size: [number, number];
      right_sw: [number, number];
      right_size: [number, number];
    } | null;
    num_tile_ids: number[];
    tile_level_min8: number;
    tile_level_min2: number;
  }>;
  wgs84_aabb_contains: Array<{
    box: string;
    point: string;
    point_lon: number;
    point_lat: number;
    contains: boolean;
  }>;
  wgs84_aabb_intersects: Array<{
    a: string;
    b: string;
    intersects: boolean;
  }>;
  polygon_orientation: Array<{
    name: string;
    polygon_type: number;
    vertices: Array<[number, number]>;
    orientation: number;
    is_valid: boolean;
  }>;
  wgs84_polygon: Array<{
    name: string;
    vertices: Array<[number, number]>;
    is_valid: boolean;
    aabb_sw: [number, number];
    aabb_size: [number, number];
    median_lon: number;
    median_lat: number;
  }>;
  wgs84_polygon_collision: Array<{
    a: string;
    a_vertices: Array<[number, number]>;
    b: string;
    b_vertices: Array<[number, number]>;
    a_collides_b: boolean;
    b_collides_a: boolean;
  }>;
}

const vectors: Vectors = JSON.parse(readFileSync(vectorsPath, 'utf-8'));
const TOL = vectors._meta.float_tolerance;

function approx(actual: number, expected: number): void {
  expect(Math.abs(actual - expected)).toBeLessThanOrEqual(TOL);
}

describe('wgs84_to_nds', () => {
  it.each(vectors.wgs84_to_nds)('lon=$lon lat=$lat', (v) => {
    const p = new Wgs84(v.lon, v.lat);
    approx(p.x, v.normalized_lon);
    approx(p.y, v.normalized_lat);
    const [x, y] = p.toNdsCoordinates();
    expect(x).toBe(v.nds_x);
    expect(y).toBe(v.nds_y);
  });
});

describe('nds_to_wgs84', () => {
  it.each(vectors.nds_to_wgs84)('x=$x y=$y', (v) => {
    const p = Wgs84.fromNdsCoordinates(v.x, v.y);
    approx(p.x, v.lon);
    approx(p.y, v.lat);
  });
});

describe('morton', () => {
  it.each(vectors.morton)('x=$x y=$y', (v) => {
    const m = MortonCode.fromNdsCoordinates(v.x, v.y);
    expect(m.value()).toBe(BigInt(v.morton));
    const [dx, dy] = m.toNdsCoordinates();
    expect(dx).toBe(v.decoded_x);
    expect(dy).toBe(v.decoded_y);
  });

  it('round-trips through the raw constructor', () => {
    for (const v of vectors.morton) {
      const m = new MortonCode(BigInt(v.morton));
      const [dx, dy] = m.toNdsCoordinates();
      expect(dx).toBe(v.decoded_x);
      expect(dy).toBe(v.decoded_y);
    }
  });
});

describe('packed_tile_from_index', () => {
  it.each(vectors.packed_tile_from_index)('morton=$morton_number level=$level', (v) => {
    const tile = PackedTileId.fromTileIndex(v.morton_number, v.level);
    expect(tile.value).toBe(v.value);
    expect(tile.level()).toBe(v.computed_level);
    expect(tile.mortonNumber()).toBe(v.computed_morton_number);
    expect(tile.x()).toBe(v.grid_x);
    expect(tile.y()).toBe(v.grid_y);
    expect(tile.size()).toBe(v.size);
    expect(tile.southWestCorner()).toEqual(v.sw);
    expect(tile.northEastCorner()).toEqual(v.ne);
    expect(tile.center()).toEqual(v.center);

    // Constructing from the signed value reproduces the same tile.
    const fromValue = PackedTileId.fromValue(v.value);
    expect(fromValue.value).toBe(v.value);
    expect(fromValue.level()).toBe(v.computed_level);
    expect(fromValue.mortonNumber()).toBe(v.computed_morton_number);
    expect(PackedTileId.fromTileXY(v.grid_x, v.grid_y, v.level).value).toBe(v.value);
  });
});

describe('tile_neighbours', () => {
  it.each(vectors.tile_neighbours)('morton=$morton_number level=$level', (v) => {
    const tile = PackedTileId.fromTileIndex(v.morton_number, v.level);
    expect(tile.westNeighbour().value).toBe(v.west);
    expect(tile.eastNeighbour().value).toBe(v.east);
    expect(tile.southNeighbour().value).toBe(v.south);
    expect(tile.northNeighbour().value).toBe(v.north);
  });
});

describe('from_morton_and_level', () => {
  it.each(vectors.from_morton_and_level)('x=$x y=$y level=$level', (v) => {
    const m = MortonCode.fromNdsCoordinates(v.x, v.y);
    const tile = PackedTileId.fromMortonAndLevel(m, v.level);
    expect(tile.value).toBe(v.value);
    expect(tile.level()).toBe(v.computed_level);
    expect(tile.mortonNumber()).toBe(v.computed_morton_number);
    expect(PackedTileId.fromNdsCoordinates(v.x, v.y, v.level).value).toBe(v.value);
  });
});

describe('packed_tile_from_wgs84', () => {
  it.each(vectors.packed_tile_from_wgs84)('lon=$lon lat=$lat level=$level', (v) => {
    const tile = PackedTileId.fromWgs84(v.lon, v.lat, v.level);
    expect(tile.value).toBe(v.value);
    expect(tile.mortonNumber()).toBe(v.computed_morton_number);
    expect(tile.x()).toBe(v.grid_x);
    expect(tile.y()).toBe(v.grid_y);
  });
});

describe('tiles_for_bbox', () => {
  it.each(vectors.tiles_for_bbox)('level=$level', (v) => {
    const tiles = getTileIdsForBoundingBox(v.sw_x, v.sw_y, v.ne_x, v.ne_y, v.level);
    expect(tiles.map((t) => t.value)).toEqual(v.tile_values);
  });
});

describe('bbox_from_tiles', () => {
  it.each(vectors.bbox_from_tiles)('tiles=$tile_values', (v) => {
    const bbox = boundingBoxFromTileIds(v.tile_values);
    expect(bbox).toEqual(v.result);
  });
});

describe('nds_bbox_ops', () => {
  it.each(vectors.nds_bbox_ops)('intersects/contains', (v) => {
    const a = new NdsBoundingBox(v.a[0], v.a[1], v.a[2], v.a[3]);
    const b = new NdsBoundingBox(v.b[0], v.b[1], v.b[2], v.b[3]);
    expect(a.intersects(b)).toBe(v.intersects);
    expect(a.contains(b)).toBe(v.a_contains_b);
  });
});

describe('nds_bbox_from_wgs84', () => {
  it.each(vectors.nds_bbox_from_wgs84)('corners', (v) => {
    const bbox = NdsBoundingBox.fromWgs84Corners(
      new Wgs84(v.sw[0], v.sw[1]),
      new Wgs84(v.ne[0], v.ne[1]),
    );
    expect(bbox.minX).toBe(v.min_x);
    expect(bbox.minY).toBe(v.min_y);
    expect(bbox.maxX).toBe(v.max_x);
    expect(bbox.maxY).toBe(v.max_y);
  });
});

describe('distance_bearing', () => {
  it.each(vectors.distance_bearing)('haversine + bearing', (v) => {
    const a = new Wgs84(v.a[0], v.a[1]);
    const b = new Wgs84(v.b[0], v.b[1]);
    approx(a.distanceTo(b), v.distance_m);
    approx(a.bearingFrom(b), v.bearing_rad);
  });
});

describe('nds_distance_to_meters', () => {
  it.each(vectors.nds_distance_to_meters)('at lat=$at_latitude', (v) => {
    const [w, h] = Wgs84.ndsDistanceToMeters(v.nds_x, v.nds_y, v.at_latitude);
    approx(w, v.width_m);
    approx(h, v.height_m);
  });
});

/** Reconstruct an AABB from its raw sw/size definition in the vectors. */
function makeAabb(swLon: number, swLat: number, sizeX: number, sizeY: number): Wgs84Aabb {
  return new Wgs84Aabb(new Wgs84(swLon, swLat), new Vec2(sizeX, sizeY));
}

/** Map from a named AABB case to its raw `(sw, size)` definition. */
const aabbByName = new Map<string, { swLon: number; swLat: number; sizeX: number; sizeY: number }>(
  vectors.wgs84_aabb.map((v) => [
    v.name,
    { swLon: v.sw_lon, swLat: v.sw_lat, sizeX: v.size_x, sizeY: v.size_y },
  ]),
);

function aabbForName(name: string): Wgs84Aabb {
  const def = aabbByName.get(name);
  if (def === undefined) {
    throw new Error(`Unknown AABB case: ${name}`);
  }
  return makeAabb(def.swLon, def.swLat, def.sizeX, def.sizeY);
}

function approxPair(actual: Wgs84, expected: [number, number]): void {
  approx(actual.longitude(), expected[0]);
  approx(actual.latitude(), expected[1]);
}

describe('wgs84_aabb', () => {
  it.each(vectors.wgs84_aabb)('$name', (v) => {
    const box = makeAabb(v.sw_lon, v.sw_lat, v.size_x, v.size_y);

    expect(box.valid()).toBe(v.valid);
    approx(box.size().x, v.stored_size[0]);
    approx(box.size().y, v.stored_size[1]);

    approxPair(box.sw(), v.sw);
    approxPair(box.se(), v.se);
    approxPair(box.ne(), v.ne);
    approxPair(box.nw(), v.nw);
    approxPair(box.center(), v.center);

    const verts = box.vertices();
    expect(verts.length).toBe(v.vertices.length);
    for (let i = 0; i < verts.length; i++) {
      approxPair(verts[i], v.vertices[i]);
    }

    expect(box.containsAntiMeridian()).toBe(v.contains_anti_meridian);

    const split = box.splitOverAntiMeridian();
    if (v.split_over_anti_meridian === null) {
      expect(split).toBeNull();
    } else {
      expect(split).not.toBeNull();
      const [left, right] = split!;
      approxPair(left.sw(), v.split_over_anti_meridian.left_sw);
      approx(left.size().x, v.split_over_anti_meridian.left_size[0]);
      approx(left.size().y, v.split_over_anti_meridian.left_size[1]);
      approxPair(right.sw(), v.split_over_anti_meridian.right_sw);
      approx(right.size().x, v.split_over_anti_meridian.right_size[0]);
      approx(right.size().y, v.split_over_anti_meridian.right_size[1]);
    }

    for (let lv = 0; lv < v.num_tile_ids.length; lv++) {
      expect(box.numTileIds(lv)).toBe(v.num_tile_ids[lv]);
    }
    expect(box.tileLevel(8)).toBe(v.tile_level_min8);
    expect(box.tileLevel(2)).toBe(v.tile_level_min2);
  });
});

describe('wgs84_aabb_contains', () => {
  it.each(vectors.wgs84_aabb_contains)('$box contains $point', (v) => {
    const box = aabbForName(v.box);
    expect(box.contains(new Wgs84(v.point_lon, v.point_lat))).toBe(v.contains);
  });
});

describe('wgs84_aabb_intersects', () => {
  it.each(vectors.wgs84_aabb_intersects)('$a vs $b', (v) => {
    const a = aabbForName(v.a);
    const b = aabbForName(v.b);
    expect(a.intersects(b)).toBe(v.intersects);
  });
});

describe('polygon_orientation', () => {
  it.each(vectors.polygon_orientation)('$name', (v) => {
    const poly = new Polygon(
      v.polygon_type as PolygonType,
      v.vertices.map(([lon, lat]) => new Wgs84(lon, lat)),
    );
    expect(poly.orientation()).toBe(v.orientation);
    expect(poly.isValid()).toBe(v.is_valid);
  });
});

describe('wgs84_polygon', () => {
  it.each(vectors.wgs84_polygon)('$name', (v) => {
    const poly = new Wgs84Polygon(
      undefined,
      v.vertices.map(([lon, lat]) => new Wgs84(lon, lat)),
    );
    expect(poly.isValid()).toBe(v.is_valid);

    const bb = poly.aaBb();
    approxPair(bb.sw(), v.aabb_sw);
    approx(bb.size().x, v.aabb_size[0]);
    approx(bb.size().y, v.aabb_size[1]);

    const med = poly.median();
    approx(med.longitude(), v.median_lon);
    approx(med.latitude(), v.median_lat);
  });
});

describe('wgs84_polygon_collision', () => {
  it.each(vectors.wgs84_polygon_collision)('$a vs $b', (v) => {
    const a = new Wgs84Polygon(
      undefined,
      v.a_vertices.map(([lon, lat]) => new Wgs84(lon, lat)),
    );
    const b = new Wgs84Polygon(
      undefined,
      v.b_vertices.map(([lon, lat]) => new Wgs84(lon, lat)),
    );
    expect(a.collidesWith(b)).toBe(v.a_collides_b);
    expect(b.collidesWith(a)).toBe(v.b_collides_a);
  });
});
