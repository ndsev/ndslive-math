// SPDX-License-Identifier: BSD-3-Clause
//
// Focused C++ unit tests for edge cases not fully covered by the golden-vector
// parity test (validity, level decoding, signed level-15 values, corners,
// antimeridian east/west wrap, bounding-box enumeration).
#include "test_harness.h"

#include "ndsmath/wgs84.h"
#include "ndsmath/mortoncode.h"
#include "ndsmath/packedtileid.h"

#include <cstdint>
#include <limits>

using ndsmath::MortonCode;
using ndsmath::PackedTileId;
using ndsmath::Wgs84;

int main()
{
    // Default-constructed id is not a valid tile.
    CHECK(!PackedTileId().isValid());

    // level() decodes every level 1..15.
    for (int level = 1; level <= 15; ++level)
    {
        uint32_t mask = 1u << (level + 16);
        CHECK_EQ(PackedTileId(mask).level(), level);
    }

    // Signed int32 value per NDS.Live spec: level 15 tiles are negative.
    CHECK_EQ(PackedTileId::fromTileIndex(0, 15).value(),
             std::numeric_limits<int32_t>::min()); // 0x80000000 -> -2147483648
    CHECK_EQ(PackedTileId::fromTileIndex((1u << 31) - 1, 15).value(),
             static_cast<int32_t>(-1)); // 0xFFFFFFFF -> -1
    CHECK_EQ(PackedTileId::fromTileIndex(0, 14).value(),
             static_cast<int32_t>(1u << 30)); // 1073741824 (positive)

    // Corners of a level-13 tile at the SW origin.
    constexpr uint32_t L13 = 1u << (32 - 14); // tile length in NDS units
    {
        MortonCode m = MortonCode::fromNdsCoordinates(L13 / 2, L13 / 2);
        PackedTileId t(m, 13);
        int32_t sx, sy, nx, ny;
        t.southWestCorner().toNdsCoordinates(sx, sy);
        t.northEastCorner().toNdsCoordinates(nx, ny);
        CHECK_EQ(sx, 0);
        CHECK_EQ(sy, 0);
        CHECK_EQ(static_cast<uint32_t>(nx - sx), L13);
        CHECK_EQ(static_cast<uint32_t>(ny - sy), L13);
        CHECK_EQ(t.size(), L13);
    }

    // East/west neighbours wrap across the antimeridian and round-trip.
    {
        const int64_t offset = L13 / 2;
        MortonCode m1 = MortonCode::fromNdsCoordinates((1LL << 31) - offset, offset);
        MortonCode m2 = MortonCode::fromNdsCoordinates(-(1LL << 31) + offset, offset);
        PackedTileId t1(m1, 13);
        PackedTileId t2(m2, 13);
        CHECK(t1.eastNeighbour() == t2);
        CHECK(t2.westNeighbour() == t1);
        // Round-trip in both directions.
        CHECK(t1.eastNeighbour().westNeighbour() == t1);
        CHECK(t1.westNeighbour().eastNeighbour() == t1);
    }

    // Bounding-box enumeration: a 2x2 span yields four tiles.
    {
        constexpr int32_t tileSize = 1 << (31 - 13);
        auto tiles = ndsmath::getTileIdsForBoundingBox(0, 0, tileSize + 1, tileSize + 1, 13);
        CHECK_EQ(tiles.size(), static_cast<size_t>(4));
        for (const auto &t : tiles)
            CHECK_EQ(t.level(), 13);
    }

    return TEST_SUMMARY();
}
