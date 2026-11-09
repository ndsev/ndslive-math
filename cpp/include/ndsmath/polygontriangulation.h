// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include "polygon.h"
#include "wgs84polygon.h"

namespace ndsmath
{

//! Stateless ear-clipping triangulation on the longitude/latitude plane.
class PolygonTriangulation
{
public:
    //! Triangulates a polygon by ear clipping.
    //! Time complexity: O(n ^ 2)
    //! Space complexity: O(n)
    //! @param polygon Input polygon of type SIMPLE_POLYGON with at least 3 vertices.
    //!        Vertices must form a counter-clockwise simple ring without holes or
    //!        dateline crossings. A three-vertex input is copied without checking winding.
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

    //! Check whether p1, p2 and p3 form a convex turn (positive planar cross product).
    bool isConvex(const HighPrecWgs84 &p1, const HighPrecWgs84 &p2, const HighPrecWgs84 &p3);

    //! Check whether p is inside the counter-clockwise triangle (p1, p2, p3),
    //! including its boundary.
    bool isInside(const HighPrecWgs84 &p1, const HighPrecWgs84 &p2, const HighPrecWgs84 &p3,
                  const HighPrecWgs84 &p);

    //! Checks if two lines intersect.
    bool intersects(const HighPrecWgs84 &p11, const HighPrecWgs84 &p12, const HighPrecWgs84 &p21,
                    const HighPrecWgs84 &p22);

    //! Normalize a point treated as a vector; return (0, 0) for zero length.
    HighPrecWgs84 normalize(const HighPrecWgs84 &p);

    //! Update a vertex's convexity, angle score and ear status after its neighbours change.
    void updateVertex(PartitionVertex *v, PartitionVertex *vertices, int numVertices);

}; // class PolygonTriangulation

} // namespace ndsmath
