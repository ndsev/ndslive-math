// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include "wgs84.h"
#include "packedtileid.h"
#include <algorithm>
#include <cstdint>
#include <stdexcept>

namespace ndsmath
{

//! Axis-aligned bounding box in NDS coordinates (32-bit integers).
//! NDS coordinates use integers for fast comparisons:
//! - X (longitude): 32-bit signed integer
//! - Y (latitude): 31-bit signed integer
struct NdsBoundingBox
{
    int32_t minX; //!< SW corner longitude (NDS coords)
    int32_t minY; //!< SW corner latitude (NDS coords)
    int32_t maxX; //!< NE corner longitude (NDS coords)
    int32_t maxY; //!< NE corner latitude (NDS coords)

    //! Default constructor
    NdsBoundingBox() : minX(0), minY(0), maxX(0), maxY(0) {}

    //! Constructor from NDS coordinates
    NdsBoundingBox(int32_t minX, int32_t minY, int32_t maxX, int32_t maxY)
        : minX(minX), minY(minY), maxX(maxX), maxY(maxY)
    {
    }

    //! Create bounding box from WGS84 corner coordinates.
    //! @param sw South-west corner (min longitude, min latitude)
    //! @param ne North-east corner (max longitude, max latitude)
    //! @return NdsBoundingBox with corners converted to NDS coordinates
    template <typename T>
    static NdsBoundingBox fromWgs84Corners(const Wgs84<T> &sw, const Wgs84<T> &ne)
    {
        int32_t swX, swY, neX, neY;
        sw.toNdsCoordinates(swX, swY);
        ne.toNdsCoordinates(neX, neY);
        return NdsBoundingBox(swX, swY, neX, neY);
    }

    //! Create bounding box from a tile ID.
    //! @param tile PackedTileId to create bbox from
    //! @return NdsBoundingBox covering the tile's area
    static NdsBoundingBox fromTile(const PackedTileId &tile)
    {
        int32_t swX, swY, neX, neY;
        tile.southWestCorner().toNdsCoordinates(swX, swY);
        tile.northEastCorner().toNdsCoordinates(neX, neY);
        return NdsBoundingBox(swX, swY, neX, neY);
    }

    //! Check if this bbox intersects (overlaps) with another.
    //! Two bounding boxes intersect if they share any area.
    //! @param other Another bounding box to check against
    //! @return True if the bounding boxes overlap
    bool intersects(const NdsBoundingBox &other) const
    {
        return !(maxX < other.minX || minX > other.maxX || maxY < other.minY || minY > other.maxY);
    }

    //! Check if this bbox fully contains another.
    //! @param other Another bounding box to check
    //! @return True if other is completely inside this bbox
    bool contains(const NdsBoundingBox &other) const
    {
        return minX <= other.minX && maxX >= other.maxX && minY <= other.minY && maxY >= other.maxY;
    }

    bool operator==(const NdsBoundingBox &other) const
    {
        return minX == other.minX && minY == other.minY && maxX == other.maxX && maxY == other.maxY;
    }

    bool operator!=(const NdsBoundingBox &other) const { return !(*this == other); }
};

//! Minimal bounding box in NDS coordinates that covers all the given tiles.
//! The NE corner is the inclusive last interior point (exclusive corner minus
//! one), matching getTileIdsForBoundingBox's inclusive coordinate treatment, so
//! a single tile round-trips back to itself. Computed in 64-bit because the
//! exclusive NE corner of a world-edge low-level tile reaches 2^31 / 2^30.
//! @throws std::invalid_argument if tiles is empty.
inline NdsBoundingBox boundingBoxFromTileIds(const PackedTileIds &tiles)
{
    if (tiles.empty())
        throw std::invalid_argument("boundingBoxFromTileIds: tiles must not be empty");

    int64_t minX = 0, minY = 0, maxX = 0, maxY = 0;
    bool first = true;
    for (const auto &tile : tiles)
    {
        int32_t sx, sy;
        tile.southWestCorner().toNdsCoordinates(sx, sy);
        const int64_t size = tile.size();
        const int64_t neX = static_cast<int64_t>(sx) + size;
        const int64_t neY = static_cast<int64_t>(sy) + size;
        if (first)
        {
            minX = sx;
            minY = sy;
            maxX = neX;
            maxY = neY;
            first = false;
        }
        else
        {
            minX = std::min<int64_t>(minX, sx);
            minY = std::min<int64_t>(minY, sy);
            maxX = std::max<int64_t>(maxX, neX);
            maxY = std::max<int64_t>(maxY, neY);
        }
    }
    return NdsBoundingBox(static_cast<int32_t>(minX), static_cast<int32_t>(minY),
                          static_cast<int32_t>(maxX - 1), static_cast<int32_t>(maxY - 1));
}

} // namespace ndsmath
