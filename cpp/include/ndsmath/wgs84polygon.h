// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include "wgs84.h"
#include "wgs84aabb.h"
#include "polygon.h"

#include <glm/vec2.hpp>
#include <glm/geometric.hpp>
#include <limits>
#include <vector>
#include <algorithm>
#include <numeric>

namespace ndsmath
{

//! Representation of a polygon with the use of the `Polygon` class and the high precision version
//! of `Wgs84<T>`. Introduces additional methods for collision and bounding box handling.
struct HighPrecWgs84Polygon : public Polygon<std::vector<HighPrecWgs84>>
{
    using PolyBase = Polygon<std::vector<HighPrecWgs84>>;

    HighPrecWgs84Polygon() : PolyBase(SIMPLE_POLYGON) {}

    HighPrecWgs84Polygon(const std::vector<HighPrecWgs84> &verts) : PolyBase(SIMPLE_POLYGON, verts)
    {
    }

    //! Constructor.
    HighPrecWgs84Polygon(PolygonType polygonType) : PolyBase(polygonType) {}

    //! Constructor with vertices
    HighPrecWgs84Polygon(PolygonType polygonType, const std::vector<HighPrecWgs84> &vertices)
        : PolyBase(polygonType, vertices)
    {
    }

    static HighPrecWgs84Polygon earthWrappingPoly()
    {
        return {{HighPrecWgs84{-180., -90.}, HighPrecWgs84{-180., 90.}, HighPrecWgs84{180., -90.},
                 HighPrecWgs84{180., 90.}}};
    }

    bool isValid() const override { return vertices_.size() >= 3; }

    bool collidesWith(const HighPrecWgs84Polygon &other) const
    {
        static const auto earthWrapper = earthWrappingPoly();
        if (*this == earthWrapper || other == earthWrapper)
            return true;
        if (areSeparate(other, *this))
            return false;
        if (areSeparate(other, other))
            return false;
        return true;
    }

    // Returns axis-aligned bounding box top-left, bottom-right,
    // empty vector if this polygon is invalid
    Wgs84AABB<typename HighPrecWgs84::prec> aaBb() const
    {
        if (isValid())
        {
            using wgsT = decltype(vertices_[0]);

            auto compLon = [](wgsT &f, wgsT &s) { return f.longitude() < s.longitude(); };
            auto minLon =
                (*std::min_element(vertices_.begin(), vertices_.end(), compLon)).longitude();
            auto maxLon =
                (*std::max_element(vertices_.begin(), vertices_.end(), compLon)).longitude();

            auto compLat = [](wgsT &f, wgsT &s) { return f.latitude() < s.latitude(); };
            auto minLat =
                (*std::min_element(vertices_.begin(), vertices_.end(), compLat)).latitude();
            auto maxLat =
                (*std::max_element(vertices_.begin(), vertices_.end(), compLat)).latitude();

            return {HighPrecWgs84{minLon, minLat},
                    typename HighPrecWgs84::vec2_t{maxLon - minLon, maxLat - minLat}};
        }
        return {};
    }

    bool operator==(const HighPrecWgs84Polygon &other) const
    {
        const auto &v = vertices_;
        const auto &vo = other.vertices_;

        if (v.size() != vo.size())
            return false;
        for (int i = 0; i < v.size(); ++i)
        {
            if (v[i] != vo[i])
                return false;
        }
        return true;
    }

    HighPrecWgs84 median() const
    {
        auto addLat = [this](double s, const HighPrecWgs84 &p)
        { return s + p.latitude() / vertices_.size(); };
        auto medLat = std::accumulate(vertices_.begin(), vertices_.end(), 0., addLat);
        auto addLon = [this](double s, const HighPrecWgs84 &p)
        { return s + p.longitude() / vertices_.size(); };
        auto medLon = std::accumulate(vertices_.begin(), vertices_.end(), 0., addLon);
        return HighPrecWgs84(medLat, medLon);
    }

private:
    // TODO: HighPrecWgs84 are already glm::dvec2 :)
    using Vec2 = glm::dvec2;

    Vec2 projectOnAxis(const HighPrecWgs84Polygon &poly, const Vec2 &axis) const
    {
        auto min = std::numeric_limits<double>::max();
        auto max = std::numeric_limits<double>::lowest();

        auto &vs = poly.vertices_;
        for (int i = 0; i < vs.size(); ++i)
        {
            auto nI = i + 1 == vs.size() ? 0 : i + 1;
            auto beg = Vec2(vs[i].longitude(), vs[i].latitude());
            auto end = Vec2(vs[nI].longitude(), vs[nI].latitude());

            auto x0 = glm::dot(beg, axis);
            if (x0 < min)
                min = x0;
            if (x0 > max)
                max = x0;

            auto x1 = x0 + glm::dot(end - beg, axis);
            if (x1 < min)
                min = x1;
            if (x1 > max)
                max = x1;
        }
        return Vec2(min, max);
    }

    bool areSeparate1d(const Vec2 &minMax1, const Vec2 &minMax2) const
    {
        return (minMax1.x < minMax2.x && minMax1.y < minMax2.x) ||
               (minMax1.x > minMax2.y && minMax1.y > minMax2.y);
    }

    bool areSeparate(const HighPrecWgs84Polygon &other,
                     const HighPrecWgs84Polygon &refForAxis) const
    {
        auto &vs = refForAxis.vertices_;
        for (int i = 0; i < vs.size(); ++i)
        {
            auto nI = i + 1 == vs.size() ? 0 : i + 1;
            auto d = Vec2(vs[nI].longitude(), vs[nI].latitude()) -
                     Vec2(vs[i].longitude(), vs[i].latitude());
            auto normal = Vec2(d.y, -d.x);

            auto minMaxPoly1 = projectOnAxis(*this, normal);
            auto minMaxPoly2 = projectOnAxis(other, normal);

            if (areSeparate1d(minMaxPoly1, minMaxPoly2))
                return true;
        }
        return false;
    }
};

} // namespace ndsmath
