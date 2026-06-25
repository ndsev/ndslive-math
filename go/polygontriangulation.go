// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

import "math"

// PolygonTriangulation triangulates simple polygons by ear clipping (O(n^2)).
//
// Port of the C++ PolygonTriangulation (cpp/include/ndsmath/
// polygontriangulation.{h,cpp}). The C++ implementation uses a pointer-linked
// ring of partition vertices; this port uses an index-linked slice of
// partitionVertex (prev / next integer indices) to avoid manual memory
// management while reproducing the same traversal.
//
// The set of output triangles is deterministic, but the ordering of triangles
// and the rotation of each triangle's three vertices are implementation-
// specific (driven by the "most extruded ear" tie-break and floating-point
// angle comparisons). Triangulation output is therefore NOT part of the
// cross-language parity vectors; tests assert structure (type and vertex count)
// only.
type PolygonTriangulation struct{}

// partitionVertex is a node in the ear-clipping ring (index-linked replacement
// for the C++ pointers).
type partitionVertex struct {
	isActive bool
	isConvex bool
	isEar    bool
	p        Wgs84
	angle    float64
	previous int
	next     int
}

// TriangulateByEarClipping triangulates a CCW simple polygon into a
// TriangleList.
//
// The input must be a SimplePolygon with at least 3 vertices, in
// counter-clockwise order. It returns a Wgs84Polygon of type TriangleList on
// success (3 * (n - 2) vertices), or a polygon of type PolygonUnknown on
// failure (wrong type, too few vertices, or no ear found).
func (PolygonTriangulation) TriangulateByEarClipping(polygon Wgs84Polygon) Wgs84Polygon {
	result := NewWgs84PolygonOfType(TriangleList)

	if polygon.Type() != SimplePolygon || polygon.Len() < 3 {
		return NewWgs84PolygonOfType(PolygonUnknown)
	}

	numVertices := polygon.Len()

	// Nothing to do for a single triangle.
	if numVertices == 3 {
		result.AddVertices(polygon.Vertices())
		return result
	}

	vertices := make([]partitionVertex, numVertices)
	for i := 0; i < numVertices; i++ {
		next := i + 1
		if i == numVertices-1 {
			next = 0
		}
		previous := i - 1
		if i == 0 {
			previous = numVertices - 1
		}
		vertices[i] = partitionVertex{
			isActive: true,
			p:        polygon.At(i),
			next:     next,
			previous: previous,
		}
	}

	for i := 0; i < numVertices; i++ {
		updateVertex(i, vertices, numVertices)
	}

	ear := -1
	for i := 0; i < numVertices-3; i++ {
		earFound := false

		// Find the most extruded ear (largest angle; first wins ties).
		for j := 0; j < numVertices; j++ {
			if !vertices[j].isActive || !vertices[j].isEar {
				continue
			}
			if !earFound {
				earFound = true
				ear = j
			} else if vertices[j].angle > vertices[ear].angle {
				ear = j
			}
		}

		if !earFound {
			return NewWgs84PolygonOfType(PolygonUnknown)
		}

		earPrev := vertices[ear].previous
		earNext := vertices[ear].next
		result.AddVertex(vertices[earPrev].p)
		result.AddVertex(vertices[ear].p)
		result.AddVertex(vertices[earNext].p)

		vertices[ear].isActive = false
		vertices[earPrev].next = earNext
		vertices[earNext].previous = earPrev

		if i == numVertices-4 {
			break
		}

		updateVertex(earPrev, vertices, numVertices)
		updateVertex(earNext, vertices, numVertices)
	}

	for i := 0; i < numVertices; i++ {
		if vertices[i].isActive {
			result.AddVertex(vertices[vertices[i].previous].p)
			result.AddVertex(vertices[i].p)
			result.AddVertex(vertices[vertices[i].next].p)
			break
		}
	}

	return result
}

// triNormalize vector-normalizes p; (0, 0) if it has zero length.
//
// Mirrors the C++ normalize: the unit vector is wrapped back into a Wgs84
// (which re-normalizes as a coordinate). Odd, but part of the reference
// behavior.
func triNormalize(p Wgs84) Wgs84 {
	n := math.Sqrt(p.Dx()*p.Dx() + p.Dy()*p.Dy())
	if n != 0.0 {
		return NewWgs84(p.Dx()/n, p.Dy()/n, 0.0)
	}
	return NewWgs84(0.0, 0.0, 0.0)
}

// triIsConvex reports whether the turn p1 -> p2 -> p3 is convex (positive cross
// product).
func triIsConvex(p1, p2, p3 Wgs84) bool {
	return (p3.Dy()-p1.Dy())*(p2.Dx()-p1.Dx())-(p3.Dx()-p1.Dx())*(p2.Dy()-p1.Dy()) > 0.0
}

// triIsInside reports whether point p lies inside triangle (p1, p2, p3).
func triIsInside(p1, p2, p3, p Wgs84) bool {
	return !triIsConvex(p1, p, p2) && !triIsConvex(p2, p, p3) && !triIsConvex(p3, p, p1)
}

// updateVertex recomputes convexity, ear status, and angle of vertex vIdx.
func updateVertex(vIdx int, vertices []partitionVertex, numVertices int) {
	v := &vertices[vIdx]
	v1 := vertices[v.previous]
	v3 := vertices[v.next]
	v.isConvex = triIsConvex(v1.p, v.p, v3.p)

	vec1 := triNormalize(v1.p.Sub(v.p))
	vec3 := triNormalize(v3.p.Sub(v.p))

	v.angle = vec1.Dx()*vec3.Dx() + vec1.Dy()*vec3.Dy()

	if v.isConvex {
		v.isEar = true
		for i := 0; i < numVertices; i++ {
			if vertices[i].p.Dx() == v.p.Dx() && vertices[i].p.Dy() == v.p.Dy() {
				continue
			}
			if vertices[i].p.Dx() == v1.p.Dx() && vertices[i].p.Dy() == v1.p.Dy() {
				continue
			}
			if vertices[i].p.Dx() == v3.p.Dx() && vertices[i].p.Dy() == v3.p.Dy() {
				continue
			}
			if triIsInside(v1.p, v.p, v3.p, vertices[i].p) {
				v.isEar = false
				break
			}
		}
	} else {
		v.isEar = false
	}
}
