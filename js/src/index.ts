// SPDX-License-Identifier: MIT

/**
 * `@ndsev/ndslive-math` — coordinate math, tile IDs, and Morton codes for
 * NDS.Live.
 *
 * A small set of geometry primitives: WGS84 ↔ NDS coordinate conversion,
 * packed tile IDs, Morton (Z-order) encoding, and bounding boxes in NDS space.
 *
 * @example WGS84 ↔ NDS coordinates
 * ```ts
 * import { Wgs84 } from "@ndsev/ndslive-math";
 *
 * const point = new Wgs84(11.585, 48.137); // Munich
 * const [ndsX, ndsY] = point.toNdsCoordinates();
 * const back = Wgs84.fromNdsCoordinates(ndsX, ndsY);
 * ```
 *
 * @example Packed tile IDs and neighbour traversal
 * ```ts
 * import { PackedTileId, MortonCode } from "@ndsev/ndslive-math";
 *
 * const morton = MortonCode.fromNdsCoordinates(ndsX, ndsY);
 * const tile = PackedTileId.fromMortonAndLevel(morton, 13);
 * const sw = tile.southWestCorner();
 * const east = tile.eastNeighbour();
 * ```
 */

export { Wgs84 } from './wgs84.js';
export { MortonCode } from './morton.js';
export { PackedTileId, getTileIdsForBoundingBox, boundingBoxFromTileIds } from './tileid.js';
export { NdsBoundingBox } from './boundingBox.js';
