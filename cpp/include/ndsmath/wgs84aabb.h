// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include <utility>
#include <list>
#include <vector>
#include <functional>

#include "wgs84.h"
#include "packedtileid.h"

namespace ndsmath {

//! Template class representing a WGS84 axis-aligned bounding box.
template<typename T>
class Wgs84AABB
{
public:
    using vec2_t = typename Wgs84<T>::vec2_t;

    Wgs84AABB() = default;
    Wgs84AABB(Wgs84AABB const &other) = default;

    /// Construct an AABB from a position and a size.
    Wgs84AABB(Wgs84<T> const &sw, vec2_t size) : sw_(sw), size_(size) {
        if (!valid())
            return;

        auto excessHeight = 90. - sw_.latitude() - size_.y;
        if (excessHeight < 0)
            size_.y += excessHeight;
    }

    /// Construct an AABB from a PackedTileId.
    explicit Wgs84AABB(PackedTileId const& tileId)
        : Wgs84AABB(Wgs84<T>::fromMortonCode(tileId.southWestCorner()),
                    glm::abs((Wgs84<T>::fromMortonCode(tileId.southWestCorner()) -
                              Wgs84<T>::fromMortonCode(tileId.northEastCorner())).vec())) {}

    /// Construct the AABB from a center position, a tile count limit, and a tile level
    static Wgs84AABB<T> fromCenterAndTileLimit(Wgs84<T> const& center, uint32_t softLimit, uint16_t level) {
        constexpr auto targetAspectRatio = .7; // approx. height / width
        auto tileWidth = 180. / static_cast<double>(1u << level);
        auto targetSize = glm::sqrt(softLimit) * tileWidth;
        auto targetSizeVec = typename Wgs84<T>::vec2_t{
            targetSize / targetAspectRatio,
            targetSize * targetAspectRatio};
        return Wgs84AABB<T>(center - targetSizeVec * .5, targetSizeVec);
    }

    /// Determine, whether the AABBs size is within reasonable bounds.
    inline bool valid() const {
        return size_.x >= 0 && size_.y >= 0 && size_.x <= 360. && size_.y <= 180.;
    }

    /// Obtain the South-West corner of this AABB.
    inline Wgs84<T> const &sw() const {
        return sw_;
    }

    /// Obtain the North-East corner of this AABB.
    inline Wgs84<T> ne() const {
        return sw_ + size_;
    }

    /// Obtain the North-West corner of this AABB.
    inline Wgs84<T> nw() const {
        return sw_ + vec2_t{.0, size_.y};
    }

    /// Obtain the South-East corner of this AABB.
    inline Wgs84<T> se() const {
        return sw_ + vec2_t{size_.x, .0};
    }

    /// Obtain all four vertices, one for each corner of the AABB.
    inline std::vector<Wgs84<T>> vertices() const {
        return {sw(), se(), ne(), nw()};
    }

    /// Obtain the size of this bounding box.
    inline vec2_t const& size() const {return size_;}

    /// Determine whether the horizontal extent of this bounding rect
    /// crosses the anti-meridian (lon == +/- 180°).
    inline bool containsAntiMeridian() const {
        return sw_.longitude() + size_.x > Wgs84<T>::lonMax + Wgs84<T>::lonNdsDelta;
    }

    /// Obtain the center coordinate of this AABB.
    inline Wgs84<T> center() const {
        return sw_ + size_ * .5;
    }

    /// Note: Only call if containsAntiMeridian() is true.
    /// If this bounding rect crosses the anti-meridian, obtain two normalized bounding
    /// rects, one to the right and one to the left.
    std::pair<Wgs84AABB<T>, Wgs84AABB<T>> splitOverAntiMeridian() const {
        auto widthAfterAM = sw_.longitude() + size_.x - Wgs84<T>::lonMax;
        if (widthAfterAM > 0) {
            auto widthBeforeAM = size_.x - widthAfterAM;
            return {
               Wgs84AABB<T>{sw_,                                        {widthBeforeAM, size_.y}},
               Wgs84AABB<T>{Wgs84<T>{Wgs84<T>::lonMin, sw_.latitude()}, {widthAfterAM,  size_.y}},
            };
        }
        return {};
    }

    /// Calculate the mercator-projection vertical stretch factor.
    inline double avgMercatorStretch() {
        T const latTop = glm::radians(sw_.latitude() + size_.y);
        T const latBottom = glm::radians(sw_.latitude());
        auto radToMercatorLat = [](T wgs84Lat){return atanh(sin(wgs84Lat - M_PI_2));};
        return (radToMercatorLat(latTop) - radToMercatorLat(latBottom))/glm::radians(size_.y);
    }

    /// Obtain the number of tiles for the given level contained in this AABB.
    ///  Note: The number returned is approximate; the actual tile count returned
    ///  by tileIdsWithPriority might still be a bit higher if the viewport is slightly
    ///  shifted (one additional row/column + 1 corner).
    inline uint32_t numTileIds(uint32_t lv) const {
        T const tileWidth = 180. / static_cast<float>(1u << lv);
        auto const tilesPerDim = glm::ceil(size_ / tileWidth);
        return static_cast<uint32_t>(tilesPerDim.x * tilesPerDim.y);
    }

    /// Obtain the first tile level for this bounding box, for which
    /// a certain minimum number of tiles would be contained.
    inline uint8_t tileLevel(uint32_t minNumTiles=8) const {
        for (uint8_t resultTileLevel = 0; resultTileLevel <= 15 ; ++resultTileLevel) {
            if (numTileIds(resultTileLevel) >= minNumTiles)
                return resultTileLevel;
        }
        return 15;
    }

    /// Determine whether this bounding rect contains the given point
    inline bool contains(Wgs84<T> const& point) const {
        return
            point.longitude() >= sw_.longitude() &&
            point.longitude() <= sw_.longitude() + size_.x &&
            point.latitude() >= sw_.latitude() &&
            point.latitude() <= sw_.latitude() + size_.y;
    }

    /// Determine whether this bounding rect has an intersection with another bounding rect.
    inline bool intersects(Wgs84AABB<T> const& other) const {
        return
            contains(other.sw()) || contains(other.ne()) ||
            contains(other.se()) || contains(other.nw()) ||
            other.intersects(*this);
    }

private:
    Wgs84<T> sw_{.0, .0};
    vec2_t size_{.0, .0};
};


using HighPrecWgs84AABB = Wgs84AABB<double>;

}
