// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#include "ndsmath/wgs84polygon.h"

#include <vector>
#include <utility>

#include "catch2/catch_all.hpp"
#include "catch2/catch_test_macros.hpp"

using namespace ndsmath;


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

