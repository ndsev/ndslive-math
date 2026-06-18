// SPDX-License-Identifier: MIT
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#include "mortoncode.h"
#include "wgs84.h"

namespace ndsmath
{

MortonCode MortonCode::fromWgs84Coordinates(const HighPrecWgs84 &wgs84)
{
    const double bitScaling = 360.0 / (std::numeric_limits<uint32_t>::max() + 1.0);
    const double ndsCoordX = wgs84.longitude() / bitScaling;
    const double ndsCoordY = wgs84.latitude() / bitScaling;

    return MortonCode::fromNdsCoordinates(static_cast<int64_t>(ndsCoordX),
                                          static_cast<int64_t>(ndsCoordY));
}

} // namespace ndsmath
