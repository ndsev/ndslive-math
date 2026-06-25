// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

import "math"

// Wgs84Polygon is a simple polygon of WGS84 vertices with bounding box, median,
// and Separating-Axis-Theorem collision helpers.
//
// Port of the C++ HighPrecWgs84Polygon (cpp/include/ndsmath/wgs84polygon.h). It
// embeds Polygon, defaults to SimplePolygon, and overrides validity to require
// at least three vertices. The collision math runs on raw (lon, lat) doubles:
// no normalization, no antimeridian handling.
type Wgs84Polygon struct {
	Polygon
}

// NewWgs84Polygon constructs an empty simple WGS84 polygon.
func NewWgs84Polygon() Wgs84Polygon {
	return Wgs84Polygon{Polygon: NewPolygon(SimplePolygon)}
}

// NewWgs84PolygonWithVertices constructs a simple WGS84 polygon with the given
// vertices.
func NewWgs84PolygonWithVertices(vertices []Wgs84) Wgs84Polygon {
	return Wgs84Polygon{Polygon: NewPolygonWithVertices(SimplePolygon, vertices)}
}

// NewWgs84PolygonOfType constructs an empty WGS84 polygon of the given type.
func NewWgs84PolygonOfType(polygonType PolygonType) Wgs84Polygon {
	return Wgs84Polygon{Polygon: NewPolygon(polygonType)}
}

// NewWgs84PolygonOfTypeWithVertices constructs a WGS84 polygon of the given
// type with the given vertices.
func NewWgs84PolygonOfTypeWithVertices(polygonType PolygonType, vertices []Wgs84) Wgs84Polygon {
	return Wgs84Polygon{Polygon: NewPolygonWithVertices(polygonType, vertices)}
}

// EarthWrappingPoly returns the 4-vertex sentinel polygon wrapping the whole
// Earth.
//
// Constructed from (-180,-90), (-180,90), (180,-90), (180,90). These
// coordinates pass through Wgs84 normalization, so the stored values are not
// exactly those literals. This polygon is only used as an identity sentinel in
// CollidesWith via Equals; its exact normalized coordinates are not part of
// cross-language parity.
func EarthWrappingPoly() Wgs84Polygon {
	return NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(-180.0, -90.0, 0.0),
		NewWgs84(-180.0, 90.0, 0.0),
		NewWgs84(180.0, -90.0, 0.0),
		NewWgs84(180.0, 90.0, 0.0),
	})
}

// IsValid reports whether this is a valid polygon: at least three vertices.
// It overrides the embedded Polygon.IsValid (which requires only one vertex).
func (p Wgs84Polygon) IsValid() bool {
	return len(p.vertices) >= 3
}

// Equals reports order-sensitive vertex-wise equality via Wgs84 approximate
// equality.
func (p Wgs84Polygon) Equals(other Wgs84Polygon) bool {
	v := p.vertices
	vo := other.vertices
	if len(v) != len(vo) {
		return false
	}
	for i := range v {
		if !v[i].Equals(vo[i]) {
			return false
		}
	}
	return true
}

// AaBb returns the axis-aligned bounding box of this polygon.
//
// Returns a default (empty) Wgs84AABB if the polygon is invalid (fewer than 3
// vertices). The size is computed as raw coordinate differences (not
// normalized), then handed to the Wgs84AABB constructor, which still applies
// the excess-height clamp.
func (p Wgs84Polygon) AaBb() Wgs84AABB {
	if !p.IsValid() {
		return Wgs84AABB{}
	}

	minLon := p.vertices[0].Longitude()
	maxLon := p.vertices[0].Longitude()
	minLat := p.vertices[0].Latitude()
	maxLat := p.vertices[0].Latitude()
	for _, v := range p.vertices[1:] {
		lon := v.Longitude()
		lat := v.Latitude()
		if lon < minLon {
			minLon = lon
		}
		if lon > maxLon {
			maxLon = lon
		}
		if lat < minLat {
			minLat = lat
		}
		if lat > maxLat {
			maxLat = lat
		}
	}

	return NewWgs84AABB(NewWgs84(minLon, minLat, 0.0), Vec2{X: maxLon - minLon, Y: maxLat - minLat})
}

// Median returns the centroid of the polygon vertices.
//
// WARNING: this faithfully reproduces a bug in the C++ reference. The C++
// median() returns HighPrecWgs84(medLat, medLon) while the
// Wgs84(longitude, latitude) constructor takes longitude first — so the mean
// latitude is stored in the longitude slot and the mean longitude in the
// latitude slot. The returned point therefore has Longitude() == mean_lat and
// Latitude() == mean_lon. For symmetric polygons the swap is invisible; for
// asymmetric ones it is observable. It is preserved here for cross-language
// parity.
//
// The means are accumulated as sum(coord / n) per the C++ code (not
// sum(coord) / n), to match its floating-point rounding.
func (p Wgs84Polygon) Median() Wgs84 {
	n := float64(len(p.vertices))
	medLat := 0.0
	for _, v := range p.vertices {
		medLat += v.Latitude() / n
	}
	medLon := 0.0
	for _, v := range p.vertices {
		medLon += v.Longitude() / n
	}
	// NOTE: lon/lat swap preserved from the C++ reference (see doc comment).
	return NewWgs84(medLat, medLon, 0.0)
}

// CollidesWith reports whether this polygon collides with other (via the
// Separating-Axis Theorem).
//
// The earth-wrapping sentinel collides with everything. Otherwise the SAT axis
// sets are taken from this polygon's edges (first test) and from other's edges
// (second test); if no separating axis is found on either, the polygons
// collide.
func (p Wgs84Polygon) CollidesWith(other Wgs84Polygon) bool {
	earth := EarthWrappingPoly()
	if p.Equals(earth) || other.Equals(earth) {
		return true
	}
	if areSeparate(p, other, p) {
		return false
	}
	// NOTE: the C++ reference passes (other, other) here — axes come from
	// other's edges, projecting both this polygon and other. Preserved exactly.
	if areSeparate(p, other, other) {
		return false
	}
	return true
}

// projectOnAxis projects poly onto axis, returning Vec2{min, max}.
func projectOnAxis(poly Wgs84Polygon, axis Vec2) Vec2 {
	minimum := math.Inf(1)
	maximum := math.Inf(-1)

	vs := poly.vertices
	n := len(vs)
	for i := 0; i < n; i++ {
		ni := i + 1
		if ni == n {
			ni = 0
		}
		begX, begY := vs[i].Longitude(), vs[i].Latitude()
		endX, endY := vs[ni].Longitude(), vs[ni].Latitude()

		x0 := begX*axis.X + begY*axis.Y
		if x0 < minimum {
			minimum = x0
		}
		if x0 > maximum {
			maximum = x0
		}

		x1 := x0 + (endX-begX)*axis.X + (endY-begY)*axis.Y
		if x1 < minimum {
			minimum = x1
		}
		if x1 > maximum {
			maximum = x1
		}
	}
	return Vec2{X: minimum, Y: maximum}
}

// areSeparate1d reports whether two 1D intervals (min, max) are disjoint.
func areSeparate1d(minMax1, minMax2 Vec2) bool {
	return (minMax1.X < minMax2.X && minMax1.Y < minMax2.X) ||
		(minMax1.X > minMax2.Y && minMax1.Y > minMax2.Y)
}

// areSeparate reports whether a separating axis exists among refForAxis's edge
// normals, projecting both this and other onto each.
func areSeparate(this, other, refForAxis Wgs84Polygon) bool {
	vs := refForAxis.vertices
	n := len(vs)
	for i := 0; i < n; i++ {
		ni := i + 1
		if ni == n {
			ni = 0
		}
		dx := vs[ni].Longitude() - vs[i].Longitude()
		dy := vs[ni].Latitude() - vs[i].Latitude()
		normal := Vec2{X: dy, Y: -dx}

		minMaxPoly1 := projectOnAxis(this, normal)
		minMaxPoly2 := projectOnAxis(other, normal)

		if areSeparate1d(minMaxPoly1, minMaxPoly2) {
			return true
		}
	}
	return false
}
