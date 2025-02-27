// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#include <glm/glm.hpp>
#include "ndsmath/packedtileid.h"

#include "catch2/catch_all.hpp"
#include "catch2/catch_test_macros.hpp"

#define LEVEL_MASK(level)                       \
    (1u << (level + 16u))

using namespace ndsmath;
using NdsCoord = glm::ivec2;

namespace {
    constexpr uint8_t TILE_LEVEL_13 = 13;
    constexpr uint32_t LEVEL13_TILE_LEN_NDS_UNITS = (1 << (32-(TILE_LEVEL_13+1)));
}

TEST_CASE("PackedTileId is valid", "[PackedTileId]")
{
    auto id = PackedTileId();
    REQUIRE_FALSE(id.isValid());
}

TEST_CASE("PackedTileId levels", "[PackedTileId]")
{
    /* Create tile-id from level 1 to 15 and check
     * if the `level` function of `PackedTileId` returns
     * the correct level. */
    for (auto level = 1u; level <= 15u; ++level) {
        REQUIRE(PackedTileId(LEVEL_MASK(level)).level() == level);
    }
}

TEST_CASE("PackedTileId tile number", "[PackedTileId]")
{
    constexpr auto size = LEVEL13_TILE_LEN_NDS_UNITS;

    struct TestData
    {
        uint32_t ndsX;
        uint32_t ndsY;
        uint8_t level;
        uint32_t tileNum;
    };

    std::vector<TestData> testData = {
        {1 * size/2, 1 * size/2, TILE_LEVEL_13, 0u},
        {3 * size/2, 1 * size/2, TILE_LEVEL_13, 1u},
        {1 * size/2, 3 * size/2, TILE_LEVEL_13, 2u},
        {3 * size/2, 3 * size/2, TILE_LEVEL_13, 3u}
    };

    for (const auto& data : testData) {
        auto morton = MortonCode::fromNdsCoordinates(data.ndsX, data.ndsY);
        auto tileId = PackedTileId(morton, data.level);
        REQUIRE(tileId.mortonNumber() == data.tileNum);
    }
}

TEST_CASE("PackedTileId neighbours", "[PackedTileId]")
{
    constexpr auto size = LEVEL13_TILE_LEN_NDS_UNITS;
    auto morton = MortonCode::fromNdsCoordinates(size/2, size/2);
    auto refTile = PackedTileId(morton, 13);

    REQUIRE(refTile == refTile.eastNeighbour().westNeighbour());
    REQUIRE(refTile == refTile.northNeighbour().southNeighbour());
    REQUIRE(refTile == refTile.westNeighbour().eastNeighbour());
    REQUIRE(refTile == refTile.southNeighbour().northNeighbour());
}

TEST_CASE("PackedTileId corners", "[PackedTileId]") {
    auto morton = MortonCode::fromNdsCoordinates(LEVEL13_TILE_LEN_NDS_UNITS/2, LEVEL13_TILE_LEN_NDS_UNITS/2);
    auto refTile = PackedTileId(morton, 13);

    NdsCoord refTileNorthEast;
    refTile.northEastCorner().toNdsCoordinates(refTileNorthEast.x, refTileNorthEast.y);
    REQUIRE(refTileNorthEast.x == LEVEL13_TILE_LEN_NDS_UNITS);
    REQUIRE(refTileNorthEast.y == LEVEL13_TILE_LEN_NDS_UNITS);

    NdsCoord refTileSouthWest;
    refTile.southWestCorner().toNdsCoordinates(refTileSouthWest.x, refTileSouthWest.y);
    REQUIRE(refTileSouthWest.x == 0);
    REQUIRE(refTileSouthWest.y == 0);
}

TEST_CASE("PackedTileId longitude edge", "[PackedTileId]") {
    constexpr auto OFFSET = LEVEL13_TILE_LEN_NDS_UNITS >> 1;
    auto morton1 = MortonCode::fromNdsCoordinates((1 << 31) - OFFSET, OFFSET);
    auto refTile1 = PackedTileId(morton1, 13);
    int32_t x1, y1;
    refTile1.northEastCorner().toNdsCoordinates(x1, y1);

    auto morton2 = MortonCode::fromNdsCoordinates(-(1 << 31) + OFFSET, OFFSET);
    int32_t x2, y2;
    auto refTile2 = PackedTileId(morton2, 13);
    refTile2.southWestCorner().toNdsCoordinates(x2, y2);

    REQUIRE(refTile1.eastNeighbour() == refTile2);
    REQUIRE(refTile2.westNeighbour() == refTile1);
    REQUIRE(x1 == x2);
}

