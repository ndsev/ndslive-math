// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include <utility>
#include <list>
#include <vector>
#include <functional>

#include "wgs84.h"
#include "packedtileid.h"

namespace ndsmath {

/// Function which returns a priority penalty value for a tile
using TilePriorityFn = std::function<double(PackedTileId const&)>;

/**
 * @brief Wgs84AABB Wgs84 axis-aligned bounding box.
 *
 */
template<typename T>
class Wgs84AABB
{
public:
    using vec2_t = typename Wgs84<T>::vec2_t;

    Wgs84AABB() = default;
    Wgs84AABB(Wgs84AABB const &other) = default;

    /// Construct an AABB from a position and a size.
    Wgs84AABB(Wgs84<T> const &sw, vec2_t size) : sw_(sw), size_(size) {
        /* FIXME: Replace with: NDSAFW_COND_WARNING_AND_RETURN(..., "Attempt to construct Wgs84 AABB with invalid size %1*%2") */
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
    ///  rects, one to the right and one to the left.
    std::pair<Wgs84AABB<T>, Wgs84AABB<T>> splitOverAntiMeridian() const {
        auto widthAfterAM = sw_.longitude() + size_.x - Wgs84<T>::lonMax;
        if (widthAfterAM > 0) {
            auto widthBeforeAM = size_.x - widthAfterAM;
            return {
               Wgs84AABB<T>{sw_,                                        {widthBeforeAM, size_.y}},
               Wgs84AABB<T>{Wgs84<T>{Wgs84<T>::lonMin, sw_.latitude()}, {widthAfterAM,  size_.y}},
            };
        } else
            NDSAFW_WARNING("Attempt to split AABB over anti-meridian which does not contain it.");
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

    /// Obtain all TileIds for a given tile level. Note: The tiles will be sorted
    ///  by the given penalty distribution function ().
    std::list<std::pair<PackedTileId, double>> tileIdsWithPriority(
        uint32_t const& level,
        std::function<double(PackedTileId const&)> const& tilePenaltyFun = {},
        uint32_t limit = 0) const
    {
        std::list<std::pair<PackedTileId, double>> result;

        if (containsAntiMeridian()) {
            auto normalizedViewports = splitOverAntiMeridian();
            NDSAFW_ASSERT(
                !normalizedViewports.first.containsAntiMeridian() &&
                !normalizedViewports.second.containsAntiMeridian());
            auto right = normalizedViewports.first.tileIdsWithPriority(level, tilePenaltyFun, limit);
            auto left = normalizedViewports.second.tileIdsWithPriority(level, tilePenaltyFun, limit);

            // Merge left/right result sets
            auto rit = right.begin(), lit = left.begin();
            while (result.size() < limit) {
                if (rit != right.end() && lit != left.end()) {
                    if (rit->second < lit->second)
                        result.push_back(*(rit++));
                    else
                        result.push_back(*(lit++));
                }
                else if (rit != right.end())
                    result.push_back(*(rit++));
                else if (lit != left.end())
                    result.push_back(*(lit++));
                else
                    break;
            }

            return result;
        }

        const int64_t tileWidth = 1u << (31 - level);
        int32_t minX, minY, maxX, maxY;
        sw_.toNdsCoordinates(minX, minY);
        ne().toNdsCoordinates(maxX, maxY);
        if ((minX % tileWidth) == 0)
            minX += 1;
        if ((minY % tileWidth) == 0)
            minY += 1;

        int64_t x = minX;
        while (x <= maxX && x < std::numeric_limits<int32_t>::max()) {
            int64_t y = minY;
            while (y <= maxY && y < std::numeric_limits<int32_t>::max()) {
                auto tid = PackedTileId(MortonCode::fromNdsCoordinates(x, y), (int)level);
                auto penalty = tilePenaltyFun ? tilePenaltyFun(tid) : .0;
                auto it = std::lower_bound(
                    result.begin(),
                    result.end(),
                    penalty,
                    [](auto const& lhs, auto const& rhs) {
                        return lhs.second < rhs;
                    });
                if (it == result.end() || it->first != tid)
                    result.insert(it, {tid, penalty});
                if (limit && result.size() > limit)
                    result.pop_back();
                y += glm::min(tileWidth,  glm::max(static_cast<int64_t>(maxY) - y, static_cast<int64_t>(1)));
            }
            x += glm::min(tileWidth, glm::max(static_cast<int64_t>(maxX) - x, static_cast<int64_t>(1)));
        }

        return result;
    }

    /// Same as tileIdsWithPriority, but strips the priority values
    ///  and converts the linked list to a vector.
    PackedTileIds tileIds(
        uint32_t const& level,
        std::function<double(PackedTileId const&)> const& tilePenaltyFun = {},
        uint32_t limit = 0) const
    {
        auto resultList = tileIdsWithPriority(level, tilePenaltyFun, limit);
        PackedTileIds result;
        result.reserve(resultList.size());
        for (auto const& [tid, _] : resultList)
            result.emplace_back(tid);
        return result;
    }

private:
    Wgs84<T> sw_{.0, .0};
    vec2_t size_{.0, .0};
};


using HighPrecWgs84AABB = Wgs84AABB<double>;

}
