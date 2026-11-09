// SPDX-License-Identifier: BSD-3-Clause

import { PackedTileId } from './tileid.js';
import { Wgs84 } from './wgs84.js';

/**
 * Axis-aligned bounding box in NDS coordinates (32-bit integers).
 *
 * NDS coordinates use integers for fast comparisons:
 * - X (longitude): 32-bit signed integer
 * - Y (latitude): 31-bit signed integer
 *
 * Faithful port of the Python reference
 * (`python/src/ndslive/math/bounding_box.py`).
 */
export class NdsBoundingBox {
  /** SW corner longitude (NDS coords). */
  minX: number;

  /** SW corner latitude (NDS coords). */
  minY: number;

  /** NE corner longitude (NDS coords). */
  maxX: number;

  /** NE corner latitude (NDS coords). */
  maxY: number;

  constructor(minX: number, minY: number, maxX: number, maxY: number) {
    this.minX = minX;
    this.minY = minY;
    this.maxX = maxX;
    this.maxY = maxY;
  }

  /**
   * Check if this bbox intersects (overlaps) with another.
   *
   * Closed intervals include contact at an edge or point. Bounds must be
   * ordered in each coordinate; longitude wrapping is not handled here.
   */
  intersects(other: NdsBoundingBox): boolean {
    return !(
      this.maxX < other.minX ||
      this.minX > other.maxX ||
      this.maxY < other.minY ||
      this.minY > other.maxY
    );
  }

  /** Check if this bbox fully contains another. */
  contains(other: NdsBoundingBox): boolean {
    return (
      this.minX <= other.minX &&
      this.maxX >= other.maxX &&
      this.minY <= other.minY &&
      this.maxY >= other.maxY
    );
  }

  /**
   * Copy the tile's SW and exclusive NE coordinates without subtracting one.
   * Use boundingBoxFromTileIds for inclusive interior bounds that enumerate
   * exactly one tile at the same level.
   *
   * @param tile PackedTileId object or integer tile ID.
   */
  static fromTile(tile: PackedTileId | number): NdsBoundingBox {
    const t = typeof tile === 'number' ? new PackedTileId(tile) : tile;
    const [swX, swY] = t.southWestCorner();
    const [neX, neY] = t.northEastCorner();
    return new NdsBoundingBox(swX, swY, neX, neY);
  }

  /**
   * Create a bounding box from WGS84 corner coordinates.
   *
   * @param sw South-west corner (min longitude, min latitude).
   * @param ne North-east corner (max longitude, max latitude).
   */
  static fromWgs84Corners(sw: Wgs84, ne: Wgs84): NdsBoundingBox {
    const [minX, minY] = sw.toNdsCoordinates();
    const [maxX, maxY] = ne.toNdsCoordinates();
    return new NdsBoundingBox(minX, minY, maxX, maxY);
  }
}
