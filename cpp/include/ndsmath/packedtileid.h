// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include "mortoncode.h"
#include "wgs84.h"
#include <cstdint>
#include <vector>

#include <mapget/model/tileid.h>

namespace ndsmath
{

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

    //! Converstion operator for hash function.
    operator uint32_t() const;

    //! Penalty value to determine an inverse priority for the tile,
    //! in combination with a geographic position and a view direction.
    //! The orientation denotes the viewing angle from the given lon+lat
    //! position in counter-clockwise radians.
    double penalty(int32_t const& lon, int32_t const& lat, double const& orientation) const;

    //! Converts the packed tile id to a mapget::TileId.
    mapget::TileId toMapgetTileId() const;

    //! Create a packed tile id from a mapget::TileId.
    static PackedTileId fromMapgetTileId(mapget::TileId const& tileId);

private:
    //! The packed tile id.
    uint32_t value_;

}; // class PackedTileId

using PackedTileIds = std::vector<PackedTileId>;

} // namespace ndsmath
