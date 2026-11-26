// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

import (
	"math"
	"math/big"
)

// Orientation is the winding order of a polygon. The integer values match the
// C++ enum (cpp/include/ndsmath/polygon.h) and are part of the parity output.
type Orientation int

const (
	// Clockwise winding (negative signed area).
	Clockwise Orientation = -1
	// InvalidOrientation: not a simple polygon / single triangle, or zero area.
	InvalidOrientation Orientation = 0
	// CounterClockwise winding (positive signed area).
	CounterClockwise Orientation = 1
)

// PolygonType is the topology of a polygon. The integer values match the C++
// enum and are part of the parity output.
type PolygonType int

const (
	// SimplePolygon is a shape with an arbitrary number of vertices and no
	// holes; the last vertex connects back to the first.
	SimplePolygon PolygonType = 0
	// TriangleStrip is a triangle strip.
	TriangleStrip PolygonType = 1
	// TriangleFan is a triangle fan.
	TriangleFan PolygonType = 2
	// TriangleList is a set of independent triangles; three consecutive
	// vertices form one.
	TriangleList PolygonType = 3
	// PolygonUnknown is an illegal polygon type, used to signal failure.
	PolygonUnknown PolygonType = 4
)

// Polygon is a set of WGS84 vertices with a topology type and an orientation
// query. It mirrors the C++ Polygon<Vector> template, specialized directly to a
// slice of Wgs84 vertices. Orientation is computed on the raw (lon, lat) plane
// (no WGS84 normalization, no antimeridian handling).
//
// Wgs84Polygon embeds Polygon and overrides validity semantics via its own
// IsValid method.
type Polygon struct {
	polygonType PolygonType
	vertices    []Wgs84
}

// NewPolygon constructs an empty polygon of the given type.
func NewPolygon(polygonType PolygonType) Polygon {
	return Polygon{polygonType: polygonType}
}

// NewPolygonWithVertices constructs a polygon of the given type with the
// supplied vertices (copied).
func NewPolygonWithVertices(polygonType PolygonType, vertices []Wgs84) Polygon {
	cp := make([]Wgs84, len(vertices))
	copy(cp, vertices)
	return Polygon{polygonType: polygonType, vertices: cp}
}

// AddVertex appends a single vertex.
func (p *Polygon) AddVertex(position Wgs84) {
	p.vertices = append(p.vertices, position)
}

// AddVertices appends a list of vertices, in order.
func (p *Polygon) AddVertices(vertices []Wgs84) {
	p.vertices = append(p.vertices, vertices...)
}

// At returns the vertex at index i (no bounds check beyond Go's own, mirroring
// the C++ operator[]).
func (p Polygon) At(i int) Wgs84 {
	return p.vertices[i]
}

// Set replaces the vertex at index i.
func (p *Polygon) Set(i int, value Wgs84) {
	p.vertices[i] = value
}

// Type returns the polygon type.
func (p Polygon) Type() PolygonType {
	return p.polygonType
}

// SetType sets the polygon type.
func (p *Polygon) SetType(polygonType PolygonType) {
	p.polygonType = polygonType
}

// IsValid reports whether this is a valid polygon. The base implementation
// requires at least one vertex; Wgs84Polygon overrides it to require >= 3.
func (p Polygon) IsValid() bool {
	return len(p.vertices) > 0
}

// Vertices returns the underlying vertex slice.
func (p Polygon) Vertices() []Wgs84 {
	return p.vertices
}

// Len returns the number of vertices.
func (p Polygon) Len() int {
	return len(p.vertices)
}

// Orientation computes the winding order via the signed shoelace formula.
//
// Only works for SimplePolygon and a single-triangle TriangleList (exactly 3
// vertices). All other types return InvalidOrientation without computing area.
// Collinear vertices (zero area) also return InvalidOrientation. Uses raw
// (lon, lat) doubles; no normalization.
func (p Polygon) Orientation() Orientation {
	if p.polygonType != SimplePolygon &&
		!(p.polygonType == TriangleList && len(p.vertices) == 3) {
		return InvalidOrientation
	}

	n := len(p.vertices)
	if n < 3 {
		return InvalidOrientation
	}

	originX := p.vertices[0].Dx()
	originY := p.vertices[0].Dy()
	area, magnitude := 0.0, 0.0
	for i := 1; i < n-1; i++ {
		a, b := p.vertices[i], p.vertices[i+1]
		left := (a.Dx() - originX) * (b.Dy() - originY)
		right := (a.Dy() - originY) * (b.Dx() - originX)
		area += left - right
		magnitude += math.Abs(left) + math.Abs(right)
	}
	// Only trust a sign larger than the roundoff bound on the products and sum.
	bound := 4 * (float64(n) + 4) * 0x1p-52 * (magnitude + 0x1p-1022)
	if math.Abs(area) > bound {
		if area > 0 {
			return CounterClockwise
		}
		return Clockwise
	}
	return p.exactOrientation()
}

// exactOrientation sums the signed products of the original binary coordinates.
func (p Polygon) exactOrientation() Orientation {
	var area, left, right big.Rat
	prev := p.vertices[len(p.vertices)-1]
	for _, v := range p.vertices {
		var px, py, x, y big.Rat
		if px.SetFloat64(prev.Dx()) == nil || py.SetFloat64(prev.Dy()) == nil ||
			x.SetFloat64(v.Dx()) == nil || y.SetFloat64(v.Dy()) == nil {
			return InvalidOrientation
		}
		left.Mul(&px, &y)
		right.Mul(&py, &x)
		area.Add(&area, left.Sub(&left, &right))
		prev = v
	}
	return Orientation(area.Sign())
}
