// SPDX-License-Identifier: MIT

import { MortonCode } from "./morton.js";
import { Wgs84 } from "./wgs84.js";

const TWO_32 = 2 ** 32; // 4294967296
const TWO_31 = 2 ** 31; // 2147483648

/**
 * Represents a tile in a hierarchical tiling system following the NDS.Live
 * standard.
 *
 * Per the NDS.Live standard, tile IDs are signed 32-bit integers. For levels
 * 0-14 values are positive; for level 15 values are negative
 * (`-2147483648` to `-1`) because the level bit (bit 31) is the sign bit in a
 * signed int32.
 *
 * Internally values are stored as unsigned 32-bit integers for clean bit
 * operations; conversion between signed and unsigned happens only at the API
 * boundary. The {@link PackedTileId.value} getter returns the signed int32.
 *
 * Faithful port of the Python reference (`python/src/ndslive/math/tileid.py`).
 */
export class PackedTileId {
  /** Internal unsigned 32-bit representation. */
  private readonly _value: number;

  /**
   * Construct a PackedTileId from a tile ID value.
   *
   * Accepts both signed and unsigned 32-bit integer representations. Per the
   * NDS.Live standard, level 15 tiles have negative values
   * (`-2147483648` to `-1`), while levels 0-14 have positive values.
   *
   * @param value Tile ID as signed int32 (negative for level 15) or unsigned int32.
   * @throws {Error} If the resulting tile ID is invalid.
   */
  constructor(value = 0) {
    let v: number;
    if (value < 0) {
      // Convert signed int32 to unsigned (e.g. -2147483648 -> 2147483648).
      v = value + TWO_32;
    } else if (value >= TWO_32) {
      // Mask values outside the 32-bit range down to 32 bits.
      v = value >>> 0;
    } else {
      v = value;
    }
    this._value = v;
    this.validate();
  }

  /**
   * Get the tile ID value as signed int32 per the NDS.Live standard.
   *
   * Level 15 tiles return negative values (`-2147483648` to `-1`); levels 0-14
   * return positive values.
   */
  get value(): number {
    if (this._value >= TWO_31) {
      // Bit 31 set => negative in signed int32.
      return this._value - TWO_32;
    }
    return this._value;
  }

  /**
   * Create a PackedTileId directly from a tile morton number and level.
   *
   * Constructs a tile using `mortonNumber` as the tile's index at the
   * specified level, without any coordinate conversion.
   *
   * @param mortonNumber The tile's morton number (`0` to `2^(2*level+1) - 1`).
   * @param level Tile level (0-15).
   * @throws {RangeError} If level or mortonNumber are out of valid range.
   */
  static fromTileIndex(mortonNumber: number, level: number): PackedTileId {
    if (!(level >= 0 && level <= 15)) {
      throw new RangeError(`Invalid level ${level} (must be 0-15)`);
    }

    const maxMorton = 2 ** (2 * level + 1) - 1;
    if (!(mortonNumber >= 0 && mortonNumber <= maxMorton)) {
      throw new RangeError(
        `Invalid morton number ${mortonNumber} for level ${level} ` +
          `(allowed: 0-${maxMorton})`,
      );
    }

    const value = mortonNumber + 2 ** (16 + level);
    return new PackedTileId(value);
  }

  /**
   * Create a PackedTileId that contains the point encoded by a MortonCode.
   *
   * Finds the tile at the specified level that contains the full-precision NDS
   * coordinates encoded in the MortonCode. The resulting `mortonNumber()` will
   * NOT equal the input `mortonCode.value()` unless the point happens to fall
   * in that specific tile. Use {@link PackedTileId.fromTileIndex} to build a
   * tile with a specific morton number.
   *
   * @param mortonCode A MortonCode representing full-precision NDS coordinates.
   * @param level Tile level (0-15).
   * @throws {RangeError} If level is out of valid range.
   */
  static fromMortonAndLevel(mortonCode: MortonCode, level: number): PackedTileId {
    if (!(level >= 0 && level <= 15)) {
      throw new RangeError(`Invalid level ${level} (must be 0-15)`);
    }

    let [xCoord, yCoord] = mortonCode.toNdsCoordinates();

    if (xCoord < 0) xCoord += TWO_32;
    if (yCoord < 0) yCoord += TWO_31;

    // Use BigInt for the >> since xCoord can be up to 2^32 (exceeds int32).
    const nLevel = BigInt(31 - level);
    const nX = Number(BigInt(xCoord) >> nLevel);
    const nY = Number(BigInt(yCoord) >> nLevel);

    const temp = MortonCode.fromNdsCoordinates(nX, nY);

    // temp.value() <= 2^(2*level+1) here, which fits in a JS number for level <= 15.
    const value = Number(temp.value()) + 2 ** (16 + level);

    return new PackedTileId(value);
  }

  /** Level of the tile (0..15). */
  level(): number {
    let level = 0;
    let tileId = Math.floor(this._value / 65536); // value >> 16
    while (tileId > 1) {
      tileId = Math.floor(tileId / 2); // tileId >> 1
      level += 1;
    }
    return level;
  }

  /** Size of the tile in NDS coordinate units. */
  size(): number {
    return 2 ** (31 - this.level());
  }

  /**
   * Get tile dimensions in meters at the tile's center latitude.
   *
   * @returns Tuple of `[widthMeters, heightMeters]`. Dimensions vary by
   *   latitude — tiles are largest at the equator and shrink toward the poles.
   */
  dimensionsInMeters(): [number, number] {
    const [centerX, centerY] = this.center();
    const centerWgs = Wgs84.fromNdsCoordinates(centerX, centerY);
    const tileSize = this.size();
    return Wgs84.ndsDistanceToMeters(tileSize, tileSize, centerWgs.y);
  }

  /** Returns the center of the tile in NDS coordinates. */
  center(): [number, number] {
    const [x, y] = this.southWestCorner();
    const halfSize = Math.floor(this.size() / 2);
    return [x + halfSize, y + halfSize];
  }

  /** Returns the south-west corner of the tile in NDS coordinates. */
  southWestCorner(): [number, number] {
    const mortonNumber = this.mortonNumber();
    const shift = BigInt(63 - (2 * this.level() + 1));
    return new MortonCode(BigInt(mortonNumber) << shift).toNdsCoordinates();
  }

  /**
   * Returns the north-east corner of the tile in NDS coordinates.
   *
   * Note: the NE corner is EXCLUSIVE (first point outside the tile).
   */
  northEastCorner(): [number, number] {
    const [x, y] = this.southWestCorner();
    const size = this.size();
    return [x + size, y + size];
  }

  /**
   * Returns the Morton number of the tile, derived by subtracting the
   * level-specific offset from the packed tile ID value.
   */
  mortonNumber(): number {
    const tileLevel = this.level();
    return this._value - 2 ** (16 + tileLevel);
  }

  private validate(): void {
    const minPackedTileId = 1 << 16;
    if (this._value < minPackedTileId) {
      throw new Error(
        `Invalid PackedTileId(${this.value}): value must be >= ${minPackedTileId} ` +
          `or negative for level 15`,
      );
    }

    const tileLevel = this.level();
    const morton = this.mortonNumber();
    const maxMorton = 2 ** (2 * tileLevel + 1) - 1;

    if (morton < 0 || morton > maxMorton) {
      throw new Error(
        `Invalid PackedTileId(${this.value}): morton number ${morton} ` +
          `exceeds valid range for level ${tileLevel} (allowed: 0-${maxMorton})`,
      );
    }
  }

  /**
   * Extract X and Y coordinates from a morton number.
   *
   * In the NDS tiling system X has `(level+1)` bits and Y has `level` bits,
   * creating a rectangular grid twice as wide as it is tall.
   */
  private deinterleaveMorton(morton: number, level: number): [number, number] {
    let x = 0;
    let y = 0;
    for (let i = 0; i < level; i++) {
      if (morton & (1 << (2 * i))) {
        x |= 1 << i;
      }
      if (morton & (1 << (2 * i + 1))) {
        y |= 1 << i;
      }
    }
    if (morton & (1 << (2 * level))) {
      x |= 1 << level;
    }
    return [x, y];
  }

  /**
   * Create a morton number from X and Y coordinates.
   *
   * In the NDS tiling system X has `(level+1)` bits and Y has `level` bits.
   */
  private interleaveCoords(x: number, y: number, level: number): number {
    let morton = 0;
    for (let i = 0; i < level; i++) {
      if (x & (1 << i)) {
        morton |= 1 << (2 * i);
      }
      if (y & (1 << i)) {
        morton |= 1 << (2 * i + 1);
      }
    }
    if (x & (1 << level)) {
      morton |= 1 << (2 * level);
    }
    return morton;
  }

  /**
   * Returns the tile to the west at the same level, wrapping at the
   * antimeridian (180° longitude).
   */
  westNeighbour(): PackedTileId {
    const level = this.level();
    const morton = this.mortonNumber();
    let [x, y] = this.deinterleaveMorton(morton, level);
    const maxX = (1 << (level + 1)) - 1;
    x = (x - 1) & maxX;
    const newMorton = this.interleaveCoords(x, y, level);
    return PackedTileId.fromTileIndex(newMorton, level);
  }

  /**
   * Returns the tile to the east at the same level, wrapping at the
   * antimeridian (180° longitude).
   */
  eastNeighbour(): PackedTileId {
    const level = this.level();
    const morton = this.mortonNumber();
    let [x, y] = this.deinterleaveMorton(morton, level);
    const maxX = (1 << (level + 1)) - 1;
    x = (x + 1) & maxX;
    const newMorton = this.interleaveCoords(x, y, level);
    return PackedTileId.fromTileIndex(newMorton, level);
  }

  /**
   * Returns the tile to the south at the same level, wrapping at the
   * south pole.
   */
  southNeighbour(): PackedTileId {
    const level = this.level();
    const morton = this.mortonNumber();
    let [x, y] = this.deinterleaveMorton(morton, level);
    const maxY = (1 << level) - 1;
    y = (y - 1) & maxY;
    const newMorton = this.interleaveCoords(x, y, level);
    return PackedTileId.fromTileIndex(newMorton, level);
  }

  /**
   * Returns the tile to the north at the same level, wrapping at the
   * north pole.
   */
  northNeighbour(): PackedTileId {
    const level = this.level();
    const morton = this.mortonNumber();
    let [x, y] = this.deinterleaveMorton(morton, level);
    const maxY = (1 << level) - 1;
    y = (y + 1) & maxY;
    const newMorton = this.interleaveCoords(x, y, level);
    return PackedTileId.fromTileIndex(newMorton, level);
  }

  equals(other: PackedTileId): boolean {
    return this._value === other._value;
  }

  toString(): string {
    return `PackedTileId(value=${this.value})`;
  }
}

/** Floor division matching Python's `//` for negative operands. */
function floorDiv(a: number, b: number): number {
  return Math.floor(a / b);
}

/**
 * Get all tile IDs that intersect with a bounding box defined by NDS
 * coordinates.
 *
 * @param swX South-west corner X coordinate (longitude) in NDS coordinates.
 * @param swY South-west corner Y coordinate (latitude) in NDS coordinates.
 * @param neX North-east corner X coordinate (longitude) in NDS coordinates.
 * @param neY North-east corner Y coordinate (latitude) in NDS coordinates.
 * @param level Tile level (0-15).
 * @returns Array of PackedTileId objects that intersect with the bounding box.
 */
export function getTileIdsForBoundingBox(
  swX: number,
  swY: number,
  neX: number,
  neY: number,
  level: number,
): PackedTileId[] {
  const tileIds: PackedTileId[] = [];

  const tileSize = 2 ** (31 - level);

  const startTileX = floorDiv(swX, tileSize);
  const startTileY = floorDiv(swY, tileSize);
  const endTileX = floorDiv(neX, tileSize);
  const endTileY = floorDiv(neY, tileSize);

  for (let tileY = startTileY; tileY <= endTileY; tileY++) {
    for (let tileX = startTileX; tileX <= endTileX; tileX++) {
      const tileSwX = tileX * tileSize;
      const tileSwY = tileY * tileSize;

      const morton = MortonCode.fromNdsCoordinates(tileSwX, tileSwY);
      const tileId = PackedTileId.fromMortonAndLevel(morton, level);
      tileIds.push(tileId);
    }
  }

  return tileIds;
}

/**
 * Create a tight bounding box from a list of tile IDs.
 *
 * Computes the minimal bounding box in NDS coordinates that covers all the
 * specified tiles. When given a single tile ID, the resulting bounding box
 * returns only that tile when passed to {@link getTileIdsForBoundingBox} at the
 * same level.
 *
 * @param tileIds Array of PackedTileId objects or integer tile IDs.
 * @returns Tuple of `[swX, swY, neX, neY]` in NDS coordinates. The NE corner is
 *   inclusive (the NE corner of `northEastCorner()` minus 1).
 * @throws {Error} If `tileIds` is empty.
 */
export function boundingBoxFromTileIds(
  tileIds: ReadonlyArray<PackedTileId | number>,
): [number, number, number, number] {
  if (tileIds.length === 0) {
    throw new Error("tileIds list cannot be empty");
  }

  const tiles: PackedTileId[] = tileIds.map((tid) =>
    typeof tid === "number" ? new PackedTileId(tid) : tid,
  );

  const [firstSwX, firstSwY] = tiles[0].southWestCorner();
  const [firstNeX, firstNeY] = tiles[0].northEastCorner();

  let minX = firstSwX;
  let minY = firstSwY;
  let maxX = firstNeX;
  let maxY = firstNeY;

  for (let i = 1; i < tiles.length; i++) {
    const [swX, swY] = tiles[i].southWestCorner();
    const [neX, neY] = tiles[i].northEastCorner();

    minX = Math.min(minX, swX);
    minY = Math.min(minY, swY);
    maxX = Math.max(maxX, neX);
    maxY = Math.max(maxY, neY);
  }

  // northEastCorner() is exclusive; subtract 1 to make the NE corner inclusive.
  return [minX, minY, maxX - 1, maxY - 1];
}
