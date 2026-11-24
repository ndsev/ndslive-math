// SPDX-License-Identifier: BSD-3-Clause
package ndslivemath

import "math"

// PolygonAreaRelation classifies a closed rectangle against an unwrapped polygon area.
type PolygonAreaRelation uint8

const (
	PolygonAreaOutside PolygonAreaRelation = iota
	PolygonAreaInside
	PolygonAreaBoundary
)

// areaRingSize ignores one conventional repeated closing vertex.
func areaRingSize(r []Vec2) int {
	if len(r) > 1 && r[0] == r[len(r)-1] {
		return len(r) - 1
	}
	return len(r)
}

// areaDifference returns the exact low/high components of a difference.
func areaDifference(a, b float64) [2]float64 {
	high := a - b
	virtualB := a - high
	return [2]float64{(a - (high + virtualB)) + (virtualB - b), high}
}

// areaGrow adds a scalar to a nonoverlapping expansion without losing bits.
func areaGrow(expansion []float64, value float64) []float64 {
	count := 0
	for _, term := range expansion {
		total := value + term
		virtualTerm := total - value
		low := (value - (total - virtualTerm)) + (term - virtualTerm)
		if low != 0 {
			expansion[count] = low
			count++
		}
		value = total
	}
	expansion = expansion[:count]
	if value != 0 {
		expansion = append(expansion, value)
	}
	return expansion
}

// areaCross uses exact expansions when the orientation determinant is ambiguous.
func areaCross(a, b, c Vec2) float64 {
	left, right := (b.X-a.X)*(c.Y-a.Y), (b.Y-a.Y)*(c.X-a.X)
	determinant := left - right
	if math.Abs(determinant) > (math.Abs(left)+math.Abs(right))*8*0x1p-52 {
		return determinant
	}
	expansion := make([]float64, 0, 16)
	for _, sign := range []float64{1, -1} {
		x, y := areaDifference(b.X, a.X), areaDifference(c.Y, a.Y)
		if sign < 0 {
			x, y = areaDifference(b.Y, a.Y), areaDifference(c.X, a.X)
		}
		for _, u := range x {
			for _, v := range y {
				high := u * v
				expansion = areaGrow(expansion, sign*math.FMA(u, v, -high))
				expansion = areaGrow(expansion, sign*high)
			}
		}
	}
	if len(expansion) == 0 {
		return 0
	}
	return expansion[len(expansion)-1]
}

// areaOnSegment tests closed segment membership.
func areaOnSegment(p, a, b Vec2) bool {
	return areaCross(a, b, p) == 0 && p.X >= math.Min(a.X, b.X) && p.X <= math.Max(a.X, b.X) && p.Y >= math.Min(a.Y, b.Y) && p.Y <= math.Max(a.Y, b.Y)
}

// areaIntersects includes collinear contact and endpoints.
func areaIntersects(a, b, c, d Vec2) bool {
	ac, ad, ca, cb := areaCross(a, b, c), areaCross(a, b, d), areaCross(c, d, a), areaCross(c, d, b)
	return (((ac < 0 && ad > 0) || (ac > 0 && ad < 0)) && ((ca < 0 && cb > 0) || (ca > 0 && cb < 0))) || areaOnSegment(a, c, d) || areaOnSegment(b, c, d) || areaOnSegment(c, a, b) || areaOnSegment(d, a, b)
}

// areaContains implements even/odd containment with the boundary included.
func areaContains(r []Vec2, p Vec2) bool {
	n, inside := areaRingSize(r), false
	for i := 0; i < n; i++ {
		a, b := r[i], r[(i+1)%n]
		if areaOnSegment(p, a, b) {
			return true
		}
		if (a.Y > p.Y) != (b.Y > p.Y) && (areaCross(a, b, p) > 0) == (b.Y > a.Y) {
			inside = !inside
		}
	}
	return inside
}

// areaRingsIntersect detects contact between ring boundaries.
func areaRingsIntersect(a, b []Vec2) bool {
	na, nb := areaRingSize(a), areaRingSize(b)
	for i := 0; i < na; i++ {
		for j := 0; j < nb; j++ {
			if areaIntersects(a[i], a[(i+1)%na], b[j], b[(j+1)%nb]) {
				return true
			}
		}
	}
	return false
}

// areaFinite excludes NaN and either infinity.
func areaFinite(v float64) bool { return !math.IsNaN(v) && !math.IsInf(v, 0) }

// areaValidRing requires a finite nondegenerate simple ring, preserving winding.
func areaValidRing(r []Vec2) bool {
	n, noncollinear := areaRingSize(r), false
	if n < 3 {
		return false
	}
	for i := 0; i < n; i++ {
		a, b, previous := r[i], r[(i+1)%n], r[(i+n-1)%n]
		if !areaFinite(a.X) || !areaFinite(a.Y) || a == b {
			return false
		}
		turn := areaCross(previous, a, b)
		if !areaFinite(turn) || (turn == 0 && !areaOnSegment(a, previous, b)) {
			return false
		}
		// Simplicity plus a non-collinear turn avoids a cancelling area sum.
		noncollinear = noncollinear || turn != 0
		for j := i + 1; j < n; j++ {
			if j != i+1 && !(i == 0 && j == n-1) && areaIntersects(a, b, r[j], r[(j+1)%n]) {
				return false
			}
		}
	}
	return noncollinear
}

// ValidPolygonArea validates a simple exterior and disjoint strictly interior holes.
func ValidPolygonArea(exterior []Vec2, holes [][]Vec2) bool {
	if !areaValidRing(exterior) {
		return false
	}
	for i, hole := range holes {
		if !areaValidRing(hole) || !areaContains(exterior, hole[0]) || areaRingsIntersect(exterior, hole) {
			return false
		}
		for _, other := range holes[:i] {
			if areaRingsIntersect(hole, other) || areaContains(hole, other[0]) || areaContains(other, hole[0]) {
				return false
			}
		}
	}
	return true
}

// PolygonAreasIntersect intersects prevalidated areas in one plane, including every boundary.
func PolygonAreasIntersect(a []Vec2, aHoles [][]Vec2, b []Vec2, bHoles [][]Vec2) bool {
	if len(a) == 0 || len(b) == 0 {
		return false
	}
	for _, left := range append([][]Vec2{a}, aHoles...) {
		for _, right := range append([][]Vec2{b}, bHoles...) {
			if areaRingsIntersect(left, right) {
				return true
			}
		}
	}
	inside := func(p Vec2, outer []Vec2, holes [][]Vec2) bool {
		if !areaContains(outer, p) {
			return false
		}
		for _, hole := range holes {
			if areaContains(hole, p) {
				return false
			}
		}
		return true
	}
	return inside(a[0], b, bHoles) || inside(b[0], a, aHoles)
}

// ClassifyPolygonRectangle queries prevalidated raw rings. Exterior and hole boundary contact counts.
func ClassifyPolygonRectangle(exterior []Vec2, holes [][]Vec2, minimum, maximum Vec2) PolygonAreaRelation {
	if len(exterior) < 3 || !areaFinite(minimum.X) || !areaFinite(minimum.Y) || !areaFinite(maximum.X) || !areaFinite(maximum.Y) || minimum.X > maximum.X || minimum.Y > maximum.Y {
		return PolygonAreaOutside
	}
	rectangle := []Vec2{minimum, {X: maximum.X, Y: minimum.Y}, maximum, {X: minimum.X, Y: maximum.Y}}
	touches := func(r []Vec2) bool {
		for _, p := range r {
			if p.X >= minimum.X && p.X <= maximum.X && p.Y >= minimum.Y && p.Y <= maximum.Y {
				return true
			}
		}
		return areaRingsIntersect(r, rectangle)
	}
	if touches(exterior) {
		return PolygonAreaBoundary
	}
	for _, hole := range holes {
		if touches(hole) {
			return PolygonAreaBoundary
		}
	}
	centre := Vec2{X: (minimum.X + maximum.X) * 0.5, Y: (minimum.Y + maximum.Y) * 0.5}
	if !areaContains(exterior, centre) {
		return PolygonAreaOutside
	}
	for _, hole := range holes {
		if areaContains(hole, centre) {
			return PolygonAreaOutside
		}
	}
	return PolygonAreaInside
}
