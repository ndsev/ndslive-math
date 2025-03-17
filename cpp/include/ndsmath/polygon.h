// Copyright (c) Navigation Data Standard e.V. - See "LICENSE" file.

#pragma once

#include <type_traits>

namespace ndsmath
{

//! The `Polygon` template class manages a set of vertices and supports different polygon types,
//! such as simple polygons, triangle lists, and triangle structures. It provides methods
//! for adding vertices, checking the orientation, and validating the polygon.
template<class Vector>
class Polygon
{
    using Position = typename Vector::value_type;

    // Determine type of Position.
    using T = typename std::decay<decltype(std::declval<Position>().dx())>::type;

public:
    enum Orientation
    {
        CLOCKWISE = -1,
        INVALID_ORIENTATION = 0,
        COUNTERCLOCKWISE = 1
    };

    enum PolygonType
    {
        //! A simple polygon is a shape with an arbitrary number of vertices and
        //! no holes. The last vertex is connected to the first.
        SIMPLE_POLYGON = 0,

        //! A triangle strip.
        TRIANGLE_STRIP = 1,

        //! A triangle fan.
        TRIANGLE_FAN = 2,

        //! A triangle list a set of triangles without any vertex sharing. Three
        //! consecutive vertices form a triangle.
        TRIANGLE_LIST = 3,

        //! Illegal polygon type. Mainly used for returning an illegal polygon.
        UNKNOWN = 4
    };

    //! Constructor.
    Polygon(PolygonType polygonType = UNKNOWN) :
        polygonType_(polygonType),
        vertices_()
    {
    }

    //! Constructor with vertices
    Polygon(PolygonType polygonType, const Vector &vertices) :
        polygonType_(polygonType),
        vertices_(vertices)
    {
    }

    //! Add a vertice.
    void addVertex(const Position &position)
    {
        vertices_.push_back(position);
    }

    //! Add a list of vertices.
    void addVertices(const Vector& vertices)
    {
        for (auto it = vertices.begin(); it != vertices.end(); ++it)
        {
            vertices_.push_back(*it);
        }
    }

    //! Array subscript operator.
    Position& operator[](const int index)
    {
        NDSAFW_ASSERT(index < vertices_.size());
        return vertices_[index];
    }

    //! Const array subscript operator.
    const Position& operator[](const int index) const
    {
        NDSAFW_ASSERT(index < vertices_.size());
        return vertices_[index];
    }

    //! Get the polygon type.
    PolygonType type() const
    {
        return polygonType_;
    }

    //! Set the polygon type.
    void setType(PolygonType polygonType)
    {
        polygonType_ = polygonType;
    }

    //! Is this a valid polygon?
    virtual bool isValid() const
    {
        return !vertices_.empty();
    }

    //! Get the list of vertices.
    const Vector& vertices() const
    {
        return vertices_;
    }

    //! Get the list of vertices.
    Vector& vertices()
    {
        return vertices_;
    }

    //! Get the orientation of the polygon. Only works for simple polygons
    //! and triangle lists with a single element. For all other polygons,
    //! INVALID_ORIENTATION will be returned.
    Orientation orientation() const
    {
        if (polygonType_ != SIMPLE_POLYGON && (polygonType_ != TRIANGLE_LIST || vertices_.size() != 3))
        {
            return INVALID_ORIENTATION;
        }

        T area = 0;
        for (auto i = 0; i < vertices_.size(); i++)
        {
            auto nextIndex = i + 1;
            if (nextIndex == vertices_.size())
            {
                nextIndex = 0;
            }

            area += vertices_[i].dx() * vertices_[nextIndex].dy() - vertices_[i].dy() * vertices_[nextIndex].dx();
        }

        if (area > 0)
        {
            return COUNTERCLOCKWISE;
        }
        else if (area < 0)
        {
            return CLOCKWISE;
        }
        else
        {
            return INVALID_ORIENTATION;
        }
    }

protected:
    //! Vertices.
    Vector vertices_;

    //! Polygon type.
    PolygonType polygonType_;

}; // class Polygon

} // namespace ndsmath
