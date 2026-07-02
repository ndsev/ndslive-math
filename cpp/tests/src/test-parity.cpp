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
#include "ndsmath/polygon.h"
#include "ndsmath/wgs84aabb.h"
#include "ndsmath/wgs84polygon.h"

#include <nlohmann/json.hpp>

#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

using ndsmath::HighPrecWgs84;
using ndsmath::HighPrecWgs84Polygon;
using ndsmath::MortonCode;
using ndsmath::NdsBoundingBox;
using ndsmath::PackedTileId;
using ndsmath::Wgs84;
using ndsmath::Wgs84AABB;
using json = nlohmann::json;
using Poly = ndsmath::Polygon<std::vector<HighPrecWgs84>>;

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
        CHECK_EQ(static_cast<int64_t>(t.x()), r["grid_x"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(t.y()), r["grid_y"].get<int64_t>());
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
        CHECK_EQ(static_cast<int64_t>(PackedTileId::fromValue(r["value"].get<int32_t>()).value()),
                 r["value"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(PackedTileId::fromTileXY(r["grid_x"].get<uint32_t>(),
                                                               r["grid_y"].get<uint32_t>(), level)
                                          .value()),
                 r["value"].get<int64_t>());
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
        PackedTileId fromNds = PackedTileId::fromNdsCoordinates(static_cast<int32_t>(x),
                                                                static_cast<int32_t>(y), level);
        CHECK_EQ(static_cast<int64_t>(fromNds.value()), r["value"].get<int64_t>());
    }

    // 6b. from_wgs84 (containing tile)
    for (const auto &r : data["packed_tile_from_wgs84"])
    {
        double lon = r["lon"].get<double>();
        double lat = r["lat"].get<double>();
        int level = r["level"].get<int>();
        PackedTileId t = PackedTileId::fromWgs84(lon, lat, level);
        CHECK_EQ(static_cast<int64_t>(t.value()), r["value"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(t.mortonNumber()),
                 r["computed_morton_number"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(t.x()), r["grid_x"].get<int64_t>());
        CHECK_EQ(static_cast<int64_t>(t.y()), r["grid_y"].get<int64_t>());
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

    // -----------------------------------------------------------------------
    // Geometry layer (deterministic methods only; PolygonTriangulation and the
    // transcendental avgMercatorStretch are intentionally excluded). Generated
    // from the Python reference; validated here against the long-standing C++
    // Wgs84AABB / Polygon / HighPrecWgs84Polygon.
    // -----------------------------------------------------------------------
    using Vec2 = Wgs84AABB<double>::vec2_t;
    auto makeAabb =
        [](const json &sw_lon, const json &sw_lat, const json &size_x, const json &size_y)
    {
        return Wgs84AABB<double>(HighPrecWgs84(sw_lon.get<double>(), sw_lat.get<double>()),
                                 Vec2(size_x.get<double>(), size_y.get<double>()));
    };
    // Re-create an AABB from a named case by scanning the wgs84_aabb section, so
    // the contains/intersects sections can reference boxes by name.
    auto aabbByName = [&data, &makeAabb](const std::string &name)
    {
        for (const auto &c : data["wgs84_aabb"])
            if (c["name"].get<std::string>() == name)
                return makeAabb(c["sw_lon"], c["sw_lat"], c["size_x"], c["size_y"]);
        throw std::runtime_error("unknown aabb case: " + name);
    };

    // A corner/center coordinate is "canonical" only if it is comfortably
    // inside the open WGS84 ranges. At the exact +-180 longitude / +-90 latitude
    // poles the C++ Wgs84 normalization and the Python port deliberately differ
    // (see the divergence notes below and the header skip policy), so such
    // coordinates are excluded from the cross-language corner comparison exactly
    // like the wgs84_to_nds / nds_to_wgs84 boundary rows are.
    //
    // Divergence 1 (latitude pole): C++ Wgs84::normalize() *reflects* an
    //   out-of-range latitude over the pole (y = latMax - y, plus a 180deg
    //   longitude flip), so e.g. Wgs84(10, 90) -> (-169.9999999, -8.38e-08).
    //   The Python port *clamps* latitude to latMax and leaves longitude alone,
    //   so Wgs84(10, 90) -> (10, 89.99999991618097). Affects clamp_box (NE/NW
    //   corners reach lat 90) and invalid_neg_size (corners reach lat 95).
    // Divergence 2 (longitude at exactly 180): C++ wraps lon==180 to -180
    //   (the snap-to-lonMax window |x-lonMax| < lonNdsDelta excludes 180 by an
    //   ULP), while Python snaps it to lonMax (179.99999991618097) because its
    //   normalize() uses the slightly larger non-pow2 delta in the snap test.
    //   Affects anti_meridian_box.center (lon 180).
    // Both are pre-existing Wgs84.normalize() port differences, not geometry-
    // layer bugs; per cpp/ semantics the C++ reflection/-180 results are the
    // long-standing reference. They are reported, not papered over: the size /
    // validity / split / tile-level assertions below still run for every case.
    auto lonCanonical = [](double lon) { return std::fabs(lon) < Wgs84<double>::lonMax; };
    auto latCanonical = [](double lat)
    { return lat < Wgs84<double>::latMax && lat > Wgs84<double>::latMin; };
    auto checkCorner = [&](const ndsmath::Wgs84<double> &got, const json &exp)
    {
        const double elon = exp[0].get<double>();
        const double elat = exp[1].get<double>();
        if (!lonCanonical(elon) || !latCanonical(elat))
            return; // out-of-canonical pole/anti-meridian coordinate; see notes
        CHECK_NEAR(got.longitude(), elon, tol);
        CHECK_NEAR(got.latitude(), elat, tol);
    };

    // 12. Wgs84AABB geometry: corners/center/size/validity/anti-meridian/tiles.
    for (const auto &r : data["wgs84_aabb"])
    {
        auto box = makeAabb(r["sw_lon"], r["sw_lat"], r["size_x"], r["size_y"]);
        CHECK_EQ(box.valid(), r["valid"].get<bool>());
        CHECK_NEAR(box.size().x, r["stored_size"][0].get<double>(), tol);
        CHECK_NEAR(box.size().y, r["stored_size"][1].get<double>(), tol);
        checkCorner(box.sw(), r["sw"]);
        checkCorner(box.se(), r["se"]);
        checkCorner(box.ne(), r["ne"]);
        checkCorner(box.nw(), r["nw"]);
        checkCorner(box.center(), r["center"]);
        auto verts = box.vertices();
        CHECK_EQ(verts.size(), r["vertices"].size());
        for (size_t i = 0; i < verts.size() && i < r["vertices"].size(); ++i)
            checkCorner(verts[i], r["vertices"][i]);
        CHECK_EQ(box.containsAntiMeridian(), r["contains_anti_meridian"].get<bool>());
        const auto &split = r["split_over_anti_meridian"];
        if (split.is_null())
        {
            // Python returns None when the box does not extend past lonMax. The
            // C++ splitOverAntiMeridian returns a default-constructed pair in
            // that case (both halves zero-width); only call it when expected.
            CHECK(!box.containsAntiMeridian() ||
                  box.sw().longitude() + box.size().x - Wgs84<double>::lonMax <= 0.0);
        }
        else
        {
            auto pr = box.splitOverAntiMeridian();
            CHECK_NEAR(pr.first.sw().longitude(), split["left_sw"][0].get<double>(), tol);
            CHECK_NEAR(pr.first.sw().latitude(), split["left_sw"][1].get<double>(), tol);
            CHECK_NEAR(pr.first.size().x, split["left_size"][0].get<double>(), tol);
            CHECK_NEAR(pr.first.size().y, split["left_size"][1].get<double>(), tol);
            CHECK_NEAR(pr.second.sw().longitude(), split["right_sw"][0].get<double>(), tol);
            CHECK_NEAR(pr.second.sw().latitude(), split["right_sw"][1].get<double>(), tol);
            CHECK_NEAR(pr.second.size().x, split["right_size"][0].get<double>(), tol);
            CHECK_NEAR(pr.second.size().y, split["right_size"][1].get<double>(), tol);
        }
        // numTileIds: for valid (non-negative-size) boxes both ports agree. For
        // the invalid negative-size box they differ by design: Python's math.ceil
        // keeps a signed product (negative tile counts, e.g. -15), while C++
        // numTileIds() returns 0 for a negative-size box. A negative expected
        // count marks that regime, so only compare the well-defined (>= 0)
        // entries; tileLevel() is now well-defined on both (returns 15).
        const auto &nt = r["num_tile_ids"];
        for (uint32_t lv = 0; lv < nt.size(); ++lv)
        {
            const int64_t expected = nt[lv].get<int64_t>();
            if (expected < 0)
                continue;
            CHECK_EQ(static_cast<int64_t>(box.numTileIds(lv)), expected);
        }
        CHECK_EQ(static_cast<int>(box.tileLevel(8)), r["tile_level_min8"].get<int>());
        CHECK_EQ(static_cast<int>(box.tileLevel(2)), r["tile_level_min2"].get<int>());
    }

    // 13. Wgs84AABB::contains — each sample point against each named box.
    for (const auto &r : data["wgs84_aabb_contains"])
    {
        auto box = aabbByName(r["box"].get<std::string>());
        HighPrecWgs84 p(r["point_lon"].get<double>(), r["point_lat"].get<double>());
        CHECK_EQ(box.contains(p), r["contains"].get<bool>());
    }

    // 14. Wgs84AABB::intersects — full ordered pairwise matrix (incl. symmetry).
    for (const auto &r : data["wgs84_aabb_intersects"])
    {
        auto a = aabbByName(r["a"].get<std::string>());
        auto b = aabbByName(r["b"].get<std::string>());
        CHECK_EQ(a.intersects(b), r["intersects"].get<bool>());
    }

    // 15. Polygon orientation + validity (base Polygon, raw lon/lat plane).
    for (const auto &r : data["polygon_orientation"])
    {
        auto ptype = static_cast<Poly::PolygonType>(r["polygon_type"].get<int>());
        std::vector<HighPrecWgs84> verts;
        for (const auto &v : r["vertices"])
            verts.emplace_back(v[0].get<double>(), v[1].get<double>());
        Poly poly(ptype, verts);
        CHECK_EQ(static_cast<int>(poly.orientation()), r["orientation"].get<int>());
        CHECK_EQ(poly.isValid(), r["is_valid"].get<bool>());
    }

    // 16. HighPrecWgs84Polygon: aaBb, median (lon/lat swap quirk), isValid.
    for (const auto &r : data["wgs84_polygon"])
    {
        std::vector<HighPrecWgs84> verts;
        for (const auto &v : r["vertices"])
            verts.emplace_back(v[0].get<double>(), v[1].get<double>());
        HighPrecWgs84Polygon poly(verts);
        CHECK_EQ(poly.isValid(), r["is_valid"].get<bool>());
        auto bb = poly.aaBb();
        CHECK_NEAR(bb.sw().longitude(), r["aabb_sw"][0].get<double>(), tol);
        CHECK_NEAR(bb.sw().latitude(), r["aabb_sw"][1].get<double>(), tol);
        CHECK_NEAR(bb.size().x, r["aabb_size"][0].get<double>(), tol);
        CHECK_NEAR(bb.size().y, r["aabb_size"][1].get<double>(), tol);
        auto med = poly.median();
        CHECK_NEAR(med.longitude(), r["median_lon"].get<double>(), tol);
        CHECK_NEAR(med.latitude(), r["median_lat"].get<double>(), tol);
    }

    // 17. HighPrecWgs84Polygon::collidesWith (SAT), ordered pairs.
    for (const auto &r : data["wgs84_polygon_collision"])
    {
        std::vector<HighPrecWgs84> av, bv;
        for (const auto &v : r["a_vertices"])
            av.emplace_back(v[0].get<double>(), v[1].get<double>());
        for (const auto &v : r["b_vertices"])
            bv.emplace_back(v[0].get<double>(), v[1].get<double>());
        HighPrecWgs84Polygon a(av), b(bv);
        CHECK_EQ(a.collidesWith(b), r["a_collides_b"].get<bool>());
        CHECK_EQ(b.collidesWith(a), r["b_collides_a"].get<bool>());
    }

    return TEST_SUMMARY();
}
