// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>

#include "ndsmath/ndsboundingbox.h"

using namespace ndsmath;

TEST_CASE("NdsBoundingBox default constructor", "[NdsBoundingBox]")
{
    NdsBoundingBox bbox;

    REQUIRE(bbox.minX == 0);
    REQUIRE(bbox.minY == 0);
    REQUIRE(bbox.maxX == 0);
    REQUIRE(bbox.maxY == 0);
}

TEST_CASE("NdsBoundingBox constructor from NDS coordinates", "[NdsBoundingBox]")
{
    NdsBoundingBox bbox(100, 200, 300, 400);

    REQUIRE(bbox.minX == 100);
    REQUIRE(bbox.minY == 200);
    REQUIRE(bbox.maxX == 300);
    REQUIRE(bbox.maxY == 400);
}

TEST_CASE("NdsBoundingBox fromWgs84Corners", "[NdsBoundingBox]")
{
    // Create WGS84 corners for a bbox around Berlin
    HighPrecWgs84 sw(13.0, 52.0);  // SW corner
    HighPrecWgs84 ne(14.0, 53.0);  // NE corner

    auto bbox = NdsBoundingBox::fromWgs84Corners(sw, ne);

    // Convert back to verify
    auto swBack = HighPrecWgs84::fromNdsCoordinates(bbox.minX, bbox.minY);
    auto neBack = HighPrecWgs84::fromNdsCoordinates(bbox.maxX, bbox.maxY);

    REQUIRE(swBack.longitude() == Catch::Approx(13.0).margin(0.0001));
    REQUIRE(swBack.latitude() == Catch::Approx(52.0).margin(0.0001));
    REQUIRE(neBack.longitude() == Catch::Approx(14.0).margin(0.0001));
    REQUIRE(neBack.latitude() == Catch::Approx(53.0).margin(0.0001));
}

TEST_CASE("NdsBoundingBox fromTile", "[NdsBoundingBox]")
{
    auto tile = PackedTileId::fromTileIndex(4, 2);
    auto bbox = NdsBoundingBox::fromTile(tile);

    // Verify bbox matches tile corners
    int32_t swX, swY, neX, neY;
    tile.southWestCorner().toNdsCoordinates(swX, swY);
    tile.northEastCorner().toNdsCoordinates(neX, neY);

    REQUIRE(bbox.minX == swX);
    REQUIRE(bbox.minY == swY);
    REQUIRE(bbox.maxX == neX);
    REQUIRE(bbox.maxY == neY);
}

TEST_CASE("NdsBoundingBox intersects - overlapping boxes", "[NdsBoundingBox]")
{
    NdsBoundingBox bbox1(0, 0, 100, 100);
    NdsBoundingBox bbox2(50, 50, 150, 150);

    REQUIRE(bbox1.intersects(bbox2));
    REQUIRE(bbox2.intersects(bbox1));
}

TEST_CASE("NdsBoundingBox intersects - non-overlapping boxes", "[NdsBoundingBox]")
{
    NdsBoundingBox bbox1(0, 0, 100, 100);
    NdsBoundingBox bbox2(200, 200, 300, 300);

    REQUIRE_FALSE(bbox1.intersects(bbox2));
    REQUIRE_FALSE(bbox2.intersects(bbox1));
}

TEST_CASE("NdsBoundingBox intersects - touching edges", "[NdsBoundingBox]")
{
    NdsBoundingBox bbox1(0, 0, 100, 100);
    NdsBoundingBox bbox2(100, 0, 200, 100);

    // Touching at edge counts as intersecting
    REQUIRE(bbox1.intersects(bbox2));
}

TEST_CASE("NdsBoundingBox intersects - one inside other", "[NdsBoundingBox]")
{
    NdsBoundingBox outer(0, 0, 100, 100);
    NdsBoundingBox inner(25, 25, 75, 75);

    REQUIRE(outer.intersects(inner));
    REQUIRE(inner.intersects(outer));
}

TEST_CASE("NdsBoundingBox contains - inner box", "[NdsBoundingBox]")
{
    NdsBoundingBox outer(0, 0, 100, 100);
    NdsBoundingBox inner(25, 25, 75, 75);

    REQUIRE(outer.contains(inner));
    REQUIRE_FALSE(inner.contains(outer));
}

TEST_CASE("NdsBoundingBox contains - same box", "[NdsBoundingBox]")
{
    NdsBoundingBox bbox(0, 0, 100, 100);

    REQUIRE(bbox.contains(bbox));
}

TEST_CASE("NdsBoundingBox contains - partially overlapping", "[NdsBoundingBox]")
{
    NdsBoundingBox bbox1(0, 0, 100, 100);
    NdsBoundingBox bbox2(50, 50, 150, 150);

    REQUIRE_FALSE(bbox1.contains(bbox2));
    REQUIRE_FALSE(bbox2.contains(bbox1));
}

TEST_CASE("NdsBoundingBox equality operators", "[NdsBoundingBox]")
{
    NdsBoundingBox bbox1(0, 0, 100, 100);
    NdsBoundingBox bbox2(0, 0, 100, 100);
    NdsBoundingBox bbox3(0, 0, 100, 200);

    REQUIRE(bbox1 == bbox2);
    REQUIRE_FALSE(bbox1 != bbox2);
    REQUIRE(bbox1 != bbox3);
    REQUIRE_FALSE(bbox1 == bbox3);
}

TEST_CASE("NdsBoundingBox tile intersection check", "[NdsBoundingBox]")
{
    // Create a bbox from WGS84 coordinates
    HighPrecWgs84 sw(13.3, 52.4);
    HighPrecWgs84 ne(13.5, 52.6);
    auto queryBbox = NdsBoundingBox::fromWgs84Corners(sw, ne);

    // Create a tile at level 13 containing the area
    auto wgsCenter = HighPrecWgs84(13.4, 52.5);
    int32_t cx, cy;
    wgsCenter.toNdsCoordinates(cx, cy);
    auto morton = MortonCode::fromNdsCoordinates(cx, cy);
    auto tile = PackedTileId(morton, 13);
    auto tileBbox = NdsBoundingBox::fromTile(tile);

    // The tile should intersect with the query bbox
    REQUIRE(queryBbox.intersects(tileBbox));
    REQUIRE(tileBbox.intersects(queryBbox));
}
