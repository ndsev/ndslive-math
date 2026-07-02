// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

import (
	"math"
	"testing"
)

func TestWgs84NormalizeWrapLongitude(t *testing.T) {
	cases := []struct {
		in, want float64
	}{
		{360.5, 0.5},
		{-360.5, -0.5},
		{181.0, -179.0},
		{-181.0, 179.0},
		{0.0, 0.0},
	}
	for _, c := range cases {
		w := NewWgs84(c.in, 0, 0)
		if !floatClose(w.Lon, c.want, 1e-9) {
			t.Errorf("NewWgs84(%v).Lon = %v, want %v", c.in, w.Lon, c.want)
		}
	}
}

func TestWgs84NormalizeClampLatitude(t *testing.T) {
	w := NewWgs84(0, 95, 0)
	if w.Lat != 90.0-LatNdsDelta {
		t.Errorf("clamp high: got %v, want %v", w.Lat, 90.0-LatNdsDelta)
	}
	w = NewWgs84(0, -95, 0)
	if w.Lat != -90.0 {
		t.Errorf("clamp low: got %v, want %v", w.Lat, -90.0)
	}
}

func TestToNdsUsesFloorNotTruncation(t *testing.T) {
	// A tiny negative longitude must floor toward -infinity, i.e. produce -12
	// (per the parity vector lon=-1e-06 -> nds_x=-12), not 0 (truncation) and
	// not -11.
	w := NewWgs84(-1e-06, -1e-06, 0)
	x, y := w.ToNdsCoordinates()
	if x != -12 || y != -12 {
		t.Errorf("floor conversion: got (%d,%d), want (-12,-12)", x, y)
	}
}

func TestWgs84RoundTrip(t *testing.T) {
	originals := []Wgs84{
		NewWgs84(13.404954, 52.520008, 0),
		NewWgs84(-122.4194, 37.7749, 0),
		NewWgs84(151.2093, -33.8688, 0),
	}
	for _, w := range originals {
		x, y := w.ToNdsCoordinates()
		back := Wgs84FromNdsCoordinates(x, y)
		// Round-trip is lossy at full precision but should be within one NDS
		// step (~8.4e-8 deg for lon, ~8.4e-8 deg for lat).
		if math.Abs(back.Lon-w.Lon) > 1e-6 {
			t.Errorf("lon round-trip: got %v, want ~%v", back.Lon, w.Lon)
		}
		if math.Abs(back.Lat-w.Lat) > 1e-6 {
			t.Errorf("lat round-trip: got %v, want ~%v", back.Lat, w.Lat)
		}
	}
}

func TestToDegreeMinutesSeconds(t *testing.T) {
	// 52.520008 deg -> 52° 31' 12.03" N (approx).
	w := NewWgs84(13.404954, 52.520008, 0)
	latStr, lonStr := w.ToDegreeMinutesSeconds()
	if len(latStr) == 0 || latStr[len(latStr)-1] != 'N' {
		t.Errorf("expected northern hemisphere, got %q", latStr)
	}
	if len(lonStr) == 0 || lonStr[len(lonStr)-1] != 'E' {
		t.Errorf("expected eastern hemisphere, got %q", lonStr)
	}

	// Southern / western hemisphere suffixes.
	s := NewWgs84(-43.1729, -22.9068, 0)
	latStr, lonStr = s.ToDegreeMinutesSeconds()
	if latStr[len(latStr)-1] != 'S' {
		t.Errorf("expected S suffix, got %q", latStr)
	}
	if lonStr[len(lonStr)-1] != 'W' {
		t.Errorf("expected W suffix, got %q", lonStr)
	}
}

func TestMortonRoundTrip(t *testing.T) {
	coords := [][2]int32{
		{0, 0}, {1, 0}, {0, 1}, {1, 1},
		{12345, 6789}, {-12345, -6789},
		{2147483647, 1073741823}, {-2147483648, -1073741824},
		{1000000000, -1000000000},
	}
	for _, c := range coords {
		m := MortonFromNdsCoordinates(c[0], c[1])
		x, y := m.ToNdsCoordinates()
		if x != c[0] || y != c[1] {
			t.Errorf("morton round-trip (%d,%d): got (%d,%d)", c[0], c[1], x, y)
		}
	}
}

func TestMortonMasksBit63(t *testing.T) {
	// The encoder must never set bit 63.
	m := MortonFromNdsCoordinates(-2147483648, -1073741824)
	if m.Value()&(uint64(1)<<63) != 0 {
		t.Errorf("bit 63 set in morton value %d", m.Value())
	}
}

func TestPackedTileIdSignedUnsignedEquivalence(t *testing.T) {
	signed, err := NewPackedTileId(-2147483648)
	if err != nil {
		t.Fatalf("signed ctor error: %v", err)
	}
	unsigned, err := NewPackedTileIdFromUnsigned(2147483648)
	if err != nil {
		t.Fatalf("unsigned ctor error: %v", err)
	}
	if signed.Value() != unsigned.Value() {
		t.Errorf("signed value %d != unsigned value %d", signed.Value(), unsigned.Value())
	}
	if signed.Value() != -2147483648 {
		t.Errorf("level-15 value should be -2147483648, got %d", signed.Value())
	}
	if signed.Level() != 15 {
		t.Errorf("level should be 15, got %d", signed.Level())
	}
	if signed.MortonNumber() != 0 {
		t.Errorf("morton number should be 0, got %d", signed.MortonNumber())
	}
}

func TestPackedTileIdMaxLevel15(t *testing.T) {
	tile, err := PackedTileIdFromTileIndex((1<<31)-1, 15)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if tile.Value() != -1 {
		t.Errorf("max level-15 tile value should be -1, got %d", tile.Value())
	}
}

func TestPackedTileIdInvalid(t *testing.T) {
	if _, err := PackedTileIdFromTileIndex(0, 16); err == nil {
		t.Error("expected error for level 16")
	}
	if _, err := PackedTileIdFromTileIndex(0, -1); err == nil {
		t.Error("expected error for level -1")
	}
	// Morton number too large for level 2 (max = 2^5-1 = 31).
	if _, err := PackedTileIdFromTileIndex(32, 2); err == nil {
		t.Error("expected error for morton 32 at level 2")
	}
	// Value below minimum (< 2^16).
	if _, err := NewPackedTileId(100); err == nil {
		t.Error("expected error for value 100 (< 2^16)")
	}
}

func TestPackedTileIdAddedFactoriesAndGridCoordinates(t *testing.T) {
	tile, err := PackedTileIdFromTileXY(3, 1, 1)
	if err != nil {
		t.Fatalf("PackedTileIdFromTileXY error: %v", err)
	}
	if tile.Value() != 131079 || tile.X() != 3 || tile.Y() != 1 {
		t.Errorf("from tile xy = value %d grid (%d,%d), want 131079 grid (3,1)", tile.Value(), tile.X(), tile.Y())
	}
	if lon, lat := tile.CenterWgs84(); lon != -45.0 || lat != -45.0 {
		t.Errorf("CenterWgs84 = (%v,%v), want (-45,-45)", lon, lat)
	}
	if lon, lat := tile.SouthWestWgs84(); lon != -90.0 || lat != -90.0 {
		t.Errorf("SouthWestWgs84 = (%v,%v), want (-90,-90)", lon, lat)
	}
	if lon, lat := tile.NorthEastWgs84(); lon != 0.0 || lat != 0.0 {
		t.Errorf("NorthEastWgs84 = (%v,%v), want (0,0)", lon, lat)
	}
	if lon, lat := tile.Wgs84Size(); lon != 90.0 || lat != 90.0 {
		t.Errorf("Wgs84Size = (%v,%v), want (90,90)", lon, lat)
	}

	fromValue, err := PackedTileIdFromValue(tile.Value())
	if err != nil {
		t.Fatalf("PackedTileIdFromValue error: %v", err)
	}
	if fromValue.Value() != tile.Value() {
		t.Errorf("from value = %d, want %d", fromValue.Value(), tile.Value())
	}

	fromNds, err := PackedTileIdFromNdsCoordinates(-1, -1, 15)
	if err != nil {
		t.Fatalf("PackedTileIdFromNdsCoordinates error: %v", err)
	}
	fromWgs, err := PackedTileIdFromWgs84(-0.005493205972015858, -0.005493205972015858, 15)
	if err != nil {
		t.Fatalf("PackedTileIdFromWgs84 error: %v", err)
	}
	if fromNds.Level() != 15 || fromWgs.Value() != -4 {
		t.Errorf("coordinate factories = level %d value %d, want level 15 value -4", fromNds.Level(), fromWgs.Value())
	}

	lon, lat := PackedTileIdWgs84FromNdsCoordinates(1<<31, 1<<30)
	if lon != 180.0 || lat != 90.0 {
		t.Errorf("PackedTileIdWgs84FromNdsCoordinates = (%v,%v), want (180,90)", lon, lat)
	}
}

func TestPackedTileIdAddedFactoryValidation(t *testing.T) {
	if _, err := PackedTileIdFromValue(0); err == nil {
		t.Error("expected error for invalid packed value")
	}
	if _, err := PackedTileIdFromTileXY(0, 0, -1); err == nil {
		t.Error("expected error for invalid tile xy level")
	}
	if _, err := PackedTileIdFromTileXY(4, 0, 1); err == nil {
		t.Error("expected error for x outside level range")
	}
	if _, err := PackedTileIdFromTileXY(0, 2, 1); err == nil {
		t.Error("expected error for y outside level range")
	}
	if _, err := PackedTileIdFromNdsCoordinates(0, 0, 16); err == nil {
		t.Error("expected error for invalid NDS factory level")
	}
	if _, err := PackedTileIdFromWgs84(0, 0, 16); err == nil {
		t.Error("expected error for invalid WGS84 factory level")
	}
}

func TestNorthEastCornerExclusive(t *testing.T) {
	// Level 0, morton 0: NE corner is the exclusive 2^31 in both axes.
	tile, err := PackedTileIdFromTileIndex(0, 0)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	neX, neY := tile.NorthEastCorner()
	if neX != int64(1)<<31 || neY != int64(1)<<31 {
		t.Errorf("NE corner = (%d,%d), want (%d,%d)", neX, neY, int64(1)<<31, int64(1)<<31)
	}
	swX, swY := tile.SouthWestCorner()
	if swX != 0 || swY != 0 {
		t.Errorf("SW corner = (%d,%d), want (0,0)", swX, swY)
	}
}

func TestPackedTileIdRelativeNeighbour(t *testing.T) {
	tile, err := PackedTileIdFromTileXY(0, 0, 1)
	if err != nil {
		t.Fatalf("PackedTileIdFromTileXY error: %v", err)
	}
	if got := tile.Neighbour(1, 0); got.Value() != tile.EastNeighbour().Value() {
		t.Errorf("Neighbour(1,0) = %d, want east %d", got.Value(), tile.EastNeighbour().Value())
	}
	if got := tile.Neighbour(0, 1); got.Value() != tile.NorthNeighbour().Value() {
		t.Errorf("Neighbour(0,1) = %d, want north %d", got.Value(), tile.NorthNeighbour().Value())
	}
	wrapped, err := PackedTileIdFromTileXY(3, 1, 1)
	if err != nil {
		t.Fatalf("PackedTileIdFromTileXY wrapped error: %v", err)
	}
	if got := tile.Neighbour(-1, -1); got.Value() != wrapped.Value() {
		t.Errorf("Neighbour(-1,-1) = %d, want %d", got.Value(), wrapped.Value())
	}
	if got := tile.Neighbour(4, 2); got.Value() != tile.Value() {
		t.Errorf("Neighbour(4,2) = %d, want %d", got.Value(), tile.Value())
	}
	if got := tile.Neighbor(4, 2); got.Value() != tile.Neighbour(4, 2).Value() {
		t.Errorf("Neighbor alias = %d, want %d", got.Value(), tile.Neighbour(4, 2).Value())
	}
}

func TestNeighbourWrapAround(t *testing.T) {
	// Going east then west should return to the original tile, and vice versa.
	tile, err := PackedTileIdFromTileIndex(0, 2)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if got := tile.EastNeighbour().WestNeighbour().Value(); got != tile.Value() {
		t.Errorf("east-then-west = %d, want %d", got, tile.Value())
	}
	if got := tile.NorthNeighbour().SouthNeighbour().Value(); got != tile.Value() {
		t.Errorf("north-then-south = %d, want %d", got, tile.Value())
	}
}

func TestFloorDiv(t *testing.T) {
	cases := []struct {
		a, b, want int64
	}{
		{7, 2, 3},
		{-7, 2, -4}, // floor, not -3 (truncation)
		{-1, 1073741824, -1},
		{-1073741824, 1073741824, -1},
		{0, 4, 0},
		{8, 4, 2},
	}
	for _, c := range cases {
		if got := floorDiv(c.a, c.b); got != c.want {
			t.Errorf("floorDiv(%d,%d) = %d, want %d", c.a, c.b, got, c.want)
		}
	}
}

func TestBoundingBoxFromTilesEmpty(t *testing.T) {
	if _, _, _, _, err := BoundingBoxFromTileIds(nil); err == nil {
		t.Error("expected error for empty tiles slice")
	}
}

func TestBboxFromTileRoundTrip(t *testing.T) {
	// A single-tile bbox must round-trip to exactly that tile at the same level.
	tile, err := PackedTileIdFromTileIndex(12345, 13)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	minX, minY, maxX, maxY, err := BoundingBoxFromTileIds([]PackedTileId{tile})
	if err != nil {
		t.Fatalf("bbox error: %v", err)
	}
	tiles := GetTileIdsForBoundingBox(int32(minX), int32(minY), int32(maxX), int32(maxY), 13)
	if len(tiles) != 1 || tiles[0].Value() != tile.Value() {
		t.Errorf("round-trip returned %d tiles (first=%v), want exactly [%v]", len(tiles), tiles, tile.Value())
	}
}

func TestNdsBoundingBoxIntersectsContains(t *testing.T) {
	a := NdsBoundingBox{MinX: 0, MinY: 0, MaxX: 100, MaxY: 100}
	b := NdsBoundingBox{MinX: 50, MinY: 50, MaxX: 150, MaxY: 150}
	if !a.Intersects(b) {
		t.Error("a should intersect b")
	}
	if a.Contains(b) {
		t.Error("a should not contain b")
	}
	inner := NdsBoundingBox{MinX: 10, MinY: 10, MaxX: 20, MaxY: 20}
	if !a.Contains(inner) {
		t.Error("a should contain inner")
	}
	far := NdsBoundingBox{MinX: 200, MinY: 200, MaxX: 300, MaxY: 300}
	if a.Intersects(far) {
		t.Error("a should not intersect far")
	}
}

func TestNdsBoundingBoxFromTile(t *testing.T) {
	tile, err := PackedTileIdFromTileIndex(0, 1)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	box := NdsBoundingBoxFromTile(tile)
	if box.MinX != 0 || box.MinY != 0 {
		t.Errorf("min = (%d,%d), want (0,0)", box.MinX, box.MinY)
	}
	// NE corner (exclusive) is 2^30 for a level-1 tile at morton 0.
	if box.MaxX != int32(1<<30) || box.MaxY != int32(1<<30) {
		t.Errorf("max = (%d,%d), want (%d,%d)", box.MaxX, box.MaxY, int32(1<<30), int32(1<<30))
	}
}

func TestDimensionsInMeters(t *testing.T) {
	// At the equator a level-1 tile (size 2^30) is wider than tall; the width
	// and height should both be positive and finite.
	tile, err := PackedTileIdFromTileIndex(0, 1)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	w, h := tile.DimensionsInMeters()
	if w <= 0 || h <= 0 || math.IsInf(w, 0) || math.IsInf(h, 0) {
		t.Errorf("dimensions = (%v,%v), expected positive finite", w, h)
	}
}
