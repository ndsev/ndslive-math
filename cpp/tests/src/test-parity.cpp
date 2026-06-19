// SPDX-License-Identifier: BSD-3-Clause
//
// Cross-language parity test: validates the C++ implementation against the
// shared golden vectors in test-vectors/parity_vectors.json (generated from the
// Python reference). Integer results are checked exactly; floating-point within
// the tolerance recorded in the file.
//
// The only intentional skips are representation/edge limits, not bugs:
//   * WGS84 normalization at the exact +-180 / +-90 boundary (out-of-canonical
//     inputs); such rows are skipped in the wgs84 sections.
//   * the exclusive NE corner of world-edge low-level tiles (reaches 2^31/2^30,
//     outside the int32 NDS coordinate range).
#include "test_harness.h"

#include "ndsmath/wgs84.h"
#include "ndsmath/mortoncode.h"
#include "ndsmath/packedtileid.h"
#include "ndsmath/ndsboundingbox.h"

#include <nlohmann/json.hpp>

#include <cstdlib>
#include <fstream>
#include <string>

using ndsmath::MortonCode;
using ndsmath::NdsBoundingBox;
using ndsmath::PackedTileId;
using ndsmath::Wgs84;
using json = nlohmann::json;

namespace
{

std::string vectorsPath()
{
    if (const char *env = std::getenv("PARITY_VECTORS"))
        return env;
#ifdef PARITY_VECTORS_PATH
    return PARITY_VECTORS_PATH;
#else
    return "test-vectors/parity_vectors.json";
#endif
}

} // namespace

int main()
{
    const std::string path = vectorsPath();
    std::ifstream in(path);
    if (!in)
    {
        std::cerr << "FATAL: cannot open parity vectors at " << path << "\n";
        return 2;
    }
    json data;
    in >> data;
    const double tol = data["_meta"]["float_tolerance"].get<double>();

    // 1. WGS84 -> NDS (skip non-canonical boundary inputs; see header note)
    for (const auto &r : data["wgs84_to_nds"])
    {
        double lon = r["lon"].get<double>();
        double lat = r["lat"].get<double>();
        if (std::fabs(lon) >= 180.0 || std::fabs(lat) >= 90.0)
            continue;
        Wgs84<double> w(lon, lat);
        int32_t x, y;
        w.toNdsCoordinates(x, y);
        CHECK_EQ(static_cast<int64_t>(x), r["nds_x"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(y), r["nds_y"].get<int64_t>());
    }

    // 2. NDS -> WGS84 (skip the +-2^31 boundary rows)
    for (const auto &r : data["nds_to_wgs84"])
    {
        int64_t x = r["x"].get<int64_t>();
        int64_t y = r["y"].get<int64_t>();
        if (x <= -(1LL << 31) || x >= (1LL << 31) - 1 || y <= -(1LL << 30) || y >= (1LL << 30) - 1)
            continue;
        Wgs84<double> w =
            Wgs84<double>::fromNdsCoordinates(static_cast<int32_t>(x), static_cast<int32_t>(y));
        CHECK_NEAR(w.longitude(), r["lon"].get<double>(), tol);
        CHECK_NEAR(w.latitude(), r["lat"].get<double>(), tol);
    }

    // 3. Morton encode/decode round-trip
    for (const auto &r : data["morton"])
    {
        int64_t x = r["x"].get<int64_t>();
        int64_t y = r["y"].get<int64_t>();
        MortonCode m = MortonCode::fromNdsCoordinates(x, y);
        CHECK_EQ(m.value(), std::stoull(r["morton"].get<std::string>()));
        int32_t dx, dy;
        m.toNdsCoordinates(dx, dy);
        CHECK_EQ(static_cast<int64_t>(dx), r["decoded_x"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(dy), r["decoded_y"].get<int64_t>());
    }

    // 4. PackedTileId from tile index
    for (const auto &r : data["packed_tile_from_index"])
    {
        uint32_t mortonNumber = r["morton_number"].get<uint32_t>();
        int level = r["level"].get<int>();
        PackedTileId t = PackedTileId::fromTileIndex(mortonNumber, level);
        CHECK_EQ(static_cast<int64_t>(t.value()), r["value"].get<int64_t>());
        CHECK_EQ(t.level(), r["computed_level"].get<int>());
        CHECK_EQ(static_cast<int64_t>(t.mortonNumber()),
                 r["computed_morton_number"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(t.size()), r["size"].get<int64_t>());
        int32_t sx, sy, nx, ny, cx, cy;
        t.southWestCorner().toNdsCoordinates(sx, sy);
        t.northEastCorner().toNdsCoordinates(nx, ny);
        t.center(cx, cy);
        CHECK_EQ(static_cast<int64_t>(sx), r["sw"][0].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(sy), r["sw"][1].get<int64_t>());
        // The exclusive NE corner of low-level (world-edge) tiles reaches 2^31 /
        // 2^30, outside the int32 NDS coordinate range. C++ wraps it via the
        // morton round-trip while the Python reference keeps the raw value, so
        // compare only when the corner is representable.
        const int64_t neX = r["ne"][0].get<int64_t>();
        const int64_t neY = r["ne"][1].get<int64_t>();
        if (neX < (1LL << 31) && neY < (1LL << 30))
        {
            CHECK_EQ(static_cast<int64_t>(nx), neX);
            CHECK_EQ(static_cast<int64_t>(ny), neY);
        }
        CHECK_EQ(static_cast<int64_t>(cx), r["center"][0].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(cy), r["center"][1].get<int64_t>());
    }

    // 5. Neighbours (all four directions)
    for (const auto &r : data["tile_neighbours"])
    {
        uint32_t mortonNumber = r["morton_number"].get<uint32_t>();
        int level = r["level"].get<int>();
        PackedTileId t = PackedTileId::fromTileIndex(mortonNumber, level);
        CHECK_EQ(static_cast<int64_t>(t.westNeighbour().value()), r["west"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(t.eastNeighbour().value()), r["east"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(t.southNeighbour().value()), r["south"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(t.northNeighbour().value()), r["north"].get<int64_t>());
    }

    // 6. from_morton_and_level (containing tile)
    for (const auto &r : data["from_morton_and_level"])
    {
        int64_t x = r["x"].get<int64_t>();
        int64_t y = r["y"].get<int64_t>();
        int level = r["level"].get<int>();
        MortonCode m = MortonCode::fromNdsCoordinates(x, y);
        PackedTileId t(m, level);
        CHECK_EQ(static_cast<int64_t>(t.value()), r["value"].get<int64_t>());
        CHECK_EQ(t.level(), r["computed_level"].get<int>());
        CHECK_EQ(static_cast<int64_t>(t.mortonNumber()),
                 r["computed_morton_number"].get<int64_t>());
    }

    // 7. getTileIdsForBoundingBox
    for (const auto &r : data["tiles_for_bbox"])
    {
        auto tiles = ndsmath::getTileIdsForBoundingBox(
            r["sw_x"].get<int32_t>(), r["sw_y"].get<int32_t>(), r["ne_x"].get<int32_t>(),
            r["ne_y"].get<int32_t>(), r["level"].get<int>());
        const auto &expected = r["tile_values"];
        CHECK_EQ(tiles.size(), expected.size());
        if (tiles.size() == expected.size())
        {
            for (size_t i = 0; i < tiles.size(); ++i)
                CHECK_EQ(static_cast<int64_t>(tiles[i].value()), expected[i].get<int64_t>());
        }
    }

    // 8. NdsBoundingBox intersects / contains
    for (const auto &r : data["nds_bbox_ops"])
    {
        auto a = r["a"];
        auto b = r["b"];
        NdsBoundingBox ba(a[0].get<int32_t>(), a[1].get<int32_t>(), a[2].get<int32_t>(),
                          a[3].get<int32_t>());
        NdsBoundingBox bb(b[0].get<int32_t>(), b[1].get<int32_t>(), b[2].get<int32_t>(),
                          b[3].get<int32_t>());
        CHECK_EQ(ba.intersects(bb), r["intersects"].get<bool>());
        CHECK_EQ(ba.contains(bb), r["a_contains_b"].get<bool>());
    }

    // 8b. bounding_box_from_tile_ids
    for (const auto &r : data["bbox_from_tiles"])
    {
        ndsmath::PackedTileIds tiles;
        for (const auto &v : r["tile_values"])
            tiles.push_back(PackedTileId(static_cast<uint32_t>(v.get<int64_t>())));
        auto bbox = ndsmath::boundingBoxFromTileIds(tiles);
        const auto &res = r["result"];
        CHECK_EQ(static_cast<int64_t>(bbox.minX), res[0].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(bbox.minY), res[1].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(bbox.maxX), res[2].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(bbox.maxY), res[3].get<int64_t>());
    }

    // 9. NdsBoundingBox::fromWgs84Corners
    for (const auto &r : data["nds_bbox_from_wgs84"])
    {
        Wgs84<double> sw(r["sw"][0].get<double>(), r["sw"][1].get<double>());
        Wgs84<double> ne(r["ne"][0].get<double>(), r["ne"][1].get<double>());
        auto bbox = NdsBoundingBox::fromWgs84Corners(sw, ne);
        CHECK_EQ(static_cast<int64_t>(bbox.minX), r["min_x"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(bbox.minY), r["min_y"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(bbox.maxX), r["max_x"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(bbox.maxY), r["max_y"].get<int64_t>());
    }

    // 10. distance / bearing (haversine)
    for (const auto &r : data["distance_bearing"])
    {
        Wgs84<double> a(r["a"][0].get<double>(), r["a"][1].get<double>());
        Wgs84<double> b(r["b"][0].get<double>(), r["b"][1].get<double>());
        CHECK_NEAR(a.distanceTo(b), r["distance_m"].get<double>(), 1e-3);
        CHECK_NEAR(a.bearingFrom(b), r["bearing_rad"].get<double>(), tol);
    }

    // 11. nds_distance_to_meters
    for (const auto &r : data["nds_distance_to_meters"])
    {
        auto wh = Wgs84<double>::ndsDistanceToMeters(
            r["nds_x"].get<int32_t>(), r["nds_y"].get<int32_t>(), r["at_latitude"].get<double>());
        CHECK_NEAR(wh.first, r["width_m"].get<double>(), 1e-3);
        CHECK_NEAR(wh.second, r["height_m"].get<double>(), 1e-3);
    }

    return TEST_SUMMARY();
}
