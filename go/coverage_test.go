// SPDX-License-Identifier: BSD-3-Clause
package ndslivemath

import (
	"strings"
	"testing"
)

func TestPackedTileIdString(t *testing.T) {
	tile, _ := PackedTileIdFromTileIndex(0, 13)
	if s := tile.String(); !strings.Contains(s, "PackedTileId(value=") {
		t.Fatalf("unexpected String(): %q", s)
	}
}

func TestWgs84Equals(t *testing.T) {
	a := NewWgs84(13.404954, 52.520008, 0)
	b := NewWgs84(13.404954, 52.520008, 0)
	if !a.Equals(b) {
		t.Error("equal points should compare Equal")
	}
	if a.Equals(NewWgs84(11.585, 48.137, 0)) {
		t.Error("different points should not compare Equal")
	}
}

func TestFactoryErrors(t *testing.T) {
	if _, err := PackedTileIdFromTileIndex(0, 16); err == nil {
		t.Error("expected error for level 16")
	}
	if _, err := PackedTileIdFromTileIndex(5, 0); err == nil { // max morton at level 0 is 1
		t.Error("expected error for out-of-range morton number")
	}
	if _, err := NewPackedTileIdFromUnsigned(0); err == nil {
		t.Error("expected error for value below the minimum packed tile id")
	}
	if _, err := NewPackedTileIdFromUnsigned(uint64(1) << 16); err != nil {
		t.Errorf("expected a valid level-0 tile, got %v", err)
	}
	m := MortonFromNdsCoordinates(0, 0)
	if _, err := PackedTileIdFromMortonAndLevel(m, 16); err == nil {
		t.Error("expected error for level 16")
	}
}

func TestBoundingBoxFromTileIdsEmpty(t *testing.T) {
	if _, _, _, _, err := BoundingBoxFromTileIds(nil); err == nil {
		t.Error("expected error for an empty tile list")
	}
}

func TestBoundingBoxFromTileIdsMulti(t *testing.T) {
	tiles := GetTileIdsForBoundingBox(0, 0, 1<<28, 1<<28, 3)
	if len(tiles) < 3 {
		t.Fatalf("expected several tiles, got %d", len(tiles))
	}
	// Order as [middle, SW-most, NE-most] so every min/max update branch fires.
	ordered := []PackedTileId{tiles[len(tiles)/2], tiles[0], tiles[len(tiles)-1]}
	minX, minY, maxX, maxY, err := BoundingBoxFromTileIds(ordered)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if minX > maxX || minY > maxY {
		t.Errorf("degenerate box: %d,%d,%d,%d", minX, minY, maxX, maxY)
	}
}

func TestMortonYWrap(t *testing.T) {
	// y outside [-2^30, 2^30) exercises the wrap loops (x is full int32, so its
	// wrap loops are unreachable from this API).
	if _, y := MortonFromNdsCoordinates(0, 1<<30).ToNdsCoordinates(); y != -(1 << 30) {
		t.Errorf("y=2^30 should wrap to %d, got %d", -(1 << 30), y)
	}
	// Negative out-of-range y exercises the other wrap loop.
	_, _ = MortonFromNdsCoordinates(0, -(1<<30)-1).ToNdsCoordinates()
}
