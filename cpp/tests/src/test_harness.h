// SPDX-License-Identifier: BSD-3-Clause
// Minimal dependency-free test harness for the C++ tests.
//
// We deliberately avoid an external unit-test framework: a tiny set of CHECK
// macros plus a `main()` per test executable is enough, portable everywhere
// (no framework runtime, no DLL surprises on Windows CI), and keeps the test
// binaries trivial to launch.
#pragma once

#include <cmath>
#include <cstdint>
#include <iostream>
#include <string>

namespace tst
{
inline int g_checks = 0;
inline int g_failures = 0;

inline bool approx(double a, double b, double tol)
{
    return std::fabs(a - b) <= tol;
}
} // namespace tst

#define CHECK(cond)                                                                                \
    do                                                                                             \
    {                                                                                              \
        ++tst::g_checks;                                                                           \
        if (!(cond))                                                                               \
        {                                                                                          \
            ++tst::g_failures;                                                                     \
            std::cerr << "FAIL " << __FILE__ << ":" << __LINE__ << ": " << #cond << "\n";          \
        }                                                                                          \
    } while (0)

#define CHECK_EQ(a, b)                                                                             \
    do                                                                                             \
    {                                                                                              \
        ++tst::g_checks;                                                                           \
        auto _a = (a);                                                                             \
        auto _b = (b);                                                                             \
        if (!(_a == _b))                                                                           \
        {                                                                                          \
            ++tst::g_failures;                                                                     \
            std::cerr << "FAIL " << __FILE__ << ":" << __LINE__ << ": " << #a << " (" << _a        \
                      << ") != " << #b << " (" << _b << ")\n";                                     \
        }                                                                                          \
    } while (0)

#define CHECK_NEAR(a, b, tol)                                                                      \
    do                                                                                             \
    {                                                                                              \
        ++tst::g_checks;                                                                           \
        double _a = (a);                                                                           \
        double _b = (b);                                                                           \
        if (!tst::approx(_a, _b, (tol)))                                                           \
        {                                                                                          \
            ++tst::g_failures;                                                                     \
            std::cerr << "FAIL " << __FILE__ << ":" << __LINE__ << ": " << #a << " (" << _a        \
                      << ") !~ " << #b << " (" << _b << ")\n";                                     \
        }                                                                                          \
    } while (0)

// Use at the end of main(): prints a summary and yields the process exit code.
#define TEST_SUMMARY()                                                                             \
    (std::cerr << tst::g_checks << " checks, " << tst::g_failures << " failures\n",                \
     tst::g_failures == 0 ? 0 : 1)
