// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

import (
	"math"
	"testing"
)

// triangleArea returns twice the signed area of triangle (a, b, c) in the
// (lon, lat) plane.
func triangleArea2(a, b, c Wgs84) float64 {
	return (b.Lon-a.Lon)*(c.Lat-a.Lat) - (c.Lon-a.Lon)*(b.Lat-a.Lat)
}

func TestTriangulateTriangle(t *testing.T) {
	var tri PolygonTriangulation
	in := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0), NewWgs84(4, 0, 0), NewWgs84(0, 4, 0),
	})
	out := tri.TriangulateByEarClipping(in)
	if out.Type() != TriangleList {
		t.Fatalf("type = %v, want TriangleList", out.Type())
	}
	if out.Len() != 3 {
		t.Fatalf("vertex count = %d, want 3", out.Len())
	}
	// A single triangle is copied through unchanged.
	for i := 0; i < 3; i++ {
		if !out.At(i).Equals(in.At(i)) {
			t.Errorf("vertex %d = %v, want %v", i, out.At(i), in.At(i))
		}
	}
}

func TestTriangulateConvexQuad(t *testing.T) {
	var tri PolygonTriangulation
	in := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0), NewWgs84(4, 0, 0), NewWgs84(4, 4, 0), NewWgs84(0, 4, 0),
	})
	out := tri.TriangulateByEarClipping(in)
	if out.Type() != TriangleList {
		t.Fatalf("type = %v, want TriangleList", out.Type())
	}
	// n = 4 -> 3 * (n - 2) = 6 vertices (2 triangles).
	if out.Len() != 6 {
		t.Fatalf("vertex count = %d, want 6", out.Len())
	}
	// The two emitted triangles should tile the quad: total area == quad area.
	v := out.Vertices()
	total := 0.0
	for i := 0; i+2 < len(v); i += 3 {
		total += math.Abs(triangleArea2(v[i], v[i+1], v[i+2])) / 2.0
	}
	if math.Abs(total-16.0) > 1e-9 {
		t.Errorf("triangulated area = %v, want 16", total)
	}
}

func TestTriangulateConcaveReflexVertex(t *testing.T) {
	var tri PolygonTriangulation
	// An arrow-head / concave polygon (CCW). The vertex (2, 1) is reflex.
	in := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0),
		NewWgs84(4, 0, 0),
		NewWgs84(2, 1, 0), // reflex vertex pointing inward
		NewWgs84(4, 4, 0),
		NewWgs84(0, 4, 0),
	})
	out := tri.TriangulateByEarClipping(in)
	if out.Type() != TriangleList {
		t.Fatalf("type = %v, want TriangleList", out.Type())
	}
	// n = 5 -> 3 * (n - 2) = 9 vertices (3 triangles).
	if out.Len() != 9 {
		t.Fatalf("vertex count = %d, want 9", out.Len())
	}
	// The output triangles must tile the concave polygon: the summed triangle
	// area equals the polygon's shoelace area.
	inV := in.Vertices()
	polyArea2 := 0.0
	for i := 0; i < len(inV); i++ {
		j := (i + 1) % len(inV)
		polyArea2 += inV[i].Lon*inV[j].Lat - inV[i].Lat*inV[j].Lon
	}
	polyArea := math.Abs(polyArea2) / 2.0

	v := out.Vertices()
	total := 0.0
	for i := 0; i+2 < len(v); i += 3 {
		total += math.Abs(triangleArea2(v[i], v[i+1], v[i+2])) / 2.0
	}
	if math.Abs(total-polyArea) > 1e-9 {
		t.Errorf("triangulated area = %v, want %v", total, polyArea)
	}
}

func TestTriangulateTooFewVertices(t *testing.T) {
	var tri PolygonTriangulation
	in := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0), NewWgs84(1, 0, 0),
	})
	out := tri.TriangulateByEarClipping(in)
	if out.Type() != PolygonUnknown {
		t.Errorf("type = %v, want PolygonUnknown", out.Type())
	}
}

func TestTriangulateWrongType(t *testing.T) {
	var tri PolygonTriangulation
	in := NewWgs84PolygonOfTypeWithVertices(TriangleStrip, []Wgs84{
		NewWgs84(0, 0, 0), NewWgs84(4, 0, 0), NewWgs84(4, 4, 0), NewWgs84(0, 4, 0),
	})
	out := tri.TriangulateByEarClipping(in)
	if out.Type() != PolygonUnknown {
		t.Errorf("type = %v, want PolygonUnknown", out.Type())
	}
}

func TestTriangulateNoEarDegenerate(t *testing.T) {
	var tri PolygonTriangulation
	// All-collinear vertices: no vertex is ever convex, so no ear is found and
	// triangulation fails with UNKNOWN. This exercises the "no ear" branch.
	in := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0), NewWgs84(1, 1, 0), NewWgs84(2, 2, 0), NewWgs84(3, 3, 0),
	})
	out := tri.TriangulateByEarClipping(in)
	if out.Type() != PolygonUnknown {
		t.Errorf("type = %v, want PolygonUnknown", out.Type())
	}
}

func TestTriangulateLargerConvex(t *testing.T) {
	var tri PolygonTriangulation
	// A regular-ish hexagon (CCW). n = 6 -> 3 * (6 - 2) = 12 vertices. This
	// exercises multiple ear-clipping iterations and the relink/update path.
	in := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0),
		NewWgs84(2, 0, 0),
		NewWgs84(3, 2, 0),
		NewWgs84(2, 4, 0),
		NewWgs84(0, 4, 0),
		NewWgs84(-1, 2, 0),
	})
	out := tri.TriangulateByEarClipping(in)
	if out.Type() != TriangleList {
		t.Fatalf("type = %v, want TriangleList", out.Type())
	}
	if out.Len() != 12 {
		t.Fatalf("vertex count = %d, want 12", out.Len())
	}
}

func TestAvgMercatorStretchFinite(t *testing.T) {
	box := NewWgs84AABB(NewWgs84(0, 10, 0), Vec2{X: 20, Y: 10})
	got := box.AvgMercatorStretch()
	if math.IsNaN(got) || math.IsInf(got, 0) {
		t.Errorf("avgMercatorStretch = %v, want a finite value", got)
	}
}

func TestWgs84AabbFromCenterAndTileLimit(t *testing.T) {
	center := NewWgs84(10, 20, 0)
	box := Wgs84AABBFromCenterAndTileLimit(center, 16, 10)
	if !box.Valid() {
		t.Fatal("box should be valid")
	}
	// The center of the constructed box should be (approximately) the input
	// center, since it is built symmetrically around it.
	c := box.Center()
	if math.Abs(c.Longitude()-10) > 1e-9 || math.Abs(c.Latitude()-20) > 1e-9 {
		t.Errorf("center = (%v,%v), want (10,20)", c.Longitude(), c.Latitude())
	}
}

func TestWgs84AabbFromTile(t *testing.T) {
	tile, err := PackedTileIdFromTileIndex(0, 10)
	if err != nil {
		t.Fatalf("setup: %v", err)
	}
	box := Wgs84AABBFromTile(tile)
	if !box.Valid() {
		t.Fatal("tile box should be valid")
	}
	// Level-10 tile width: 2^21 * 360/2^32 = 0.17578125 degrees on both axes.
	const want = 0.17578125
	if math.Abs(box.Size().X-want) > 1e-9 || math.Abs(box.Size().Y-want) > 1e-9 {
		t.Errorf("size = (%v,%v), want (%v,%v)", box.Size().X, box.Size().Y, want, want)
	}
	if box.SW().Longitude() != 0 || box.SW().Latitude() != 0 {
		t.Errorf("sw = (%v,%v), want (0,0)", box.SW().Longitude(), box.SW().Latitude())
	}
}

func TestSplitOverAntiMeridianNoSplit(t *testing.T) {
	// A box that does not extend past LonMax returns ok=false.
	box := NewWgs84AABB(NewWgs84(0, 0, 0), Vec2{X: 10, Y: 5})
	if _, _, ok := box.SplitOverAntiMeridian(); ok {
		t.Error("expected no split for a box well inside the date line")
	}
}

func TestPolygonBaseValidity(t *testing.T) {
	empty := NewPolygon(SimplePolygon)
	if empty.IsValid() {
		t.Error("empty base polygon should be invalid")
	}
	empty.AddVertex(NewWgs84(0, 0, 0))
	if !empty.IsValid() {
		t.Error("base polygon with one vertex should be valid")
	}

	// Wgs84Polygon overrides validity to require >= 3 vertices.
	wp := NewWgs84PolygonWithVertices([]Wgs84{NewWgs84(0, 0, 0), NewWgs84(1, 0, 0)})
	if wp.IsValid() {
		t.Error("Wgs84Polygon with two vertices should be invalid")
	}
	wp.AddVertex(NewWgs84(0, 1, 0))
	if !wp.IsValid() {
		t.Error("Wgs84Polygon with three vertices should be valid")
	}
}

func TestPolygonSetAndTypeAccessors(t *testing.T) {
	p := NewPolygon(PolygonUnknown)
	p.SetType(SimplePolygon)
	if p.Type() != SimplePolygon {
		t.Errorf("type = %v, want SimplePolygon", p.Type())
	}
	p.AddVertices([]Wgs84{NewWgs84(1, 2, 0), NewWgs84(3, 4, 0)})
	p.Set(0, NewWgs84(5, 6, 0))
	if got := p.At(0); got.Longitude() != 5 || got.Latitude() != 6 {
		t.Errorf("At(0) = %v, want (5,6)", got)
	}
	if p.Len() != 2 {
		t.Errorf("Len = %d, want 2", p.Len())
	}
}

func TestEarthWrappingPolyCollidesEverything(t *testing.T) {
	earth := EarthWrappingPoly()
	tri := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0), NewWgs84(4, 0, 0), NewWgs84(0, 4, 0),
	})
	if !earth.CollidesWith(tri) {
		t.Error("earth wrapper should collide with any polygon (earth as receiver)")
	}
	if !tri.CollidesWith(earth) {
		t.Error("earth wrapper should collide with any polygon (earth as argument)")
	}
}

func TestVec2Helpers(t *testing.T) {
	a := NewVec2(3, -4)
	if got := a.Add(NewVec2(1, 2)); got != (Vec2{4, -2}) {
		t.Errorf("Add = %v", got)
	}
	if got := a.Sub(NewVec2(1, 2)); got != (Vec2{2, -6}) {
		t.Errorf("Sub = %v", got)
	}
	if got := a.Scale(2); got != (Vec2{6, -8}) {
		t.Errorf("Scale = %v", got)
	}
	if got := a.Abs(); got != (Vec2{3, 4}) {
		t.Errorf("Abs = %v", got)
	}
}

func TestWgs84GeometryAccessors(t *testing.T) {
	w := NewWgs84(12.5, -7.25, 0)
	if w.Longitude() != 12.5 || w.Dx() != 12.5 {
		t.Errorf("longitude/dx = %v/%v, want 12.5", w.Longitude(), w.Dx())
	}
	if w.Latitude() != -7.25 || w.Dy() != -7.25 {
		t.Errorf("latitude/dy = %v/%v, want -7.25", w.Latitude(), w.Dy())
	}
	if got := w.Sub(NewWgs84(2.5, -1.25, 0)); got.Lon != 10.0 || got.Lat != -6.0 {
		t.Errorf("Sub = %v, want (10,-6)", got)
	}
}

func TestAaBbMinBranches(t *testing.T) {
	// Order vertices so the first vertex is NOT the min corner, exercising the
	// "lon < minLon" and "lat < minLat" update branches in AaBb.
	p := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(10, 10, 0), // start at the NE-ish corner
		NewWgs84(-5, 2, 0),  // smaller lon and lat -> hits both min branches
		NewWgs84(3, 20, 0),  // larger lat -> hits max-lat branch
	})
	aabb := p.AaBb()
	if aabb.SW().Longitude() != -5 || aabb.SW().Latitude() != 2 {
		t.Errorf("sw = (%v,%v), want (-5,2)", aabb.SW().Longitude(), aabb.SW().Latitude())
	}
	if aabb.Size().X != 15 || aabb.Size().Y != 18 {
		t.Errorf("size = %v, want (15,18)", aabb.Size())
	}
}

func TestCollidesWithSeparationViaOtherEdges(t *testing.T) {
	// Two disjoint polygons separated along an axis. CollidesWith must report
	// false. With axis-aligned rectangles, the first SAT pass (this' edges)
	// already finds the separating axis; this simply confirms the false path
	// through both are-separate checks is reachable and correct.
	a := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0), NewWgs84(2, 0, 0), NewWgs84(2, 2, 0), NewWgs84(0, 2, 0),
	})
	b := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(10, 10, 0), NewWgs84(12, 10, 0), NewWgs84(12, 12, 0), NewWgs84(10, 12, 0),
	})
	if a.CollidesWith(b) {
		t.Error("disjoint quads should not collide")
	}

	// A square and a diamond whose axis-aligned projections overlap (so the
	// square's own edge normals do NOT separate them), yet which are separated
	// along one of the diamond's diagonal edge normals. This is the only path
	// that reaches the SECOND are-separate check returning true (the C++
	// (other, other) quirk), driving CollidesWith to false there.
	square := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0), NewWgs84(2, 0, 0), NewWgs84(2, 2, 0), NewWgs84(0, 2, 0),
	})
	diamond := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(4, 2, 0), NewWgs84(2, 4, 0), NewWgs84(0, 6, 0), NewWgs84(6, 0, 0),
	})
	if areSeparate(square, diamond, square) {
		t.Fatal("square's own edge normals should not separate this pair")
	}
	if !areSeparate(square, diamond, diamond) {
		t.Fatal("diamond's edge normals should separate this pair")
	}
	if square.CollidesWith(diamond) {
		t.Error("square and diamond separated only by diamond's diagonal should not collide")
	}
}

func TestNewWgs84PolygonEmpty(t *testing.T) {
	p := NewWgs84Polygon()
	if p.Type() != SimplePolygon {
		t.Errorf("type = %v, want SimplePolygon", p.Type())
	}
	if p.Len() != 0 {
		t.Errorf("len = %d, want 0", p.Len())
	}
	if p.IsValid() {
		t.Error("empty Wgs84Polygon should be invalid")
	}
}

func TestAaBbInvalidPolygonIsDefault(t *testing.T) {
	// Fewer than 3 vertices -> default (empty) AABB with zero size.
	p := NewWgs84PolygonWithVertices([]Wgs84{NewWgs84(0, 0, 0), NewWgs84(1, 0, 0)})
	aabb := p.AaBb()
	if aabb.Size().X != 0 || aabb.Size().Y != 0 {
		t.Errorf("invalid-polygon aabb size = %v, want (0,0)", aabb.Size())
	}
	if !aabb.Valid() {
		t.Error("default aabb should be valid")
	}
}

func TestTriNormalizeZeroVector(t *testing.T) {
	// A polygon with a repeated vertex makes one edge vector zero-length, so
	// triNormalize hits its n == 0 branch during updateVertex. The result is
	// still a TRIANGLE_LIST of the expected size.
	var tri PolygonTriangulation
	in := NewWgs84PolygonWithVertices([]Wgs84{
		NewWgs84(0, 0, 0),
		NewWgs84(4, 0, 0),
		NewWgs84(4, 0, 0), // duplicate -> zero-length edge
		NewWgs84(0, 4, 0),
	})
	out := tri.TriangulateByEarClipping(in)
	if out.Type() != TriangleList {
		t.Fatalf("type = %v, want TriangleList", out.Type())
	}
	if out.Len() != 6 {
		t.Errorf("vertex count = %d, want 6", out.Len())
	}
}

func TestWgs84FromMortonCodeAxes(t *testing.T) {
	// fromMortonCode scales BOTH axes by 360/2^32 (unlike fromNdsCoordinates).
	m := MortonFromNdsCoordinates(0, 0)
	w := Wgs84FromMortonCode(m)
	if w.Lon != 0 || w.Lat != 0 {
		t.Errorf("origin morton -> (%v,%v), want (0,0)", w.Lon, w.Lat)
	}
}
