// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#include <glm/glm.hpp>
#include <set>
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

TEST_CASE("getTileIdsForBoundingBox specific bounding box", "[PackedTileId]") {
    // Given bounding box in NDS coordinates
    const int32_t swX = 132644864;  // southwest longitude
    const int32_t swY = 572522496;  // southwest latitude
    const int32_t neX = 132907007;  // northeast longitude
    const int32_t neY = 572784639;  // northeast latitude
    const int level = 13;
    
    // Expected tile ID
    const uint32_t expectedTileId = 545379780;
    
    // Get tile IDs for the bounding box
    auto tileIds = getTileIdsForBoundingBox(swX, swY, neX, neY, level);
    
    // Check that the expected tile ID is in the result
    bool found = false;
    for (const auto& tile : tileIds) {
        if (tile.value() == expectedTileId) {
            found = true;
            break;
        }
    }
    REQUIRE(found);
    
    // Verify the bounding box is contained within a single tile at level 13
    REQUIRE(tileIds.size() == 1);
}

TEST_CASE("getTileIdsForBoundingBox multiple tiles", "[PackedTileId]") {
    // Create a bounding box that spans 2x2 tiles
    const uint32_t tileSize = 1u << (31 - 13);  // Size of a level 13 tile
    
    // Start at tile boundary
    const int32_t swX = 0;
    const int32_t swY = 0;
    // End just inside the neighboring tiles
    const int32_t neX = static_cast<int32_t>(tileSize) + 1;
    const int32_t neY = static_cast<int32_t>(tileSize) + 1;
    
    auto tileIds = getTileIdsForBoundingBox(swX, swY, neX, neY, 13);
    
    // Should get exactly 4 tiles (2x2)
    REQUIRE(tileIds.size() == 4);
}

TEST_CASE("getTileIdsForBoundingBox single point", "[PackedTileId]") {
    // Test bounding box with same SW and NE corners
    const int32_t x = 132644864;
    const int32_t y = 572522496;
    const int level = 13;
    
    auto tileIds = getTileIdsForBoundingBox(x, y, x, y, level);
    
    // Should get exactly 1 tile
    REQUIRE(tileIds.size() == 1);
}

TEST_CASE("getTileIdsForBoundingBox negative coordinates", "[PackedTileId]") {
    // Test bounding box with negative coordinates
    const int32_t swX = -132644864;
    const int32_t swY = -572522496;
    const int32_t neX = -132644864 + 100000;
    const int32_t neY = -572522496 + 100000;
    const int level = 10;
    
    auto tileIds = getTileIdsForBoundingBox(swX, swY, neX, neY, level);
    
    // Should get at least one tile
    REQUIRE(tileIds.size() >= 1);
    
    // Verify all tiles have valid IDs
    for (const auto& tile : tileIds) {
        REQUIRE(tile.value() > 0);
        REQUIRE(tile.level() == level);
    }
}

TEST_CASE("getTileIdsForBoundingBox ground truth verification", "[PackedTileId]") {
    // Test with known ground truth data
    const int32_t swX = -209157330;
    const int32_t swY = 174937580;
    const int32_t neX = -208540811;
    const int32_t neY = 175239411;
    const int level = 13;

    // Expected tile IDs from ground truth
    std::set<uint32_t> expectedTileIds = {
        626579086, 626579087, 626579098, 626579120, 626579109, 626579108
    };

    auto tileIds = getTileIdsForBoundingBox(swX, swY, neX, neY, level);

    // Should get exactly 6 tiles
    REQUIRE(tileIds.size() == 6);

    // Verify all expected tiles are found
    std::set<uint32_t> foundIds;
    for (const auto& tile : tileIds) {
        foundIds.insert(tile.value());
    }

    REQUIRE(foundIds == expectedTileIds);
}

TEST_CASE("PackedTileId fromTileIndex", "[PackedTileId]") {
    // Test basic case - the original bug report
    auto tile = PackedTileId::fromTileIndex(4, 2);
    REQUIRE(tile.mortonNumber() == 4);
    REQUIRE(tile.level() == 2);

    // Test various levels and morton numbers
    struct TestData {
        uint32_t mortonNumber;
        int level;
    };

    std::vector<TestData> testData = {
        {0, 1},    // First tile at level 1
        {3, 1},    // Last tile at level 1 (4^1 - 1 = 3)
        {0, 13},   // First tile at level 13
        {15, 2},   // Last tile at level 2 (4^2 - 1 = 15)
        {100, 10}  // Arbitrary tile at level 10
    };

    for (const auto& data : testData) {
        auto tile = PackedTileId::fromTileIndex(data.mortonNumber, data.level);
        REQUIRE(tile.mortonNumber() == data.mortonNumber);
        REQUIRE(tile.level() == data.level);
    }
}

TEST_CASE("PackedTileId fromTileIndex valid corners", "[PackedTileId]") {
    auto tile = PackedTileId::fromTileIndex(4, 2);

    // Get corners
    int32_t swX, swY, neX, neY;
    tile.southWestCorner().toNdsCoordinates(swX, swY);
    tile.northEastCorner().toNdsCoordinates(neX, neY);

    // Tile size at level 2
    const uint32_t expectedSize = 1u << (31 - 2);
    REQUIRE(tile.size() == expectedSize);

    // Verify tile dimensions
    REQUIRE(static_cast<uint32_t>(neX - swX) == expectedSize);
    REQUIRE(static_cast<uint32_t>(neY - swY) == expectedSize);
}

