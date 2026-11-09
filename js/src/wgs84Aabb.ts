// SPDX-License-Identifier: BSD-3-Clause

import { MortonCode } from './morton.js';
import { PackedTileId } from './tileid.js';
import { Vec2 } from './vec2.js';
import { Wgs84 } from './wgs84.js';

/**
 * WGS84 axis-aligned bounding box.
 *
 * Port of the C++ `Wgs84AABB<T>` (`cpp/include/ndsmath/wgs84aabb.h`),
 * specialized to `double`. The box is stored as a south-west corner
 * ({@link Wgs84}) plus a raw {@link Vec2} size (a `(dx, dy)` extent that is
 * *not* normalized).
 *
 * The geometry layer deliberately uses the power-of-two NDS deltas
 * (`Wgs84.LON_NDS_DELTA_POW2` etc.) and world-edge constants used by the
 * C++ geometry APIs. Constructor normalization still follows this port's Wgs84.
 */
export class Wgs84Aabb {
  private readonly _sw: Wgs84;
  private readonly _size: Vec2;

  /**
   * Construct an AABB from a south-west corner and a size.
   *
   * After storing, if the box is {@link Wgs84Aabb.valid}, the height is clamped
   * so the top never exceeds +90 degrees (`excessHeight` correction). An
   * invalid box stores `size` unmodified. Both arguments are retained by reference;
   * the height clamp mutates the supplied size, and later caller edits affect the box.
   *
   * @param sw South-west corner. Defaults to `Wgs84(0, 0)`.
   * @param size Raw `(dx, dy)` extent. Defaults to `Vec2(0, 0)`.
   */
  constructor(sw?: Wgs84, size?: Vec2) {
    this._sw = sw ?? new Wgs84(0.0, 0.0);
    this._size = size ?? new Vec2(0.0, 0.0);

    if (!this.valid()) {
      return;
    }

    const excessHeight = 90.0 - this._sw.latitude() - this._size.y;
    if (excessHeight < 0) {
      this._size.y += excessHeight;
    }
  }

  /**
   * Build an AABB from normalized tile corners via {@link Wgs84.fromMortonCode}.
   * The coordinate scale is the same on both axes: `360 / 2^32 = 180 / 2^31`.
   * Raw corner differences determine size, so wrapped world-edge corners do
   * not preserve an unwrapped tile extent.
   *
   * @param tileId The tile whose extent the AABB should cover.
   */
  static fromTile(tileId: PackedTileId): Wgs84Aabb {
    const [swX, swY] = tileId.southWestCorner();
    const [neX, neY] = tileId.northEastCorner();

    const swCorner = Wgs84.fromMortonCode(MortonCode.fromNdsCoordinates(swX, swY));
    const neCorner = Wgs84.fromMortonCode(MortonCode.fromNdsCoordinates(neX, neY));

    const size = new Vec2(swCorner.x - neCorner.x, swCorner.y - neCorner.y).abs();
    return new Wgs84Aabb(swCorner, size);
  }

  /**
   * Construct an AABB from a center, a soft tile-count limit, and a level.
   *
   * @param center The center coordinate of the box.
   * The target area is softLimit tile footprints, not a cap on enumerated tiles.
   * Pole clamping can move the final center.
   *
   * @param softLimit Nonnegative target area in tile footprints.
   * @param level NDS tile level (0..15).
   */
  static fromCenterAndTileLimit(center: Wgs84, softLimit: number, level: number): Wgs84Aabb {
    const targetAspectRatio = 0.7; // height/width is this factor squared
    const tileWidth = 180.0 / 2 ** level;
    const targetSize = Math.sqrt(softLimit) * tileWidth;
    const targetSizeVec = new Vec2(targetSize / targetAspectRatio, targetSize * targetAspectRatio);
    const half = targetSizeVec.mul(0.5);
    const newSw = new Wgs84(center.x - half.x, center.y - half.y);
    return new Wgs84Aabb(newSw, targetSizeVec);
  }

  /**
   * Whether the box size is within reasonable bounds.
   *
   * `0 <= size.x <= 360` and `0 <= size.y <= 180`.
   */
  valid(): boolean {
    return this._size.x >= 0 && this._size.y >= 0 && this._size.x <= 360.0 && this._size.y <= 180.0;
  }

  /** Borrow the stored mutable south-west corner. */
  sw(): Wgs84 {
    return this._sw;
  }

  /** The north-east corner (`sw + size`, re-normalized). */
  ne(): Wgs84 {
    return new Wgs84(this._sw.x + this._size.x, this._sw.y + this._size.y);
  }

  /** The north-west corner. */
  nw(): Wgs84 {
    return new Wgs84(this._sw.x, this._sw.y + this._size.y);
  }

  /** The south-east corner. */
  se(): Wgs84 {
    return new Wgs84(this._sw.x + this._size.x, this._sw.y);
  }

  /** All four corners, CCW from SW: `[sw, se, ne, nw]`. */
  vertices(): Wgs84[] {
    return [this.sw(), this.se(), this.ne(), this.nw()];
  }

  /** Borrow the stored mutable raw `(dx, dy)` extent. */
  size(): Vec2 {
    return this._size;
  }

  /** Whether the horizontal extent crosses the anti-meridian (+/-180). */
  containsAntiMeridian(): boolean {
    return this._sw.longitude() + this._size.x > Wgs84.LON_MAX + Wgs84.LON_NDS_DELTA_POW2;
  }

  /** The center coordinate (`sw + size * 0.5`, re-normalized). */
  center(): Wgs84 {
    const half = this._size.mul(0.5);
    return new Wgs84(this._sw.x + half.x, this._sw.y + half.y);
  }

  /**
   * Split a box crossing the anti-meridian into a left and right half.
   *
   * Only meaningful when {@link Wgs84Aabb.containsAntiMeridian} is true.
   *
   * @returns A `[left, right]` tuple of normalized boxes, or `null` if the box
   *   does not actually extend past `LON_MAX`.
   */
  splitOverAntiMeridian(): [Wgs84Aabb, Wgs84Aabb] | null {
    const widthAfterAm = this._sw.longitude() + this._size.x - Wgs84.LON_MAX;
    if (widthAfterAm > 0) {
      const widthBeforeAm = this._size.x - widthAfterAm;
      const left = new Wgs84Aabb(this._sw, new Vec2(widthBeforeAm, this._size.y));
      const right = new Wgs84Aabb(
        new Wgs84(Wgs84.LON_MIN, this._sw.latitude()),
        new Vec2(widthAfterAm, this._size.y),
      );
      return [left, right];
    }
    return null;
  }

  /**
   * Average the projection's vertical stretch over a nonzero latitude span.
   * Callers must avoid singular projection latitudes.
   */
  avgMercatorStretch(): number {
    const latTop = toRadians(this._sw.latitude() + this._size.y);
    const latBottom = toRadians(this._sw.latitude());

    const radToMercatorLat = (wgs84Lat: number): number =>
      Math.atanh(Math.sin(wgs84Lat - Math.PI / 2.0));

    return (radToMercatorLat(latTop) - radToMercatorLat(latBottom)) / toRadians(this._size.y);
  }

  /**
   * Approximate number of tiles at level `lv` contained in this box.
   *
   * Mirrors the C++ `numTileIds`: `tileWidth = 180 / float(2^lv)` and a
   * component-wise `ceil` of `size / tileWidth`. For an invalid (negative-size)
   * box the product can be negative. This method retains the signed product;
   * the C++ implementation clamps nonpositive counts to zero.
   */
  numTileIds(lv: number): number {
    const tileWidth = 180.0 / 2 ** lv;
    const tilesPerDimX = Math.ceil(this._size.x / tileWidth);
    const tilesPerDimY = Math.ceil(this._size.y / tileWidth);
    // `+ 0` collapses an IEEE `-0` (from `Math.ceil` of a small negative, as in
    // the invalid negative-size box) to `+0`, matching the integer result the
    // Python/C++ reference produces.
    return tilesPerDimX * tilesPerDimY + 0;
  }

  /**
   * First level (0..15) whose tile count is at least `minNumTiles`.
   *
   * Returns 15 if no level in `0..15` reaches the threshold.
   *
   * @param minNumTiles Minimum tile count threshold (default 8).
   */
  tileLevel(minNumTiles = 8): number {
    for (let resultTileLevel = 0; resultTileLevel <= 15; resultTileLevel++) {
      if (this.numTileIds(resultTileLevel) >= minNumTiles) {
        return resultTileLevel;
      }
    }
    return 15;
  }

  /** Test inclusive raw coordinate intervals; split anti-meridian boxes first. */
  contains(point: Wgs84): boolean {
    return (
      point.longitude() >= this._sw.longitude() &&
      point.longitude() <= this._sw.longitude() + this._size.x &&
      point.latitude() >= this._sw.latitude() &&
      point.latitude() <= this._sw.latitude() + this._size.y
    );
  }

  /**
   * Axis-aligned interval-overlap test against another box.
   *
   * Edge contact counts as intersection. Longitude is not unwrapped here;
   * split anti-meridian boxes before comparing them.
   */
  intersects(other: Wgs84Aabb): boolean {
    const aMaxX = this._sw.longitude() + this._size.x;
    const aMaxY = this._sw.latitude() + this._size.y;
    const bMaxX = other.sw().longitude() + other.size().x;
    const bMaxY = other.sw().latitude() + other.size().y;
    return (
      this._sw.longitude() <= bMaxX &&
      aMaxX >= other.sw().longitude() &&
      this._sw.latitude() <= bMaxY &&
      aMaxY >= other.sw().latitude()
    );
  }
}

function toRadians(deg: number): number {
  return (deg * Math.PI) / 180;
}
