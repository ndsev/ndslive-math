// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#include "packedtileid.h"

#include "glm/glm.hpp"
#include "glm/ext.hpp"

namespace ndsmath
{

PackedTileId::PackedTileId() :
    value_(0u)
{
}

PackedTileId::PackedTileId(uint32_t value) :
    value_(value)
{
}

PackedTileId PackedTileId::westNeighbour() const
{
    int level = this->level();
    auto currentBit = 1u;

    auto result = value_;

    while (level >= 0)
    {
        if ((result & currentBit) != 0)
        {
            // Clear bit.
            result &= ~currentBit;
            break;
        }
        else
        {
            // Set bit and move to next level.
            result |= currentBit;
            level--;
            currentBit <<= 2;
        }
    }

    return PackedTileId(result);
}

PackedTileId PackedTileId::eastNeighbour() const
{
    int level = this->level();
    auto currentBit = 1u;

    auto result = value_;

    while (level >= 0)
    {
        if ((result & currentBit) == 0)
        {
            // Set bit.
            result |= currentBit;
            break;
        }
        else
        {
            // Set bit and move to next level.
            result &= ~currentBit;
            level--;
            currentBit <<= 2;
        }
    }

    return PackedTileId(result);
}

PackedTileId PackedTileId::southNeighbour() const
{
    int level = this->level();
    auto currentBit = 2u;

    auto result = value_;

    while (level >= 0)
    {
        if ((result & currentBit) != 0)
        {
            // Clear bit.
            result &= ~currentBit;
            break;
        }
        else
        {
            // Set bit and move to next level.
            result |= currentBit;
            level--;
            currentBit <<= 2;
        }
    }

    return PackedTileId(result);
}

PackedTileId PackedTileId::northNeighbour() const
{
    int level = this->level();
    auto currentBit = 2u;

    auto result = value_;

    while (level >= 0)
    {
        if ((result & currentBit) == 0)
        {
            // Set bit.
            result |= currentBit;
            break;
        }
        else
        {
            // Set bit and move to next level.
            result &= ~currentBit;
            level--;
            currentBit <<= 2;
        }
    }

    return PackedTileId(result);
}

PackedTileId::PackedTileId(MortonCode mortonCode, const int level)
{
    int32_t xCoord;
    int32_t yCoord;

    mortonCode.toNdsCoordinates(xCoord, yCoord);

    int64_t xCoord2 = xCoord;
    int64_t yCoord2 = yCoord;

    if (xCoord2 < 0)
    {
        xCoord2 += std::numeric_limits<uint32_t>::max();
    }

    if (yCoord2 < 0)
    {
        yCoord2 += std::numeric_limits<int32_t>::max();
    }

    int nLevel = 31 - level;

    int64_t nX = (xCoord2) >> nLevel;
    int64_t nY = (yCoord2) >> nLevel;

    MortonCode temp = MortonCode::fromNdsCoordinates(nX, nY);
    value_ = temp.value();
    value_ += (1 << (16 + level));
}

bool PackedTileId::isValid() const
{
   const auto MIN_PACKED_TILE_ID = 1u << 16u;
   return value_ >= MIN_PACKED_TILE_ID;
}

MortonCode PackedTileId::southWestCorner() const
{
    const uint64_t tileNum = mortonNumber();
    return MortonCode(tileNum << (63 - (2 * level() + 1)));
}

MortonCode PackedTileId::northEastCorner() const
{
    int32_t x,y;
    southWestCorner().toNdsCoordinates(x,y);
    auto const s = size();
    return MortonCode::fromNdsCoordinates(x + s, y + s);
}

void PackedTileId::center(int32_t &centerX, int32_t &centerY) const
{
    southWestCorner().toNdsCoordinates(centerX, centerY);
    auto const halfSize = size()/2;
    centerX += halfSize;
    centerY += halfSize;
}

uint32_t PackedTileId::mortonNumber() const
{
    const auto tileLevel = level();
    return (value_ - (1 << (16 + tileLevel)));
}

uint32_t PackedTileId::size() const
{
   return 1 << (31 - (level()));
}

int PackedTileId::level() const
{
    int level = 0;

    auto tID = value_ >> 16u;
    for (; tID > 1u; level++)
    {
        tID = tID >> 1;
    }

    return level;
}

bool PackedTileId::operator==(const PackedTileId& other) const
{
    return value_ == other.value_;
}

bool PackedTileId::operator!=(const PackedTileId& other) const
{
    return value_ != other.value_;
}

bool PackedTileId::operator<(const PackedTileId& other) const
{
    return value_ < other.value_;
}

uint32_t PackedTileId::value() const
{
    return value_;
}

PackedTileId::operator uint32_t() const
{
    return value();
}

PackedTileIds getTileIdsForBoundingBox(int32_t swX, int32_t swY, int32_t neX, int32_t neY, int level)
{
    PackedTileIds tileIds;
    
    // Calculate tile size at this level
    const uint32_t tileSize = 1u << (31 - level);
    
    // Calculate tile indices for the bounding box corners
    // We need to handle the coordinate system properly
    const int32_t startTileX = swX / static_cast<int32_t>(tileSize);
    const int32_t startTileY = swY / static_cast<int32_t>(tileSize);
    const int32_t endTileX = neX / static_cast<int32_t>(tileSize);
    const int32_t endTileY = neY / static_cast<int32_t>(tileSize);
    
    // Iterate through all tiles in the bounding box
    for (int32_t tileY = startTileY; tileY <= endTileY; ++tileY)
    {
        for (int32_t tileX = startTileX; tileX <= endTileX; ++tileX)
        {
            // Calculate the south-west corner of this tile
            const int32_t tileSwX = tileX * static_cast<int32_t>(tileSize);
            const int32_t tileSwY = tileY * static_cast<int32_t>(tileSize);
            
            // Create morton code from the tile's south-west corner
            const MortonCode morton = MortonCode::fromNdsCoordinates(tileSwX, tileSwY);
            
            // Create the packed tile ID
            const PackedTileId tileId(morton, level);
            tileIds.push_back(tileId);
        }
    }
    
    return tileIds;
}

} // namespace ndsmath
