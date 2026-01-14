// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#include "ndsmath/wgs84polygon.h"

#include <vector>
#include <utility>

#include "catch2/catch_all.hpp"
#include "catch2/catch_test_macros.hpp"

using namespace ndsmath;


TEST_CASE("toNdsCoordinates uses floor", "[toNdsCoordinates]")
{
    // Floor should round toward -infinity, not toward zero (truncate)
    // This matters for negative coordinates near tile boundaries

    // Test positive coordinates (floor and truncate behave the same)
    HighPrecWgs84 positive(0.0001, 0.0001);
    int32_t px, py;
    positive.toNdsCoordinates(px, py);
    REQUIRE(px > 0);
    REQUIRE(py > 0);

    // Test negative coordinates (floor rounds down, truncate rounds toward zero)
    HighPrecWgs84 negative(-0.0001, -0.0001);
    int32_t nx, ny;
    negative.toNdsCoordinates(nx, ny);
    REQUIRE(nx < 0);
    REQUIRE(ny < 0);

    // Verify floor behavior: for small negative value, result should be -1 times unit, not 0
    // The scaled value is approximately -1193 for x and -1193 for y
    // floor(-1193.046) = -1194, truncate(-1193.046) = -1193
    // We verify floor by checking that very small negative gives more negative result
    HighPrecWgs84 tinyNeg(-1e-10, -1e-10);
    int32_t tnx, tny;
    tinyNeg.toNdsCoordinates(tnx, tny);
    REQUIRE(tnx == -1);  // floor(-tiny) = -1, not 0
    REQUIRE(tny == -1);

    // Roundtrip test: convert back and verify we're in the same "cell"
    auto backPositive = HighPrecWgs84::fromNdsCoordinates(px, py);
    auto backNegative = HighPrecWgs84::fromNdsCoordinates(nx, ny);

    REQUIRE(backPositive.longitude() >= 0.0);
    REQUIRE(backNegative.longitude() < 0.0);
}


TEST_CASE("Point inside polygon", "[isInsidePolygon]")
{
    std::vector<HighPrecWgs84> v = {
        HighPrecWgs84{30.10, 66.55},
        HighPrecWgs84{30.10, 66.27},
        HighPrecWgs84{29.90, 66.27},
        HighPrecWgs84{29.90, 66.55}
    };

    HighPrecWgs84 p{30.0, 66.30};
    REQUIRE(p.isInsidePolygon(v));

    HighPrecWgs84 p2{67.30, 30.0};
    REQUIRE_FALSE(p2.isInsidePolygon(v));
}


TEST_CASE("Polygon collision detection", "[collidesWith]")
{
    std::vector<HighPrecWgs84> v1 = {
        HighPrecWgs84{60.55, 30.1},
        HighPrecWgs84{66.27, 30.1},
        HighPrecWgs84{66.27, 29.90},
        HighPrecWgs84{66.55, 29.90}
    };

    HighPrecWgs84Polygon p1(v1);

    std::vector<std::pair<std::vector<HighPrecWgs84>, bool>> testData{
        {
            {
                HighPrecWgs84{66.505, 30.003},
                HighPrecWgs84{66.279, 30.003},
                HighPrecWgs84{66.279, 29.919},
                HighPrecWgs84{66.505, 29.919}
            },
            true
        },
        {
            {
                HighPrecWgs84{1., 1.},
                HighPrecWgs84{1., 0.},
                HighPrecWgs84{0., 0.},
                HighPrecWgs84{0., 1.}
            },
            false
        },
    };

    for (const auto& [polygon, expected] : testData) {
        HighPrecWgs84Polygon poly(polygon);
        REQUIRE(poly.collidesWith(p1) == expected);
    }

    std::vector<HighPrecWgs84> v2{
        HighPrecWgs84{0.8, 13.},
        HighPrecWgs84{2.7, 27.4},
        HighPrecWgs84{12.9, 31.2},
        HighPrecWgs84{24.1, 22.4},
        HighPrecWgs84{23.6, 8.5},
        HighPrecWgs84{13.2, .7}
    };
    HighPrecWgs84Polygon p2{v2};
    testData = {
        {
            {
                HighPrecWgs84{14.3, 38.4},
                HighPrecWgs84{17.0, 43.7},
                HighPrecWgs84{24.7, 40.7},
                HighPrecWgs84{26.5, 34.8},
                HighPrecWgs84{23.0, 31.2},
                HighPrecWgs84{16.85, 32.7}
            },
            false // completely outside
        },
        {
            {
                HighPrecWgs84{14.3, 31.4},
                HighPrecWgs84{17.0, 36.7},
                HighPrecWgs84{24.7, 33.7},
                HighPrecWgs84{26.5, 27.8},
                HighPrecWgs84{23.0, 24.2},
                HighPrecWgs84{16.85, 25.7}
            },
            true // partly overlapping
        },
        {
            {
                HighPrecWgs84{6.3, 17.4},
                HighPrecWgs84{9.0, 22.7},
                HighPrecWgs84{16.7, 19.7},
                HighPrecWgs84{18.5, 13.8},
                HighPrecWgs84{15.0, 10.2},
                HighPrecWgs84{8.85, 11.7}
            },
            true // completely inside
        },
    };

    for (const auto& [polygon, expected] : testData) {
        HighPrecWgs84Polygon poly(polygon);
        REQUIRE(poly.collidesWith(p2) == expected);
    }
}


TEST_CASE("Degrees to meters at equator", "[degreesToMeters]")
{
    // At equator (latitude 0), both longitude and latitude should have same meters per degree
    constexpr double METERS_PER_DEGREE = 111320.0;

    auto [lonMeters, latMeters] = HighPrecWgs84::degreesToMeters(1.0, 1.0, 0.0);

    REQUIRE(lonMeters == Catch::Approx(METERS_PER_DEGREE).margin(0.1));
    REQUIRE(latMeters == Catch::Approx(METERS_PER_DEGREE).margin(0.1));
}


TEST_CASE("Degrees to meters at different latitudes", "[degreesToMeters]")
{
    constexpr double METERS_PER_DEGREE = 111320.0;

    // At 60° latitude, longitude distance should be ~half of equatorial
    auto [lonMeters60, latMeters60] = HighPrecWgs84::degreesToMeters(1.0, 1.0, 60.0);

    REQUIRE(lonMeters60 == Catch::Approx(METERS_PER_DEGREE * 0.5).margin(1.0));
    REQUIRE(latMeters60 == Catch::Approx(METERS_PER_DEGREE).margin(0.1));

    // At poles (90°), longitude distance should be ~0
    auto [lonMeters90, latMeters90] = HighPrecWgs84::degreesToMeters(1.0, 1.0, 90.0);

    REQUIRE(lonMeters90 == Catch::Approx(0.0).margin(1.0));
    REQUIRE(latMeters90 == Catch::Approx(METERS_PER_DEGREE).margin(0.1));
}


TEST_CASE("NDS distance to meters conversion", "[ndsDistanceToMeters]")
{
    // Test with a known NDS distance
    // At equator, 1 NDS unit at level 0 (1 << 31) should cover half the earth's longitude
    constexpr int32_t HALF_NDS_X = 1u << 31;  // Half of NDS X range
    constexpr int32_t HALF_NDS_Y = 1u << 30;  // Half of NDS Y range

    auto [lonMeters, latMeters] = HighPrecWgs84::ndsDistanceToMeters(HALF_NDS_X, HALF_NDS_Y, 0.0);

    // Half the X range = 180° longitude at equator ≈ 20,037 km
    REQUIRE(lonMeters == Catch::Approx(20037500.0).margin(1000.0));

    // Half the Y range = 90° latitude ≈ 10,018 km
    REQUIRE(latMeters == Catch::Approx(10018750.0).margin(1000.0));
}


TEST_CASE("PackedTileId dimensions in meters", "[dimensionsInMeters]")
{
    // Test with tiles at a mid-latitude (45°) where dimensions are reasonable
    auto wgs45 = HighPrecWgs84(0.0, 45.0);
    int32_t x45, y45;
    wgs45.toNdsCoordinates(x45, y45);
    auto morton45 = MortonCode::fromNdsCoordinates(x45, y45);

    // Test level 5 tile (reasonable size)
    auto tile5 = PackedTileId(morton45, 5);
    auto [width5, height5] = tile5.dimensionsInMeters();

    // Dimensions should be positive and reasonable (not zero, not insanely large)
    REQUIRE(width5 > 0.0);
    REQUIRE(height5 > 0.0);
    REQUIRE(width5 < 10000000.0);  // Less than 10,000 km
    REQUIRE(height5 < 10000000.0);

    // Test level 6 tile (smaller than level 5)
    auto tile6 = PackedTileId(morton45, 6);
    auto [width6, height6] = tile6.dimensionsInMeters();

    // Higher level should have smaller dimensions
    REQUIRE(width6 < width5);
    REQUIRE(height6 < height5);

    // Each level increase divides tile size by 2 (in NDS units)
    // So both width and height should be approximately half
    // Note: Width varies slightly due to different tile center latitudes
    REQUIRE(width6 == Catch::Approx(width5 / 2.0).margin(10000.0));
    REQUIRE(height6 == Catch::Approx(height5 / 2.0).margin(1000.0));
}


TEST_CASE("Tile dimensions vary by latitude", "[dimensionsInMeters]")
{
    // Create tiles at different latitudes at level 5
    // Tile near equator (morton index that maps to ~0° latitude)
    auto tileEquator = PackedTileId::fromTileIndex(0, 5);
    auto [widthEq, heightEq] = tileEquator.dimensionsInMeters();

    // Tile at higher latitude (need to calculate morton for ~60° lat)
    // For simplicity, create a tile using coordinates
    auto wgs60 = HighPrecWgs84(0.0, 60.0);
    int32_t x60, y60;
    wgs60.toNdsCoordinates(x60, y60);
    auto morton60 = MortonCode::fromNdsCoordinates(x60, y60);
    auto tile60 = PackedTileId(morton60, 5);
    auto [width60, height60] = tile60.dimensionsInMeters();

    // Width should decrease with latitude (cos effect)
    REQUIRE(width60 < widthEq);

    // Height should remain approximately the same
    REQUIRE(height60 == Catch::Approx(heightEq).margin(100.0));
}

