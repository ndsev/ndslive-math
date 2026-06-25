// SPDX-License-Identifier: BSD-3-Clause
//
// Unit tests for the C++-only geometry layer that has no cross-language parity
// vectors: Polygon<>, HighPrecWgs84Polygon, Wgs84AABB, and PolygonTriangulation
// (ear clipping). Exercised directly here so they are covered.
#include "test_harness.h"

#include "ndsmath/polygon.h"
#include "ndsmath/wgs84polygon.h"
#include "ndsmath/wgs84aabb.h"
#include "ndsmath/polygontriangulation.h"
#include "ndsmath/packedtileid.h"
#include "ndsmath/mortoncode.h"

#include <cmath>
#include <vector>

using ndsmath::HighPrecWgs84;
using ndsmath::HighPrecWgs84Polygon;
using ndsmath::PackedTileId;
using ndsmath::PolygonTriangulation;
using ndsmath::Wgs84AABB;
using Poly = ndsmath::Polygon<std::vector<HighPrecWgs84>>;
using Vec2 = Wgs84AABB<double>::vec2_t;

int main()
{
    // ---- Polygon<> base template -------------------------------------------
    {
        Poly p; // default: UNKNOWN type, empty
        CHECK(p.type() == Poly::UNKNOWN);
        CHECK(!p.isValid()); // empty → invalid
        p.setType(Poly::SIMPLE_POLYGON);
        CHECK(p.type() == Poly::SIMPLE_POLYGON);

        p.addVertex(HighPrecWgs84(0, 0));
        std::vector<HighPrecWgs84> more{HighPrecWgs84(1, 0), HighPrecWgs84(0, 1)};
        p.addVertices(more);
        CHECK(p.isValid()); // non-empty → valid
        CHECK_EQ(p.vertices().size(), static_cast<size_t>(3));

        // operator[] (non-const + const)
        CHECK_NEAR(p[0].longitude(), 0.0, 1e-12);
        const Poly &cp = p;
        CHECK_NEAR(cp[1].longitude(), 1.0, 1e-12);

        // non-const vertices() accessor is mutable
        p.vertices().push_back(HighPrecWgs84(2, 2));
        CHECK_EQ(p.vertices().size(), static_cast<size_t>(4));
    }

    // ---- Polygon orientation -----------------------------------------------
    {
        Poly ccw(Poly::SIMPLE_POLYGON,
                 {HighPrecWgs84(0, 0), HighPrecWgs84(1, 0), HighPrecWgs84(0, 1)});
        CHECK(ccw.orientation() == Poly::COUNTERCLOCKWISE);

        Poly cw(Poly::SIMPLE_POLYGON,
                {HighPrecWgs84(0, 0), HighPrecWgs84(0, 1), HighPrecWgs84(1, 0)});
        CHECK(cw.orientation() == Poly::CLOCKWISE);

        // Collinear vertices → zero area → INVALID_ORIENTATION.
        Poly flat(Poly::SIMPLE_POLYGON,
                  {HighPrecWgs84(0, 0), HighPrecWgs84(1, 1), HighPrecWgs84(2, 2)});
        CHECK(flat.orientation() == Poly::INVALID_ORIENTATION);

        // Unsupported type → early INVALID_ORIENTATION.
        Poly strip(Poly::TRIANGLE_STRIP,
                   {HighPrecWgs84(0, 0), HighPrecWgs84(1, 0), HighPrecWgs84(0, 1)});
        CHECK(strip.orientation() == Poly::INVALID_ORIENTATION);

        // A single-triangle TRIANGLE_LIST is allowed.
        Poly tlist(Poly::TRIANGLE_LIST,
                   {HighPrecWgs84(0, 0), HighPrecWgs84(1, 0), HighPrecWgs84(0, 1)});
        CHECK(tlist.orientation() == Poly::COUNTERCLOCKWISE);
    }

    // ---- HighPrecWgs84Polygon ----------------------------------------------
    {
        HighPrecWgs84Polygon empty;
        CHECK(empty.type() == HighPrecWgs84Polygon::SIMPLE_POLYGON);
        CHECK(!empty.isValid()); // < 3 vertices
        // aaBb() on an invalid polygon → default (empty) AABB.
        CHECK_NEAR(empty.aaBb().size().x, 0.0, 1e-12);

        HighPrecWgs84Polygon tri({HighPrecWgs84(0, 0), HighPrecWgs84(4, 0), HighPrecWgs84(0, 4)});
        CHECK(tri.isValid());

        auto bb = tri.aaBb();
        CHECK_NEAR(bb.sw().longitude(), 0.0, 1e-9);
        CHECK_NEAR(bb.sw().latitude(), 0.0, 1e-9);
        CHECK_NEAR(bb.size().x, 4.0, 1e-9);
        CHECK_NEAR(bb.size().y, 4.0, 1e-9);

        // operator==
        HighPrecWgs84Polygon same({HighPrecWgs84(0, 0), HighPrecWgs84(4, 0), HighPrecWgs84(0, 4)});
        HighPrecWgs84Polygon diffVert(
            {HighPrecWgs84(0, 0), HighPrecWgs84(4, 0), HighPrecWgs84(1, 4)});
        HighPrecWgs84Polygon quad(
            {HighPrecWgs84(0, 0), HighPrecWgs84(4, 0), HighPrecWgs84(4, 4), HighPrecWgs84(0, 4)});
        CHECK(tri == same);
        CHECK(!(tri == diffVert)); // same size, different vertex
        CHECK(!(tri == quad));     // different size

        // median() — exercise (finite point)
        auto med = tri.median();
        CHECK(std::isfinite(med.longitude()));
        CHECK(std::isfinite(med.latitude()));

        // earthWrappingPoly + collidesWith (SAT)
        auto earth = HighPrecWgs84Polygon::earthWrappingPoly();
        CHECK_EQ(earth.vertices().size(), static_cast<size_t>(4));
        CHECK(earth.collidesWith(tri)); // earth wrapper collides with everything
        CHECK(tri.collidesWith(earth));

        HighPrecWgs84Polygon overlap(
            {HighPrecWgs84(1, 1), HighPrecWgs84(5, 1), HighPrecWgs84(1, 5)});
        HighPrecWgs84Polygon apart(
            {HighPrecWgs84(20, 20), HighPrecWgs84(24, 20), HighPrecWgs84(20, 24)});
        CHECK(tri.collidesWith(overlap)); // overlapping → true
        CHECK(!tri.collidesWith(apart));  // separated → false
    }

    // ---- Wgs84AABB ----------------------------------------------------------
    {
        Wgs84AABB<double> box(HighPrecWgs84(0, 10), Vec2(20.0, 10.0));
        CHECK(box.valid());
        CHECK_NEAR(box.sw().longitude(), 0.0, 1e-9);
        CHECK_NEAR(box.sw().latitude(), 10.0, 1e-9);
        CHECK_NEAR(box.ne().longitude(), 20.0, 1e-9);
        CHECK_NEAR(box.ne().latitude(), 20.0, 1e-9);
        CHECK_NEAR(box.se().longitude(), 20.0, 1e-9);
        CHECK_NEAR(box.nw().latitude(), 20.0, 1e-9);
        CHECK_NEAR(box.center().longitude(), 10.0, 1e-9);
        CHECK_NEAR(box.center().latitude(), 15.0, 1e-9);
        CHECK_EQ(box.vertices().size(), static_cast<size_t>(4));
        CHECK_NEAR(box.size().x, 20.0, 1e-9);

        CHECK(box.contains(HighPrecWgs84(5, 15)));
        CHECK(!box.contains(HighPrecWgs84(50, 50)));

        CHECK(box.numTileIds(5) > 0u);
        CHECK(box.tileLevel(8) <= 15);

        // avgMercatorStretch is non-const; result must be finite.
        Wgs84AABB<double> box2 = box;
        CHECK(std::isfinite(box2.avgMercatorStretch()));

        // Overlapping boxes intersect (a corner of `over` lies in `box`).
        Wgs84AABB<double> over(HighPrecWgs84(10, 15), Vec2(20.0, 10.0));
        CHECK(box.intersects(over));

        // Disjoint boxes do not intersect — and must not recurse forever.
        Wgs84AABB<double> faraway(HighPrecWgs84(100, 60), Vec2(5.0, 5.0));
        CHECK(!box.intersects(faraway));
        CHECK(!faraway.intersects(box)); // symmetric

        // Cross-shaped overlap: neither box holds a corner of the other, yet
        // they overlap (x in [8,10], y in [14,16]). The old corner test missed
        // this and recursed; the interval test reports the true intersection.
        Wgs84AABB<double> wide(HighPrecWgs84(-5, 14), Vec2(40.0, 2.0));
        Wgs84AABB<double> tall(HighPrecWgs84(8, 0), Vec2(2.0, 40.0));
        CHECK(wide.intersects(tall));
        CHECK(tall.intersects(wide));

        CHECK(!box.containsAntiMeridian());

        // A box straddling +180° splits into two normalized halves.
        Wgs84AABB<double> am(HighPrecWgs84(175, 0), Vec2(10.0, 5.0));
        CHECK(am.containsAntiMeridian());
        auto split = am.splitOverAntiMeridian();
        CHECK(split.first.size().x > 0.0);
        CHECK(split.second.size().x > 0.0);

        // Constructed from a tile, from center+limit, and default.
        Wgs84AABB<double> tileBox(PackedTileId::fromTileIndex(0, 10));
        CHECK(tileBox.valid());
        CHECK(tileBox.size().x > 0.0);

        auto cbox = Wgs84AABB<double>::fromCenterAndTileLimit(HighPrecWgs84(0, 0), 16u, 10);
        CHECK(cbox.size().x > 0.0);

        Wgs84AABB<double> def;
        CHECK(def.valid());
    }

    // ---- PolygonTriangulation (ear clipping) -------------------------------
    {
        PolygonTriangulation tri;

        // Fewer than 3 vertices → UNKNOWN.
        HighPrecWgs84Polygon tooFew({HighPrecWgs84(0, 0), HighPrecWgs84(1, 0)});
        CHECK(tri.triangulateByEarClipping(tooFew).type() == HighPrecWgs84Polygon::UNKNOWN);

        // Wrong polygon type → UNKNOWN.
        HighPrecWgs84Polygon notSimple(
            HighPrecWgs84Polygon::TRIANGLE_LIST,
            {HighPrecWgs84(0, 0), HighPrecWgs84(4, 0), HighPrecWgs84(0, 4)});
        CHECK(tri.triangulateByEarClipping(notSimple).type() == HighPrecWgs84Polygon::UNKNOWN);

        // Exactly 3 vertices → unchanged TRIANGLE_LIST.
        HighPrecWgs84Polygon triangle(
            {HighPrecWgs84(0, 0), HighPrecWgs84(4, 0), HighPrecWgs84(0, 4)});
        auto rt = tri.triangulateByEarClipping(triangle);
        CHECK(rt.type() == HighPrecWgs84Polygon::TRIANGLE_LIST);
        CHECK_EQ(rt.vertices().size(), static_cast<size_t>(3));

        // Convex quad (CCW) → 2 triangles.
        HighPrecWgs84Polygon quad(
            {HighPrecWgs84(0, 0), HighPrecWgs84(4, 0), HighPrecWgs84(4, 4), HighPrecWgs84(0, 4)});
        auto rq = tri.triangulateByEarClipping(quad);
        CHECK(rq.type() == HighPrecWgs84Polygon::TRIANGLE_LIST);
        CHECK_EQ(rq.vertices().size(), static_cast<size_t>(6));

        // Concave polygon with a reflex vertex (2,2) → 3 triangles; exercises
        // the non-convex / isInside() == true paths in updateVertex().
        HighPrecWgs84Polygon concave({HighPrecWgs84(0, 0), HighPrecWgs84(4, 0), HighPrecWgs84(4, 4),
                                      HighPrecWgs84(2, 2), HighPrecWgs84(0, 4)});
        auto rc = tri.triangulateByEarClipping(concave);
        CHECK(rc.type() == HighPrecWgs84Polygon::TRIANGLE_LIST);
        CHECK_EQ(rc.vertices().size(), static_cast<size_t>(9));
    }

    return TEST_SUMMARY();
}
