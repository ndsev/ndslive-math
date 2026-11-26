// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace ndsmath::detail
{
//! Exact sum of signed coordinate products when the floating-point area has an uncertain sign.
//! A binary coordinate has only a few nonzero base-2^16 digits. Accumulating their products
//! separately also handles subnormal coordinates without a multiprecision dependency.
template <typename F> class ExactArea
{
    using Limits = std::numeric_limits<F>;
    static constexpr int digitBits = 16, base = 1 << digitBits;
    static constexpr int minExponent = Limits::min_exponent - Limits::digits;
    // Two products per edge, and at most SIZE_MAX edges.
    static constexpr int bits =
        2 * (Limits::max_exponent - minExponent) + std::numeric_limits<std::size_t>::digits + 1;
    std::array<int32_t, (bits + digitBits - 1) / digitBits> digits_{};

    template <class Visitor> static void forDigits(F value, Visitor visit)
    {
        int exponent;
        F fraction = std::frexp(value, &exponent);
        const int shift = exponent - minExponent;
        int index = (shift + digitBits - 1) / digitBits;
        fraction = std::ldexp(fraction, shift - index * digitBits);
        while (fraction != 0)
        {
            fraction *= base;
            const int digit = static_cast<int>(fraction);
            fraction -= digit;
            visit(--index, digit);
        }
    }

public:
    void addProduct(F x, F y, int sign)
    {
        forDigits(x,
                  [&](int i, int a)
                  {
                      forDigits(y,
                                [&](int j, int b)
                                {
                                    int index = i + j;
                                    int64_t carry = static_cast<int64_t>(sign) * a * b;
                                    while (carry != 0)
                                    {
                                        carry += digits_[index];
                                        digits_[index++] = static_cast<int32_t>(carry % base);
                                        carry /= base;
                                    }
                                });
                  });
    }

    int sign() const
    {
        // Each lower digit has magnitude < base, so the highest nonzero digit decides.
        for (auto it = digits_.rbegin(); it != digits_.rend(); ++it)
            if (*it != 0)
                return *it > 0 ? 1 : -1;
        return 0;
    }
};
} // namespace ndsmath::detail
