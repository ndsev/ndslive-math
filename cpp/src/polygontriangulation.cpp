// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#include "polygontriangulation.h"
#include <cmath>

namespace ndsmath
{

HighPrecWgs84 PolygonTriangulation::normalize(const HighPrecWgs84 &p)
{
    const double n = sqrt(p.dx() * p.dx() + p.dy() * p.dy());
    return (n != 0.0) ? HighPrecWgs84(p / n) : HighPrecWgs84(0.0, 0.0);
}

bool PolygonTriangulation::isConvex(const HighPrecWgs84 &p1, const HighPrecWgs84 &p2,
                                    const HighPrecWgs84 &p3)
{
    return (p3.dy() - p1.dy()) * (p2.dx() - p1.dx()) - (p3.dx() - p1.dx()) * (p2.dy() - p1.dy()) >
           0.0;
}

bool PolygonTriangulation::isInside(const HighPrecWgs84 &p1, const HighPrecWgs84 &p2,
                                    const HighPrecWgs84 &p3, const HighPrecWgs84 &p)
{
    return (!isConvex(p1, p, p2) && !isConvex(p2, p, p3) && !isConvex(p3, p, p1));
}

void PolygonTriangulation::updateVertex(PartitionVertex *v, PartitionVertex *vertices,
                                        int numVertices)
{
    PartitionVertex *v1 = v->previous;
    PartitionVertex *v3 = v->next;
    v->isConvex = isConvex(v1->p, v->p, v3->p);

    HighPrecWgs84 vec1 = normalize(v1->p - v->p);
    HighPrecWgs84 vec3 = normalize(v3->p - v->p);

    v->angle = vec1.dx() * vec3.dx() + vec1.dy() * vec3.dy();

    if (v->isConvex)
    {
        v->isEar = true;
        for (auto i = 0; i < numVertices; i++)
        {
            if ((vertices[i].p.dx() == v->p.dx()) && (vertices[i].p.dy() == v->p.dy()))
                continue;
            if ((vertices[i].p.dx() == v1->p.dx()) && (vertices[i].p.dy() == v1->p.dy()))
                continue;
            if ((vertices[i].p.dx() == v3->p.dx()) && (vertices[i].p.dy() == v3->p.dy()))
                continue;

            if (isInside(v1->p, v->p, v3->p, vertices[i].p))
            {
                v->isEar = false;
                break;
            }
        }
    }
    else
    {
        v->isEar = false;
    }
}

HighPrecWgs84Polygon
PolygonTriangulation::triangulateByEarClipping(const HighPrecWgs84Polygon &polygon)
{
    PartitionVertex *vertices = nullptr;
    PartitionVertex *ear = nullptr;
    HighPrecWgs84Polygon result(HighPrecWgs84Polygon::TRIANGLE_LIST);

    if (polygon.type() != HighPrecWgs84Polygon::SIMPLE_POLYGON || polygon.vertices().size() < 3)
    {
        return HighPrecWgs84Polygon(HighPrecWgs84Polygon::UNKNOWN);
    }

    auto numVertices = polygon.vertices().size();

    // Nothing to do for three triangles.
    if (numVertices == 3)
    {
        result.addVertices(polygon.vertices());
        return result;
    }

    vertices = new PartitionVertex[numVertices];
    for (auto i = 0; i < numVertices; i++)
    {
        vertices[i].isActive = true;
        vertices[i].p = polygon[i];
        vertices[i].next = (i == (numVertices - 1)) ? &(vertices[0]) : &(vertices[i + 1]);
        vertices[i].previous = (i == 0) ? &(vertices[numVertices - 1]) : &(vertices[i - 1]);
    }

    for (auto i = 0; i < numVertices; i++)
    {
        updateVertex(&vertices[i], vertices, numVertices);
    }

    for (auto i = 0; i < numVertices - 3; i++)
    {
        bool earFound = false;

        // Find the most extruded ear.
        for (auto j = 0; j < numVertices; j++)
        {
            if (!vertices[j].isActive || !vertices[j].isEar)
            {
                continue;
            }

            if (!earFound)
            {
                earFound = true;
                ear = &(vertices[j]);
            }
            else
            {
                if (vertices[j].angle > ear->angle)
                {
                    ear = &(vertices[j]);
                }
            }
        }

        if (!earFound)
        {
            delete[] vertices;
            return HighPrecWgs84Polygon(HighPrecWgs84Polygon::UNKNOWN);
        }

        result.addVertex(ear->previous->p);
        result.addVertex(ear->p);
        result.addVertex(ear->next->p);

        ear->isActive = false;
        ear->previous->next = ear->next;
        ear->next->previous = ear->previous;

        if (i == numVertices - 4)
        {
            break;
        }

        updateVertex(ear->previous, vertices, numVertices);
        updateVertex(ear->next, vertices, numVertices);
    }

    for (auto i = 0; i < numVertices; i++)
    {
        if (vertices[i].isActive)
        {
            result.addVertex(vertices[i].previous->p);
            result.addVertex(vertices[i].p);
            result.addVertex(vertices[i].next->p);
            break;
        }
    }

    delete[] vertices;
    return result;
}

} // namespace ndsmath
