// SPDX-License-Identifier: BSD-3-Clause
//
// Focused C++ unit tests for edge cases not fully covered by the golden-vector
// parity test (validity, level decoding, signed level-15 values, corners,
// antimeridian east/west wrap, bounding-box enumeration).
#include "test_harness.h"

#include "ndsmath/wgs84.h"
#include "ndsmath/mortoncode.h"
#include "ndsmath/packedtileid.h"
#include "ndsmath/ndsboundingbox.h"

#include <stdexcept>

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
    CHECK_EQ(PackedTileId::fromValue(std::numeric_limits<int32_t>::min()).value(),
             std::numeric_limits<int32_t>::min());

    // The explicit factory validates, while the raw constructor preserves the
    // legacy "construct then query isValid()" behavior.
    {
        bool threw = false;
        try
        {
            (void)PackedTileId::fromValue(0);
        }
        catch (const std::out_of_range &)
        {
            threw = true;
        }
        CHECK(threw);
    }

    // Added PackedTileId factories and tile-grid coordinate accessors.
    {
        auto tile = PackedTileId::fromTileXY(3, 1, 1);
        CHECK_EQ(tile.value(), static_cast<int32_t>(131079));
        CHECK_EQ(tile.x(), static_cast<uint32_t>(3));
        CHECK_EQ(tile.y(), static_cast<uint32_t>(1));
        CHECK_EQ(PackedTileId::fromValue(tile.value()).value(), tile.value());
        CHECK_EQ(tile.centerWgs84().first, -45.0);
        CHECK_EQ(tile.centerWgs84().second, -45.0);
        CHECK_EQ(tile.southWestWgs84().first, -90.0);
        CHECK_EQ(tile.southWestWgs84().second, -90.0);
        CHECK_EQ(tile.northEastWgs84().first, 0.0);
        CHECK_EQ(tile.northEastWgs84().second, 0.0);
        CHECK_EQ(tile.wgs84Size().first, 90.0);
        CHECK_EQ(tile.wgs84Size().second, 90.0);
        auto boundary = PackedTileId::wgs84FromNdsCoordinates(1LL << 31, 1LL << 30);
        CHECK_EQ(boundary.first, 180.0);
        CHECK_EQ(boundary.second, 90.0);

        auto fromNds = PackedTileId::fromNdsCoordinates(-65537, -65537, 15);
        auto fromWgs = PackedTileId::fromWgs84(-0.005493205972015858, -0.005493205972015858, 15);
        CHECK_EQ(fromNds.value(), static_cast<int32_t>(-4));
        CHECK_EQ(fromWgs.value(), static_cast<int32_t>(-4));
    }

    // Added factories reject invalid levels and grid coordinates.
    {
        bool threw = false;
        try
        {
            (void)PackedTileId::fromTileIndex(0, 16);
        }
        catch (const std::out_of_range &)
        {
            threw = true;
        }
        CHECK(threw);

        threw = false;
        try
        {
            (void)PackedTileId::fromTileXY(4, 0, 1);
        }
        catch (const std::out_of_range &)
        {
            threw = true;
        }
        CHECK(threw);

        threw = false;
        try
        {
            (void)PackedTileId::fromTileXY(0, 2, 1);
        }
        catch (const std::out_of_range &)
        {
            threw = true;
        }
        CHECK(threw);

        threw = false;
        try
        {
            (void)PackedTileId::fromNdsCoordinates(0, 0, 16);
        }
        catch (const std::out_of_range &)
        {
            threw = true;
        }
        CHECK(threw);

        threw = false;
        try
        {
            (void)PackedTileId::fromWgs84(0.0, 0.0, 16);
        }
        catch (const std::out_of_range &)
        {
            threw = true;
        }
        CHECK(threw);
    }

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
        CHECK(t1.neighbour(1, 0) == t1.eastNeighbour());
        CHECK(t1.neighbour(-1, 0) == t1.westNeighbour());
        CHECK(t1.neighbour(2, 0) == t1.eastNeighbour().eastNeighbour());
        CHECK(t1.neighbor(2, 0) == t1.neighbour(2, 0));
    }

    // Bounding-box enumeration: a 2x2 span yields four tiles.
    {
        constexpr int32_t tileSize = 1 << (31 - 13);
        auto tiles = ndsmath::getTileIdsForBoundingBox(0, 0, tileSize + 1, tileSize + 1, 13);
        CHECK_EQ(tiles.size(), static_cast<size_t>(4));
        for (const auto &t : tiles)
            CHECK_EQ(t.level(), 13);

        // boundingBoxFromTileIds over several tiles exercises the min/max
        // accumulation branch for the 2nd+ tile.
        auto bb = ndsmath::boundingBoxFromTileIds(tiles);
        CHECK_EQ(bb.minX, 0);
        CHECK_EQ(bb.minY, 0);
        CHECK_EQ(bb.maxX, 2 * tileSize - 1);
        CHECK_EQ(bb.maxY, 2 * tileSize - 1);
    }

    // boundingBoxFromTileIds rejects an empty list.
    {
        bool threw = false;
        try
        {
            ndsmath::boundingBoxFromTileIds(ndsmath::PackedTileIds{});
        }
        catch (const std::invalid_argument &)
        {
            threw = true;
        }
        CHECK(threw);
    }

    // MortonCode::fromWgs84Coordinates round-trips through NDS coordinates.
    {
        MortonCode m = MortonCode::fromWgs84Coordinates(Wgs84<double>(13.404954, 52.520008));
        int32_t x, y;
        m.toNdsCoordinates(x, y);
        CHECK(x > 0); // Berlin lies in the NE quadrant
        CHECK(y > 0);
        CHECK_EQ(MortonCode::fromNdsCoordinates(x, y).value(), m.value());
    }

    return TEST_SUMMARY();
}
