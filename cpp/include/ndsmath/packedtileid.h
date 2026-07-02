// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include "mortoncode.h"
#include "wgs84.h"
#include <cstdint>
#include <utility>
#include <vector>

namespace ndsmath
{

//! A class representing a tile in a hierarchical tiling system.
//! Provides methods to extract level, size, and coordinate
//! information from the packed tile ID.
class PackedTileId
{
public:
    //! Constructor with no value.
    explicit PackedTileId();

    //! Constructor.
    explicit PackedTileId(uint32_t value);

    //! Create a PackedTileId from the signed NDS.Live public value.
    //! Level 15 values are negative and are reinterpreted as their unsigned bit pattern.
    static PackedTileId fromValue(int32_t value);

    //! Create a PackedTileId that contains the point encoded by a MortonCode.
    //! This finds the tile at the specified level containing the full-precision
    //! NDS coordinates. The resulting mortonNumber() will NOT equal the input
    //! mortonCode.value(). Use fromTileIndex() if you need a specific morton number.
    PackedTileId(MortonCode mortonCode, const int level);

    //! Create a PackedTileId directly from a tile morton number and level.
    //! @param mortonNumber The tile's morton number (0 to 4^level - 1)
    //! @param level Tile level (0-15)
    //! @return PackedTileId with the specified morton number at the given level
    static PackedTileId fromTileIndex(uint32_t mortonNumber, int level);

    //! Create a PackedTileId from tile-grid coordinates at the given level.
    //! X is in [0, 2^(level+1)-1], Y is in [0, 2^level-1]. Coordinates follow
    //! the NDS Morton tile-grid order and are inverse to x()/y().
    static PackedTileId fromTileXY(uint32_t x, uint32_t y, int level);

    //! Create a PackedTileId containing the given NDS integer coordinate.
    static PackedTileId fromNdsCoordinates(int32_t x, int32_t y, int level);

    //! Create a PackedTileId containing the given WGS84 coordinate.
    static PackedTileId fromWgs84(double longitude, double latitude, int level);

    ///! Checks if the internal value represents an actual PackedTileId or not
    bool isValid() const;

public:
    //! Get the morton code of the south west corner
    //! from a the tile id.
    MortonCode southWestCorner() const;

    //! Get the morton code of the north east corner
    //! from a the tile id.
    MortonCode northEastCorner() const;

    //! Get the tile id left from the current tile.
    PackedTileId westNeighbour() const;

    //! Get the tile id right from the current tile.
    PackedTileId eastNeighbour() const;

    //! Get the tile id on the top of the current tile.
    PackedTileId northNeighbour() const;

    //! Get the tile id below the current tile.
    PackedTileId southNeighbour() const;

    //! Get the same-level tile at a relative grid offset.
    //! Offsets wrap in packed tile-grid space, matching the directional
    //! neighbour helpers but allowing multi-tile steps.
    PackedTileId neighbour(int32_t offsetX, int32_t offsetY) const;

    //! American-English alias for neighbour().
    PackedTileId neighbor(int32_t offsetX, int32_t offsetY) const;

    //! Get the tile center.
    void center(int32_t &centerX, int32_t &centerY) const;

    //! Convert NDS integer coordinates to lon/lat degrees without normalizing
    //! boundary maxima such as +180 longitude or +90 latitude.
    static std::pair<double, double> wgs84FromNdsCoordinates(int64_t x, int64_t y);

    //! Center of the tile in lon/lat degrees.
    std::pair<double, double> centerWgs84() const;

    //! South-west tile corner in lon/lat degrees.
    std::pair<double, double> southWestWgs84() const;

    //! Exclusive north-east tile corner in lon/lat degrees.
    std::pair<double, double> northEastWgs84() const;

    //! Tile width/height in lon/lat degrees.
    std::pair<double, double> wgs84Size() const;

    //! Get the level of the tile id.
    int level() const;

    //! Tile number according to Morton scheme
    uint32_t mortonNumber() const;

    //! Tile-grid X coordinate at this tile's level.
    //! This is the deinterleaved Morton X coordinate and has level+1 bits.
    uint32_t x() const;

    //! Tile-grid Y coordinate at this tile's level.
    //! This is the deinterleaved Morton Y coordinate and has level bits.
    uint32_t y() const;

    //! Width and height of the tile in NDS coord units
    uint32_t size() const;

    //! Get tile dimensions in meters.
    //! @return Pair of (width_meters, height_meters) calculated at the tile's center latitude.
    //! @note Dimensions vary by latitude - tiles are largest at the equator and shrink toward
    //! poles.
    //!       Width (longitude) is affected by cos(latitude), height (latitude) remains constant.
    template <typename T = double> DeltaInMeters<T> dimensionsInMeters() const;

    bool operator==(const PackedTileId &other) const;
    bool operator!=(const PackedTileId &other) const;
    bool operator<(const PackedTileId &other) const;

    //! Get the value as a signed 32-bit integer, per the NDS.Live standard.
    //! Levels 0-14 are positive; level 15 tiles are negative (bit 31 set), a
    //! deliberate signed-int32 "overflow" inherited from the original Java spec.
    int32_t value() const;

    //! Conversion operator for hash function.
    operator uint32_t() const;

private:
    //! The packed tile id.
    uint32_t value_;

}; // class PackedTileId

using PackedTileIds = std::vector<PackedTileId>;

//! Get all tile IDs that intersect with a bounding box defined by NDS coordinates.
//! @param swX South-west corner X coordinate (longitude) in NDS coordinates
//! @param swY South-west corner Y coordinate (latitude) in NDS coordinates
//! @param neX North-east corner X coordinate (longitude) in NDS coordinates
//! @param neY North-east corner Y coordinate (latitude) in NDS coordinates
//! @param level Tile level (0-15)
//! @return Vector of PackedTileId objects that intersect with the bounding box
PackedTileIds getTileIdsForBoundingBox(int32_t swX, int32_t swY, int32_t neX, int32_t neY,
                                       int level);

// Template implementation
template <typename T> DeltaInMeters<T> PackedTileId::dimensionsInMeters() const
{
    int32_t centerX, centerY;
    center(centerX, centerY);

    auto centerWgs = HighPrecWgs84::fromNdsCoordinates(centerX, centerY);
    uint32_t tileSize = size();

    return HighPrecWgs84::ndsDistanceToMeters(tileSize, tileSize, centerWgs.latitude());
}

} // namespace ndsmath
