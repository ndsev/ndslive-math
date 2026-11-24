// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <glm/vec2.hpp>
#include <limits>
#include <vector>

namespace ndsmath
{
/** Relation of a closed rectangle to a polygon with open hole interiors. */
enum class PolygonAreaRelation
{
    Outside,
    Inside,
    Boundary
};

/** Raw planar rings; callers unwrap geographic coordinates before querying. */
using PlanarRing = std::vector<glm::dvec2>;

namespace polygon_area_detail
{
/** Exact low/high representation of a difference. */
inline std::array<double, 2> difference(double a, double b)
{
    auto high = a - b;
    auto virtualB = a - high;
    return {(a - (high + virtualB)) + (virtualB - b), high};
}

/** Add a scalar to a nonoverlapping floating-point expansion without losing bits. */
inline void grow(std::vector<double> &expansion, double value)
{
    size_t count = 0;
    for (auto term : expansion)
    {
        auto total = value + term;
        auto virtualTerm = total - value;
        auto low = (value - (total - virtualTerm)) + (term - virtualTerm);
        if (low != 0)
            expansion[count++] = low;
        value = total;
    }
    expansion.resize(count);
    if (value != 0)
        expansion.push_back(value);
}

/** Orientation sign, with an exact expansion fallback for ambiguous determinants. */
inline double cross(glm::dvec2 a, glm::dvec2 b, glm::dvec2 c)
{
    auto left = (b.x - a.x) * (c.y - a.y), right = (b.y - a.y) * (c.x - a.x);
    auto determinant = left - right;
    if (std::abs(determinant) >
        (std::abs(left) + std::abs(right)) * 8 * std::numeric_limits<double>::epsilon())
        return determinant;
    std::vector<double> expansion;
    expansion.reserve(16);
    for (auto sign : {1., -1.})
    {
        auto x = sign > 0 ? difference(b.x, a.x) : difference(b.y, a.y);
        auto y = sign > 0 ? difference(c.y, a.y) : difference(c.x, a.x);
        for (auto u : x)
            for (auto v : y)
            {
                auto high = u * v;
                grow(expansion, sign * std::fma(u, v, -high));
                grow(expansion, sign * high);
            }
    }
    return expansion.empty() ? 0 : expansion.back();
}

/** Closed segment membership, including its two endpoints. */
inline bool onSegment(glm::dvec2 p, glm::dvec2 a, glm::dvec2 b)
{
    return cross(a, b, p) == 0.0 && p.x >= std::min(a.x, b.x) && p.x <= std::max(a.x, b.x) &&
           p.y >= std::min(a.y, b.y) && p.y <= std::max(a.y, b.y);
}

/** Closed segment intersection, including collinear contact. */
inline bool intersects(glm::dvec2 a, glm::dvec2 b, glm::dvec2 c, glm::dvec2 d)
{
    auto abC = cross(a, b, c), abD = cross(a, b, d);
    auto cdA = cross(c, d, a), cdB = cross(c, d, b);
    return (((abC < 0 && abD > 0) || (abC > 0 && abD < 0)) &&
            ((cdA < 0 && cdB > 0) || (cdA > 0 && cdB < 0))) ||
           onSegment(a, c, d) || onSegment(b, c, d) || onSegment(c, a, b) || onSegment(d, a, b);
}

/** Ignore a conventional repeated closing vertex. */
template <class Ring> inline size_t ringSize(Ring const &ring)
{
    return ring.size() > 1 && ring.front() == ring.back() ? ring.size() - 1 : ring.size();
}

/** Even/odd containment; boundary points belong to the closed ring. */
inline bool contains(PlanarRing const &ring, glm::dvec2 point)
{
    bool inside = false;
    auto n = ringSize(ring);
    for (size_t i = 0; i < n; ++i)
    {
        auto a = ring[i], b = ring[(i + 1) % n];
        if (onSegment(point, a, b))
            return true;
        if ((a.y > point.y) != (b.y > point.y) && (cross(a, b, point) > 0) == (b.y > a.y))
            inside = !inside;
    }
    return inside;
}

/** Detect contact between two ring boundaries. */
template <class LeftRing, class RightRing>
inline bool ringsIntersect(LeftRing const &a, RightRing const &b)
{
    auto na = ringSize(a), nb = ringSize(b);
    for (size_t i = 0; i < na; ++i)
        for (size_t j = 0; j < nb; ++j)
            if (intersects(a[i], a[(i + 1) % na], b[j], b[(j + 1) % nb]))
                return true;
    return false;
}

/** Validate finite, nondegenerate simple rings without changing winding. */
inline bool validRing(PlanarRing const &ring)
{
    auto n = ringSize(ring);
    if (n < 3)
        return false;
    bool noncollinear = false;
    for (size_t i = 0; i < n; ++i)
    {
        auto a = ring[i], b = ring[(i + 1) % n];
        if (!std::isfinite(a.x) || !std::isfinite(a.y) || a == b)
            return false;
        auto previous = ring[(i + n - 1) % n];
        auto turn = cross(previous, a, b);
        if (!std::isfinite(turn) || (turn == 0 && !onSegment(a, previous, b)))
            return false;
        // A simple ring with a non-collinear turn has nonzero area. Absolute
        // shoelace products can cancel even for a valid one-NDS-unit square.
        noncollinear |= turn != 0;
        for (size_t j = i + 1; j < n; ++j)
        {
            if (j == i + 1 || (i == 0 && j == n - 1))
                continue;
            if (intersects(a, b, ring[j], ring[(j + 1) % n]))
                return false;
        }
    }
    return noncollinear;
}
} // namespace polygon_area_detail

/** Validate a simple exterior and disjoint, strictly interior holes. */
inline bool validPolygonArea(PlanarRing const &exterior, std::vector<PlanarRing> const &holes = {})
{
    using namespace polygon_area_detail;
    if (!validRing(exterior))
        return false;
    for (size_t i = 0; i < holes.size(); ++i)
    {
        auto const &hole = holes[i];
        if (!validRing(hole) || !contains(exterior, hole.front()) || ringsIntersect(exterior, hole))
            return false;
        for (size_t j = 0; j < i; ++j)
            if (ringsIntersect(hole, holes[j]) || contains(hole, holes[j].front()) ||
                contains(holes[j], hole.front()))
                return false;
    }
    return true;
}

/** Intersect prevalidated areas, including every exterior/hole boundary.
 * Callers put both polygons in the same unwrapped coordinate plane.
 */
inline bool polygonAreasIntersect(PlanarRing const &a, std::vector<PlanarRing> const &aHoles,
                                  PlanarRing const &b, std::vector<PlanarRing> const &bHoles)
{
    using namespace polygon_area_detail;
    if (a.empty() || b.empty())
        return false;
    auto boundaryContact = [&](PlanarRing const &ring)
    {
        if (ringsIntersect(ring, b))
            return true;
        return std::any_of(bHoles.begin(), bHoles.end(),
                           [&](auto const &hole) { return ringsIntersect(ring, hole); });
    };
    if (boundaryContact(a) || std::any_of(aHoles.begin(), aHoles.end(), boundaryContact))
        return true;
    auto inside =
        [](glm::dvec2 point, PlanarRing const &exterior, std::vector<PlanarRing> const &holes)
    {
        return contains(exterior, point) &&
               std::none_of(holes.begin(), holes.end(),
                            [&](auto const &hole) { return contains(hole, point); });
    };
    return inside(a.front(), b, bHoles) || inside(b.front(), a, aHoles);
}

/** Classify a closed rectangle; exterior and hole boundary contact always counts.
 * Rings must be valid and use the same unwrapped plane as the rectangle.
 */
inline PolygonAreaRelation classifyPolygonRectangle(PlanarRing const &exterior,
                                                    std::vector<PlanarRing> const &holes,
                                                    glm::dvec2 minimum, glm::dvec2 maximum)
{
    using namespace polygon_area_detail;
    if (exterior.size() < 3 || !std::isfinite(minimum.x) || !std::isfinite(minimum.y) ||
        !std::isfinite(maximum.x) || !std::isfinite(maximum.y) || minimum.x > maximum.x ||
        minimum.y > maximum.y)
        return PolygonAreaRelation::Outside;
    std::array<glm::dvec2, 4> rectangle{minimum, glm::dvec2{maximum.x, minimum.y}, maximum,
                                        glm::dvec2{minimum.x, maximum.y}};
    auto touches = [&](PlanarRing const &ring)
    {
        for (auto p : ring)
            if (p.x >= minimum.x && p.x <= maximum.x && p.y >= minimum.y && p.y <= maximum.y)
                return true;
        return ringsIntersect(ring, rectangle);
    };
    if (touches(exterior))
        return PolygonAreaRelation::Boundary;
    for (auto const &hole : holes)
        if (touches(hole))
            return PolygonAreaRelation::Boundary;
    auto centre = (minimum + maximum) * 0.5;
    if (!contains(exterior, centre))
        return PolygonAreaRelation::Outside;
    for (auto const &hole : holes)
        if (contains(hole, centre))
            return PolygonAreaRelation::Outside;
    return PolygonAreaRelation::Inside;
}
} // namespace ndsmath
