// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include "mortoncode.h"
#include "consts.h"

#include <vector>
#include <sstream>

#define GLM_ENABLE_EXPERIMENTAL // glm::transform API may change in a future version
#include <glm/glm.hpp>
#include <glm/vec3.hpp>
#include <glm/ext.hpp>


namespace ndsmath
{
    class MortonCode;

    //! Template class representing WGS84 coordinates (in degrees).
    template<typename T>
    class Wgs84 : public glm::vec<2, T, glm::highp>
    {
    public:
        using vec2_t = typename glm::vec<2, T, glm::highp>;
        using prec = T;

        static constexpr T lonNdsDelta = static_cast<T>(360.) / static_cast<T>( (2ll << 32) - 1 );
        static constexpr T latNdsDelta = static_cast<T>(180.) / static_cast<T>( (2ll << 31) - 1 );
        static constexpr T lonMin = static_cast<T>(-180.);
        static constexpr T lonMax = static_cast<T>(180.) - lonNdsDelta;
        static constexpr T latMin = static_cast<T>(-90.);
        static constexpr T latMax = static_cast<T>(90. - latNdsDelta);

        using vec2_t::x;
        using vec2_t::y;

    public:
        Wgs84() : vec2_t (0, 0) {}

        template<typename TypeWithXY>
        requires requires(TypeWithXY t) {
            { t.x } -> std::convertible_to<double>;
            { t.y } -> std::convertible_to<double>;
        }
        explicit Wgs84(TypeWithXY const& other) : Wgs84(other.x, other.y) {}

        Wgs84(T longitude, T latitude) : vec2_t(longitude, latitude) {
            normalize();
        }

    public:
        operator vec2_t const& () const {
            return *this;
        }

        inline vec2_t const& vec() const {
            return *this;
        }

        inline T const& longitude() const
        {
            return x;
        }

        inline T const& latitude() const
        {
            return y;
        }

        inline T const& dx() const
        {
            return x;
        }

        inline T const& dy() const
        {
            return y;
        }

        //! Returns wgs in degree/minutes/seconds. First value is latitude, second is longitude.
        std::pair<std::string, std::string> toDegreeMinutesSeconds() const
        {
            std::pair<std::string, std::string> result;

            result.first = toDegreeMinutesSeconds(std::abs(y)) + ((y < 0) ? "S" : "N");
            result.second = toDegreeMinutesSeconds(std::abs(x)) + ((x < 0) ? "W" : "E");

            return result;
        }

        //! Convert WGS84 coordinates to NDS integer coordinates.
        //! @note NDS spec allows floor, truncate, or round operations for this conversion.
        //!       Floor is used here as recommended by NDS for consistency with the tiling scheme.
        void toNdsCoordinates(int32_t &xOut, int32_t &yOut) const
        {
            xOut = static_cast<int32_t>(std::floor((x / 360.0) * std::ldexp(1.0, 32)));
            yOut = static_cast<int32_t>(std::floor((y / 180.0) * std::ldexp(1.0, 31)));
        }

        //! Distance to another wgs coordinate in meters.
        T distanceTo(const Wgs84 &other) const
        {
            const double dLat = glm::radians(other.latitude() - y);
            const double dLon = glm::radians(other.longitude() - x);
            const double a = glm::sin(dLat * 0.5) *
                             glm::sin(dLat * 0.5) + glm::cos(glm::radians(y)) *
                                                    glm::cos(glm::radians(other.latitude())) *
                                                    glm::sin(dLon * 0.5) *
                                                    glm::sin(dLon * 0.5);
            const double c = 2 * glm::atan(glm::sqrt(a), glm::sqrt(1 - a));
            return static_cast<T>(EARTH_RADIUS_IN_METERS * c);
        }

        T bearingFrom(const Wgs84 &other) const
        {
            const T lat1f = glm::radians(y);
            const T lon1f = glm::radians(x);
            const T lat2f = glm::radians(other.latitude());
            const T lon2f = glm::radians(other.longitude());

            const T y = glm::sin(lon2f - lon1f) * glm::cos(lat2f);
            const T x = glm::cos(lat1f) * glm::sin(lat2f) - glm::sin(lat1f) * glm::cos(lat2f) * glm::cos(lon2f - lon1f);
            return glm::atan(y, x);
        }

        bool isInsidePolygon(const std::vector<Wgs84<T> > &polygon) const
        {
            bool isInside = false;
            const size_t verticeCount = polygon.size();

            if (verticeCount < 3)
            {
                return false;
            }

            size_t j = verticeCount - 1;
            for (size_t i = 0; i < verticeCount; i++)
            {
                if (((polygon[i].latitude() >= y ) != (polygon[j].latitude() >= y)) &&
                    (x <= (polygon[j].longitude() - polygon[i].longitude()) *
                          (y - polygon[i].latitude()) / (polygon[j].latitude() - polygon[i].latitude()) + polygon[i].longitude()))
                {
                    isInside = !isInside;
                }
                j = i;
            }

            return isInside;
        }

        //! x corresponds to longitude, y to latitude.
        static Wgs84 fromNdsCoordinates(int32_t x, int32_t y)
        {
            const T latMultiplier = 180.0 / std::pow(2.0, 31.0);
            const T lonMultiplier = 360.0 / std::pow(2.0, 32.0);

            return Wgs84(lonMultiplier * static_cast<T>(x), latMultiplier * static_cast<T>(y));
        }

        static Wgs84 fromMortonCode(const MortonCode &mortonCode)
        {
            const T bitScaling = 360.0 / (std::numeric_limits<uint32_t>::max() + 1.0);

            int32_t x, y;
            mortonCode.toNdsCoordinates(x, y);
            return Wgs84(static_cast<T>(x) * bitScaling, static_cast<T>(y) * bitScaling);
        }

        //! Convert degree distances to meters at a given latitude.
        //! @param lonDegrees Longitude distance in degrees
        //! @param latDegrees Latitude distance in degrees
        //! @param atLatitude The latitude where measurement is taken (affects longitude distance)
        //! @return Pair of (width_meters, height_meters)
        //! @note Longitude distance varies by latitude (shrinks toward poles), latitude distance is constant.
        static std::pair<T, T> degreesToMeters(T lonDegrees, T latDegrees, T atLatitude)
        {
            constexpr T METERS_PER_DEGREE = static_cast<T>(111320.0);

            T lonMeters = std::abs(lonDegrees) * METERS_PER_DEGREE * std::cos(glm::radians(atLatitude));
            T latMeters = std::abs(latDegrees) * METERS_PER_DEGREE;

            return {lonMeters, latMeters};
        }

        //! Convert NDS coordinate distances to meters at a given latitude.
        //! @param ndsXDistance X (longitude) distance in NDS units
        //! @param ndsYDistance Y (latitude) distance in NDS units
        //! @param atLatitude The latitude where measurement is taken
        //! @return Pair of (width_meters, height_meters)
        static std::pair<T, T> ndsDistanceToMeters(int32_t ndsXDistance, int32_t ndsYDistance, T atLatitude)
        {
            T lonDegrees = (static_cast<T>(ndsXDistance) / std::pow(2.0, 32.0)) * 360.0;
            T latDegrees = (static_cast<T>(ndsYDistance) / std::pow(2.0, 31.0)) * 180.0;

            return degreesToMeters(lonDegrees, latDegrees, atLatitude);
        }

        glm::dvec3 toEuclidean(T refRadius = EARTH_RADIUS_IN_METERS) const
        {
            const T theta = y * glm::pi<double>() / 180.;
            const T phi = x * glm::pi<double>() / 180.;
            return { refRadius * std::cos(theta) * std::sin(phi),
                     refRadius * std::sin(theta),
                     refRadius * std::cos(theta) * std::cos(phi)
            };
        }

        Wgs84<T>& move(T distanceInMeters, T bearing)
        {
            T latitudeInRad = glm::radians(y);
            T longitudeInRad = glm::radians(x);
            T angularDistance = distanceInMeters / EARTH_RADIUS_IN_METERS;

            T lat = glm::asin(
                glm::sin(latitudeInRad) * glm::cos(angularDistance) +
                glm::cos(latitudeInRad) * glm::sin(angularDistance) * glm::cos(bearing)
            );

            T dlon = glm::atan(
                glm::sin(bearing) * glm::sin(angularDistance) * glm::cos(latitudeInRad),
                glm::cos(angularDistance) - glm::sin(latitudeInRad) * glm::sin(lat)
            );

            T lon = longitudeInRad + dlon + glm::pi<T>();

            while (lon > glm::two_pi<T>()) lon -= (glm::two_pi<T>());

            y = glm::degrees(lat);
            x = glm::degrees(lon - glm::pi<T>());

            return *this;
        }

        Wgs84<T> normal(Wgs84 const& from, T distanceInMeters=static_cast<T>(1.)) const {
            auto bearing = bearingFrom(from);
            auto result = *this; // create a copy of this location
            auto orthogonalBearing = bearing + glm::half_pi<T>();
            result.move(distanceInMeters, orthogonalBearing);
            return result - *this;
        }

        bool operator==(const typename Wgs84<T>::vec2_t& other) const
        {
            auto cmp = [](double a, double b) {
                return std::abs(a - b) * 1000000000000.0 <= std::min<double>(std::abs(a), std::abs(b));
            };

            return cmp(x, other.x) &&
                   cmp(y, other.y);
        }

        bool operator !=(const typename Wgs84<T>::vec2_t& other) const
        {
            return !(*this == other);
        }

        Wgs84<T>& operator +=(const typename Wgs84<T>::vec2_t& other) {
            y += other.y;
            x += other.x;
            normalize();
            return *this;
        }

        Wgs84<T> operator + (const typename Wgs84<T>::vec2_t& other) const {
            return Wgs84<T>{x + other.x, y + other.y};
        }

        Wgs84<T>& operator -=(const typename Wgs84<T>::vec2_t& other) {
            y -= other.y;
            x -= other.x;
            normalize();
            return *this;
        }

        Wgs84<T> operator - (const typename Wgs84<T>::vec2_t& other) const {
            return Wgs84<T>{x - other.x, y - other.y};
        }

        Wgs84<T>& operator *=(const typename Wgs84<T>::vec2_t& other) {
            y *= other.y;
            x *= other.x;
            normalize();
            return *this;
        }

        Wgs84<T> operator * (const typename Wgs84<T>::vec2_t& other) const {
            return {x * other.x, y * other.y};
        }

        Wgs84<T>& operator /=(const typename Wgs84<T>::vec2_t& other) {
            y /= other.y;
            x /= other.x;
            normalize();
            return *this;
        }

        Wgs84<T> operator / (const typename Wgs84<T>::vec2_t & other) const {
            return {x / other.x, y / other.y};
        }

        bool isNull() const
        {
            return Wgs84<T>(x, y) == Wgs84<T>();
        }

    private:
        std::string toDegreeMinutesSeconds(float value) const
        {
            std::stringstream result;
            float fullDegree = std::floor(value);
            result << static_cast<int>(fullDegree) << "°";
            float tempMinutes = (value - fullDegree) * 60.0;
            result << static_cast<int>(std::floor(tempMinutes)) << "'";
            float tempSeconds = (tempMinutes - std::floor(tempMinutes)) * 60;
            std::stringstream secondsStream;
            secondsStream.precision(2);
            secondsStream << std::fixed << tempSeconds;
            std::string seconds = secondsStream.str();
            seconds.erase(seconds.find_last_not_of('0') + 1, std::string::npos);
            seconds.erase(seconds.find_last_not_of('.') + 1, std::string::npos);
            result << seconds << "\"";
            return result.str();
        }

        void normalize()
        {
            // Use modulo to prevent (almost) endless loops.
            x = std::fmod(x, 360.0);

            if (std::isnan(y) || std::isnan(x)) {
                y = .0;
                x = .0;
            } else {
                while (true)
                {
                    // Gracefully allow a longitude close enough to 180 to mean "rightmost"
                    if (std::abs(x - lonMax) < lonNdsDelta) {
                        x = lonMax;
                        break;
                    }

                    if(x < lonMin)
                        x += 360.0;
                    else if(x > lonMax)
                        x -= 360.0;
                    else
                        break;
                }

                while (true)
                {
                    if (std::abs(y - latMax) < latNdsDelta) {
                        y = latMax;
                        break;
                    }

                    if (y > latMax)
                        y = latMax - y;
                    else if (y < latMin)
                        y = latMin - y;
                    else
                        break;

                    if (x > 0.0)
                        x -= lonMax;
                    else
                        x += lonMax;
                }
            }
        }

    }; // class Wgs84

    //! Type alias for distance measurements in meters (width, height)
    template<typename T>
    using DeltaInMeters = std::pair<T, T>;

    using HighPrecWgs84 = Wgs84<double>;
    using HighPrecWgs84_3d = glm::dvec3;

} // namespace ndsmath
