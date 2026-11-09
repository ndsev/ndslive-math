// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include <limits>
#include <cstdint>

namespace ndsmath
{

// Forward declarations.
template <typename T = double> class Wgs84;

//! Class representing a morton code and providing some methods
//! to convert a morton code. This class does not produce any
//! overhead compared to the usage of a uint64_t as morton code.
class MortonCode
{
public:
    MortonCode(uint64_t mortonCode) : mortonCode_(mortonCode) {}

    //! Get the morton code.
    inline uint64_t value() const { return mortonCode_; }

    //! Convert morton code to nds coordinates.
    inline void toNdsCoordinates(int32_t &x, int32_t &y) const
    {
        const int32_t YBASE = (1ULL << 30);

        int32_t bit = 1;
        uint64_t mortonCode = mortonCode_;

        x = 0;
        y = 0;

        for (int i = 0; i < 31; i++)
        {
            x |= mortonCode & bit;
            mortonCode >>= 1;
            y |= mortonCode & bit;
            bit <<= 1;
        }

        x |= mortonCode & bit;
        mortonCode >>= 1;

        if (y >= YBASE)
        {
            y -= (1ULL << 31);
        }

        // x already holds a signed int32: the loop fills all 32 bits, so bit 31
        // is the sign bit and needs no further adjustment (unlike the 31-bit y,
        // which is a magnitude that must be sign-extended above).
    }

    //! Wrap X to signed 32 bits and Y to signed 31 bits, then interleave them.
    //! The encoded value uses 63 bits; bit 63 is cleared.
    static MortonCode fromNdsCoordinates(int64_t x, int64_t y)
    {
        const int64_t xBase = (1ULL << 31);
        const int64_t yBase = (1ULL << 30);

        int64_t bit = 1;
        uint64_t mortonCode = 0;

        while (x >= xBase)
            x -= (1ULL << 32);

        while (x < -xBase)
            x += (1ULL << 32);

        while (y >= yBase)
            y -= (1ULL << 31);

        while (y < -yBase)
            y += (1ULL << 31);

        y <<= 1;

        for (int i = 0; i < 31; i++)
        {
            mortonCode |= x & bit;
            x <<= 1;
            bit <<= 1;

            mortonCode |= y & bit;
            y <<= 1;
            bit <<= 1;
        }
        mortonCode |= x & bit;
        x <<= 1;
        bit <<= 1;
        mortonCode &= ~(1ULL << 63);

        return MortonCode(mortonCode);
    }

    //! Convert WGS84 degrees by truncating NDS coordinates toward zero.
    //! For floor-based conversion, call Wgs84::toNdsCoordinates followed by
    //! fromNdsCoordinates. This overload is defined out of line to avoid a cycle.
    static MortonCode fromWgs84Coordinates(const Wgs84<double> &wgs84);

private:
    //! Value.
    uint64_t mortonCode_;

}; // class MortonCode

} // namespace ndsmath
