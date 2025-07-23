// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include "mortoncode.h"
#include "wgs84.h"
#include <cstdint>
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

    //! Create the packed tile id from the morton code and level.
    PackedTileId(MortonCode mortonCode, const int level);

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

    //! Get the tile center.
    void center(int32_t &centerX, int32_t &centerY) const;

    //! Get the level of the tile id.
    int level() const;

    //! Tile number according to Morton scheme
    uint32_t mortonNumber() const;

    //! Width and height of the tile in NDS coord units
    uint32_t size() const;

    bool operator==(const PackedTileId& other) const;
    bool operator!=(const PackedTileId& other) const;
    bool operator<(const PackedTileId& other) const;

    //! Get the value.
    uint32_t value() const;

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
PackedTileIds getTileIdsForBoundingBox(int32_t swX, int32_t swY, int32_t neX, int32_t neY, int level);

} // namespace ndsmath
