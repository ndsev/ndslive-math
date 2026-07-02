// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#include "packedtileid.h"

#include "glm/glm.hpp"
#include "glm/ext.hpp"
#include <stdexcept>

namespace ndsmath
{

PackedTileId::PackedTileId() : value_(0u) {}

PackedTileId::PackedTileId(uint32_t value) : value_(value) {}

namespace
{
void validateLevel(int level)
{
    if (level < 0 || level > 15)
    {
        throw std::out_of_range("PackedTileId level must be in [0, 15]");
    }
}

// Deinterleave a tile's Morton number into its (x, y) tile-grid indices.
// Per the NDS Morton scheme, X has (level+1) bits and Y has level bits.
// Mirrors the Python reference's _deinterleave_morton.
void deinterleaveMorton(uint32_t morton, int level, uint32_t &x, uint32_t &y)
{
    x = 0;
    y = 0;
    for (int i = 0; i < level; ++i)
    {
        if (morton & (1u << (2 * i)))
            x |= (1u << i);
        if (morton & (1u << (2 * i + 1)))
            y |= (1u << i);
    }
    if (morton & (1u << (2 * level)))
        x |= (1u << level); // extra X bit
}

// Inverse of deinterleaveMorton.
uint32_t interleaveCoords(uint32_t x, uint32_t y, int level)
{
    uint32_t morton = 0;
    for (int i = 0; i < level; ++i)
    {
        if (x & (1u << i))
            morton |= (1u << (2 * i));
        if (y & (1u << i))
            morton |= (1u << (2 * i + 1));
    }
    if (x & (1u << level))
        morton |= (1u << (2 * level));
    return morton;
}
} // namespace

PackedTileId PackedTileId::fromValue(int32_t value)
{
    PackedTileId tile(static_cast<uint32_t>(value));
    if (!tile.isValid())
    {
        throw std::out_of_range("PackedTileId value is invalid");
    }
    return tile;
}

PackedTileId PackedTileId::fromTileIndex(uint32_t mortonNumber, int level)
{
    validateLevel(level);
    const auto maxMorton = (uint64_t{1} << (2 * level + 1)) - 1;
    if (static_cast<uint64_t>(mortonNumber) > maxMorton)
    {
        throw std::out_of_range("PackedTileId morton number exceeds level range");
    }
    return PackedTileId(mortonNumber + (1u << (16 + level)));
}

PackedTileId PackedTileId::fromTileXY(uint32_t x, uint32_t y, int level)
{
    validateLevel(level);
    const auto maxX = (uint32_t{1} << (level + 1)) - 1;
    const auto maxY = (uint32_t{1} << level) - 1;
    if (x > maxX || y > maxY)
    {
        throw std::out_of_range("PackedTileId tile-grid coordinate exceeds level range");
    }
    return fromTileIndex(interleaveCoords(x, y, level), level);
}

PackedTileId PackedTileId::fromNdsCoordinates(int32_t x, int32_t y, int level)
{
    validateLevel(level);
    return PackedTileId(MortonCode::fromNdsCoordinates(x, y), level);
}

PackedTileId PackedTileId::fromWgs84(double longitude, double latitude, int level)
{
    validateLevel(level);
    int32_t x;
    int32_t y;
    HighPrecWgs84(longitude, latitude).toNdsCoordinates(x, y);
    return fromNdsCoordinates(x, y, level);
}

// Neighbour traversal: deinterleave to (x, y) tile-grid indices, step by one
// with wraparound, and reinterleave. Because the tile numbering follows the
// two's-complement Morton ordering, an unsigned +/-1 with wrap is a correct
// geographic step in every direction, including the antimeridian (X) and
// pole (Y) wraps.

PackedTileId PackedTileId::westNeighbour() const
{
    const int lvl = level();
    uint32_t x, y;
    deinterleaveMorton(mortonNumber(), lvl, x, y);
    const uint32_t maxX = (1u << (lvl + 1)) - 1;
    x = (x - 1) & maxX;
    return fromTileIndex(interleaveCoords(x, y, lvl), lvl);
}

PackedTileId PackedTileId::eastNeighbour() const
{
    const int lvl = level();
    uint32_t x, y;
    deinterleaveMorton(mortonNumber(), lvl, x, y);
    const uint32_t maxX = (1u << (lvl + 1)) - 1;
    x = (x + 1) & maxX;
    return fromTileIndex(interleaveCoords(x, y, lvl), lvl);
}

PackedTileId PackedTileId::southNeighbour() const
{
    const int lvl = level();
    uint32_t x, y;
    deinterleaveMorton(mortonNumber(), lvl, x, y);
    const uint32_t maxY = (1u << lvl) - 1;
    y = (y - 1) & maxY;
    return fromTileIndex(interleaveCoords(x, y, lvl), lvl);
}

PackedTileId PackedTileId::northNeighbour() const
{
    const int lvl = level();
    uint32_t x, y;
    deinterleaveMorton(mortonNumber(), lvl, x, y);
    const uint32_t maxY = (1u << lvl) - 1;
    y = (y + 1) & maxY;
    return fromTileIndex(interleaveCoords(x, y, lvl), lvl);
}

PackedTileId::PackedTileId(MortonCode mortonCode, const int level)
{
    validateLevel(level);

    int32_t xCoord;
    int32_t yCoord;

    mortonCode.toNdsCoordinates(xCoord, yCoord);

    int64_t xCoord2 = xCoord;
    int64_t yCoord2 = yCoord;

    // Wrap negative coordinates into the unsigned range via two's complement
    // (add 2^32 for x, 2^31 for y), matching the reference implementation.
    if (xCoord2 < 0)
    {
        xCoord2 += (1LL << 32);
    }

    if (yCoord2 < 0)
    {
        yCoord2 += (1LL << 31);
    }

    int nLevel = 31 - level;

    int64_t nX = (xCoord2) >> nLevel;
    int64_t nY = (yCoord2) >> nLevel;

    MortonCode temp = MortonCode::fromNdsCoordinates(nX, nY);
    value_ = temp.value();
    value_ += (1u << (16 + level));
}

bool PackedTileId::isValid() const
{
    const auto MIN_PACKED_TILE_ID = 1u << 16u;
    if (value_ < MIN_PACKED_TILE_ID)
    {
        return false;
    }

    const auto tileLevel = level();
    if (tileLevel > 15)
    {
        return false;
    }

    const auto maxMorton = (uint64_t{1} << (2 * tileLevel + 1)) - 1;
    return static_cast<uint64_t>(mortonNumber()) <= maxMorton;
}

MortonCode PackedTileId::southWestCorner() const
{
    const uint64_t tileNum = mortonNumber();
    return MortonCode(tileNum << (63 - (2 * level() + 1)));
}

MortonCode PackedTileId::northEastCorner() const
{
    int32_t x, y;
    southWestCorner().toNdsCoordinates(x, y);
    auto const s = size();
    return MortonCode::fromNdsCoordinates(x + s, y + s);
}

void PackedTileId::center(int32_t &centerX, int32_t &centerY) const
{
    southWestCorner().toNdsCoordinates(centerX, centerY);
    auto const halfSize = size() / 2;
    centerX += halfSize;
    centerY += halfSize;
}

uint32_t PackedTileId::mortonNumber() const
{
    const auto tileLevel = level();
    return (value_ - (1u << (16 + tileLevel)));
}

uint32_t PackedTileId::x() const
{
    uint32_t resultX;
    uint32_t resultY;
    deinterleaveMorton(mortonNumber(), level(), resultX, resultY);
    return resultX;
}

uint32_t PackedTileId::y() const
{
    uint32_t resultX;
    uint32_t resultY;
    deinterleaveMorton(mortonNumber(), level(), resultX, resultY);
    return resultY;
}

uint32_t PackedTileId::size() const
{
    return 1u << (31 - (level()));
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

bool PackedTileId::operator==(const PackedTileId &other) const
{
    return value_ == other.value_;
}

bool PackedTileId::operator!=(const PackedTileId &other) const
{
    return value_ != other.value_;
}

bool PackedTileId::operator<(const PackedTileId &other) const
{
    return value_ < other.value_;
}

int32_t PackedTileId::value() const
{
    // Stored unsigned for clean bit math; the NDS.Live API value is signed
    // int32 (level-15 tiles are negative). Reinterpret the bit pattern.
    return static_cast<int32_t>(value_);
}

PackedTileId::operator uint32_t() const
{
    // Unsigned bit pattern, used for hashing / std::set keys.
    return value_;
}

PackedTileIds getTileIdsForBoundingBox(int32_t swX, int32_t swY, int32_t neX, int32_t neY,
                                       int level)
{
    validateLevel(level);
    PackedTileIds tileIds;

    // Calculate tile size at this level
    const uint32_t tileSize = 1u << (31 - level);

    auto const floorDiv = [](int64_t a, int64_t b)
    {
        auto q = a / b;
        auto r = a % b;
        if (r != 0 && ((a < 0) != (b < 0)))
        {
            --q;
        }
        return q;
    };

    const int64_t startTileX = floorDiv(swX, static_cast<int64_t>(tileSize));
    const int64_t startTileY = floorDiv(swY, static_cast<int64_t>(tileSize));
    const int64_t endTileX = floorDiv(neX, static_cast<int64_t>(tileSize));
    const int64_t endTileY = floorDiv(neY, static_cast<int64_t>(tileSize));

    // Iterate through all tiles in the bounding box
    for (int64_t tileY = startTileY; tileY <= endTileY; ++tileY)
    {
        for (int64_t tileX = startTileX; tileX <= endTileX; ++tileX)
        {
            // Calculate the south-west corner of this tile
            const int64_t tileSwX = tileX * static_cast<int64_t>(tileSize);
            const int64_t tileSwY = tileY * static_cast<int64_t>(tileSize);

            // Create morton code from the tile's south-west corner
            const MortonCode morton = MortonCode::fromNdsCoordinates(static_cast<int32_t>(tileSwX),
                                                                     static_cast<int32_t>(tileSwY));

            // Create the packed tile ID
            const PackedTileId tileId(morton, level);
            tileIds.push_back(tileId);
        }
    }

    return tileIds;
}

} // namespace ndsmath
