// SPDX-License-Identifier: MIT
package io.github.ndsev.ndslivemath;

import java.util.ArrayList;
import java.util.List;

/**
 * Free-function utilities for working with collections of {@link PackedTileId}s.
 *
 * <p>Ports the module-level functions {@code get_tile_ids_for_bounding_box} and
 * {@code bounding_box_from_tile_ids} from
 * {@code python/src/ndslive/math/tileid.py}.</p>
 */
public final class TileIds {

    private TileIds() {
    }

    /**
     * Get all tile IDs that intersect with a bounding box defined by NDS
     * coordinates.
     *
     * <p>Uses floor division ({@link Math#floorDiv}) to compute tile indices so
     * that negative coordinates are handled correctly (toward negative
     * infinity), matching Python's {@code //}.</p>
     *
     * @param swX south-west corner X (longitude) in NDS coordinates
     * @param swY south-west corner Y (latitude) in NDS coordinates
     * @param neX north-east corner X (longitude) in NDS coordinates
     * @param neY north-east corner Y (latitude) in NDS coordinates
     * @param level tile level (0-15)
     * @return the list of PackedTileIds that intersect the bounding box
     */
    public static List<PackedTileId> getTileIdsForBoundingBox(
            long swX, long swY, long neX, long neY, int level) {
        List<PackedTileId> tileIds = new ArrayList<>();

        long tileSize = 1L << (31 - level);

        long startTileX = Math.floorDiv(swX, tileSize);
        long startTileY = Math.floorDiv(swY, tileSize);
        long endTileX = Math.floorDiv(neX, tileSize);
        long endTileY = Math.floorDiv(neY, tileSize);

        for (long tileY = startTileY; tileY <= endTileY; tileY++) {
            for (long tileX = startTileX; tileX <= endTileX; tileX++) {
                long tileSwX = tileX * tileSize;
                long tileSwY = tileY * tileSize;

                MortonCode morton = MortonCode.fromNdsCoordinates(tileSwX, tileSwY);
                tileIds.add(PackedTileId.fromMortonAndLevel(morton, level));
            }
        }

        return tileIds;
    }

    /**
     * Create a tight bounding box from a list of tiles.
     *
     * <p>The north-east corner of a tile is exclusive, so the returned max
     * values have 1 subtracted to be the last point inside the coverage,
     * matching {@code bounding_box_from_tile_ids} in the reference.</p>
     *
     * @param tiles a non-empty list of PackedTileIds
     * @return a {@code long[]} of {@code {sw_x, sw_y, ne_x, ne_y}} in NDS coords
     * @throws IllegalArgumentException if {@code tiles} is empty
     */
    public static long[] boundingBoxFromTileIds(List<PackedTileId> tiles) {
        if (tiles == null || tiles.isEmpty()) {
            throw new IllegalArgumentException("tile_ids list cannot be empty");
        }

        long[] firstSw = tiles.get(0).southWestCorner();
        long[] firstNe = tiles.get(0).northEastCorner();

        long minX = firstSw[0];
        long minY = firstSw[1];
        long maxX = firstNe[0];
        long maxY = firstNe[1];

        for (int i = 1; i < tiles.size(); i++) {
            long[] sw = tiles.get(i).southWestCorner();
            long[] ne = tiles.get(i).northEastCorner();
            minX = Math.min(minX, sw[0]);
            minY = Math.min(minY, sw[1]);
            maxX = Math.max(maxX, ne[0]);
            maxY = Math.max(maxY, ne[1]);
        }

        return new long[] {minX, minY, maxX - 1, maxY - 1};
    }
}
