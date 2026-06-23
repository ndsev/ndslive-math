// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include "polygon.h"
#include "wgs84polygon.h"

namespace ndsmath
{

class PolygonTriangulation
{
public:
    //! Triangulates a polygon by ear clipping.
    //! Time complexity: O(n ^ 2)
    //! Space complexity: O(n)
    //! @param polygon Input polygon of type SIMPLE_POLYGON with at least 3 vertices.
    //!        Vertices have to be in counter-clockwise order.
    //! @return A polygon of type TRIANGLE_LIST on success and a polygon of
    //!         type UNKNOWN on failure.
    HighPrecWgs84Polygon triangulateByEarClipping(const HighPrecWgs84Polygon &polygon);

private:
    struct PartitionVertex
    {
        bool isActive;
        bool isConvex;
        bool isEar;
        HighPrecWgs84 p;
        double angle;
        PartitionVertex *previous = nullptr;
        PartitionVertex *next = nullptr;
    };

    //! Check if a polygon is convex.
    bool isConvex(const HighPrecWgs84 &p1, const HighPrecWgs84 &p2, const HighPrecWgs84 &p3);

    //! Check if a given point is inside the polygon.
    bool isInside(const HighPrecWgs84 &p1, const HighPrecWgs84 &p2, const HighPrecWgs84 &p3,
                  const HighPrecWgs84 &p);

    //! Checks if two lines intersect.
    bool intersects(const HighPrecWgs84 &p11, const HighPrecWgs84 &p12, const HighPrecWgs84 &p21,
                    const HighPrecWgs84 &p22);

    //! Normalize a point threated as a vector.
    HighPrecWgs84 normalize(const HighPrecWgs84 &p);

    //! Helper function for ear clipping triangulation.
    void updateVertex(PartitionVertex *v, PartitionVertex *vertices, int numVertices);

}; // class PolygonTriangulation

} // namespace ndsmath
