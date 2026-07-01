// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

import (
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"testing"
)

// parityData is the decoded form of test-vectors/parity_vectors.json.
type parityData struct {
	Meta struct {
		FloatTolerance float64 `json:"float_tolerance"`
	} `json:"_meta"`

	Wgs84ToNds []struct {
		Lon           float64 `json:"lon"`
		Lat           float64 `json:"lat"`
		NormalizedLon float64 `json:"normalized_lon"`
		NormalizedLat float64 `json:"normalized_lat"`
		NdsX          int32   `json:"nds_x"`
		NdsY          int32   `json:"nds_y"`
	} `json:"wgs84_to_nds"`

	NdsToWgs84 []struct {
		X   int32   `json:"x"`
		Y   int32   `json:"y"`
		Lon float64 `json:"lon"`
		Lat float64 `json:"lat"`
	} `json:"nds_to_wgs84"`

	Morton []struct {
		X        int32  `json:"x"`
		Y        int32  `json:"y"`
		Morton   string `json:"morton"`
		DecodedX int32  `json:"decoded_x"`
		DecodedY int32  `json:"decoded_y"`
	} `json:"morton"`

	PackedTileFromIndex []struct {
		MortonNumber         uint32   `json:"morton_number"`
		Level                int      `json:"level"`
		Value                int32    `json:"value"`
		ComputedLevel        int      `json:"computed_level"`
		ComputedMortonNumber uint32   `json:"computed_morton_number"`
		GridX                uint32   `json:"grid_x"`
		GridY                uint32   `json:"grid_y"`
		Size                 uint64   `json:"size"`
		SW                   [2]int64 `json:"sw"`
		NE                   [2]int64 `json:"ne"`
		Center               [2]int64 `json:"center"`
	} `json:"packed_tile_from_index"`

	TileNeighbours []struct {
		MortonNumber uint32 `json:"morton_number"`
		Level        int    `json:"level"`
		West         int32  `json:"west"`
		East         int32  `json:"east"`
		South        int32  `json:"south"`
		North        int32  `json:"north"`
	} `json:"tile_neighbours"`

	FromMortonAndLevel []struct {
		X                    int32  `json:"x"`
		Y                    int32  `json:"y"`
		Level                int    `json:"level"`
		Value                int32  `json:"value"`
		ComputedLevel        int    `json:"computed_level"`
		ComputedMortonNumber uint32 `json:"computed_morton_number"`
	} `json:"from_morton_and_level"`

	PackedTileFromWgs84 []struct {
		Lon                  float64 `json:"lon"`
		Lat                  float64 `json:"lat"`
		Level                int     `json:"level"`
		Value                int32   `json:"value"`
		ComputedMortonNumber uint32  `json:"computed_morton_number"`
		GridX                uint32  `json:"grid_x"`
		GridY                uint32  `json:"grid_y"`
	} `json:"packed_tile_from_wgs84"`

	TilesForBbox []struct {
		SwX        int32   `json:"sw_x"`
		SwY        int32   `json:"sw_y"`
		NeX        int32   `json:"ne_x"`
		NeY        int32   `json:"ne_y"`
		Level      int     `json:"level"`
		TileValues []int32 `json:"tile_values"`
	} `json:"tiles_for_bbox"`

	BboxFromTiles []struct {
		TileValues []int32  `json:"tile_values"`
		Result     [4]int64 `json:"result"`
	} `json:"bbox_from_tiles"`

	NdsBboxOps []struct {
		A          [4]int32 `json:"a"`
		B          [4]int32 `json:"b"`
		Intersects bool     `json:"intersects"`
		AContainsB bool     `json:"a_contains_b"`
	} `json:"nds_bbox_ops"`

	NdsBboxFromWgs84 []struct {
		SW   [2]float64 `json:"sw"`
		NE   [2]float64 `json:"ne"`
		MinX int32      `json:"min_x"`
		MinY int32      `json:"min_y"`
		MaxX int32      `json:"max_x"`
		MaxY int32      `json:"max_y"`
	} `json:"nds_bbox_from_wgs84"`

	DistanceBearing []struct {
		A          [2]float64 `json:"a"`
		B          [2]float64 `json:"b"`
		DistanceM  float64    `json:"distance_m"`
		BearingRad float64    `json:"bearing_rad"`
	} `json:"distance_bearing"`

	NdsDistanceToMeters []struct {
		NdsX       float64 `json:"nds_x"`
		NdsY       float64 `json:"nds_y"`
		AtLatitude float64 `json:"at_latitude"`
		WidthM     float64 `json:"width_m"`
		HeightM    float64 `json:"height_m"`
	} `json:"nds_distance_to_meters"`

	Wgs84Aabb []struct {
		Name                  string      `json:"name"`
		SwLon                 float64     `json:"sw_lon"`
		SwLat                 float64     `json:"sw_lat"`
		SizeX                 float64     `json:"size_x"`
		SizeY                 float64     `json:"size_y"`
		Valid                 bool        `json:"valid"`
		StoredSize            [2]float64  `json:"stored_size"`
		SW                    [2]float64  `json:"sw"`
		SE                    [2]float64  `json:"se"`
		NE                    [2]float64  `json:"ne"`
		NW                    [2]float64  `json:"nw"`
		Center                [2]float64  `json:"center"`
		Vertices              [][]float64 `json:"vertices"`
		ContainsAntiMeridian  bool        `json:"contains_anti_meridian"`
		SplitOverAntiMeridian *struct {
			LeftSW    [2]float64 `json:"left_sw"`
			LeftSize  [2]float64 `json:"left_size"`
			RightSW   [2]float64 `json:"right_sw"`
			RightSize [2]float64 `json:"right_size"`
		} `json:"split_over_anti_meridian"`
		NumTileIds    []int `json:"num_tile_ids"`
		TileLevelMin8 int   `json:"tile_level_min8"`
		TileLevelMin2 int   `json:"tile_level_min2"`
	} `json:"wgs84_aabb"`

	Wgs84AabbContains []struct {
		Box      string  `json:"box"`
		PointLon float64 `json:"point_lon"`
		PointLat float64 `json:"point_lat"`
		Contains bool    `json:"contains"`
	} `json:"wgs84_aabb_contains"`

	Wgs84AabbIntersects []struct {
		A          string `json:"a"`
		B          string `json:"b"`
		Intersects bool   `json:"intersects"`
	} `json:"wgs84_aabb_intersects"`

	PolygonOrientation []struct {
		Name        string      `json:"name"`
		PolygonType int         `json:"polygon_type"`
		Vertices    [][]float64 `json:"vertices"`
		Orientation int         `json:"orientation"`
		IsValid     bool        `json:"is_valid"`
	} `json:"polygon_orientation"`

	Wgs84Polygon []struct {
		Name      string      `json:"name"`
		Vertices  [][]float64 `json:"vertices"`
		IsValid   bool        `json:"is_valid"`
		AabbSW    [2]float64  `json:"aabb_sw"`
		AabbSize  [2]float64  `json:"aabb_size"`
		MedianLon float64     `json:"median_lon"`
		MedianLat float64     `json:"median_lat"`
	} `json:"wgs84_polygon"`

	Wgs84PolygonCollision []struct {
		A          string      `json:"a"`
		AVertices  [][]float64 `json:"a_vertices"`
		B          string      `json:"b"`
		BVertices  [][]float64 `json:"b_vertices"`
		ACollidesB bool        `json:"a_collides_b"`
		BCollidesA bool        `json:"b_collides_a"`
	} `json:"wgs84_polygon_collision"`
}

// loadParity locates and parses the golden parity vectors relative to this
// test file (go/parity_vectors_test.go -> ../test-vectors/parity_vectors.json).
func loadParity(t *testing.T) parityData {
	t.Helper()
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("could not determine test file location via runtime.Caller")
	}
	path := filepath.Join(filepath.Dir(thisFile), "..", "test-vectors", "parity_vectors.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("reading parity vectors at %s: %v", path, err)
	}
	var data parityData
	if err := json.Unmarshal(raw, &data); err != nil {
		t.Fatalf("parsing parity vectors: %v", err)
	}
	return data
}

func floatClose(a, b, tol float64) bool {
	if math.IsNaN(a) || math.IsNaN(b) {
		return false
	}
	return math.Abs(a-b) <= tol
}

func TestParityWgs84ToNds(t *testing.T) {
	data := loadParity(t)
	tol := data.Meta.FloatTolerance
	for i, c := range data.Wgs84ToNds {
		w := NewWgs84(c.Lon, c.Lat, 0)
		if !floatClose(w.Lon, c.NormalizedLon, tol) {
			t.Errorf("case %d: normalized lon = %v, want %v", i, w.Lon, c.NormalizedLon)
		}
		if !floatClose(w.Lat, c.NormalizedLat, tol) {
			t.Errorf("case %d: normalized lat = %v, want %v", i, w.Lat, c.NormalizedLat)
		}
		x, y := w.ToNdsCoordinates()
		if x != c.NdsX {
			t.Errorf("case %d (lon=%v lat=%v): nds_x = %d, want %d", i, c.Lon, c.Lat, x, c.NdsX)
		}
		if y != c.NdsY {
			t.Errorf("case %d (lon=%v lat=%v): nds_y = %d, want %d", i, c.Lon, c.Lat, y, c.NdsY)
		}
	}
}

func TestParityNdsToWgs84(t *testing.T) {
	data := loadParity(t)
	tol := data.Meta.FloatTolerance
	for i, c := range data.NdsToWgs84 {
		w := Wgs84FromNdsCoordinates(c.X, c.Y)
		if !floatClose(w.Lon, c.Lon, tol) {
			t.Errorf("case %d (x=%d y=%d): lon = %v, want %v", i, c.X, c.Y, w.Lon, c.Lon)
		}
		if !floatClose(w.Lat, c.Lat, tol) {
			t.Errorf("case %d (x=%d y=%d): lat = %v, want %v", i, c.X, c.Y, w.Lat, c.Lat)
		}
	}
}

func TestParityMorton(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.Morton {
		want, err := strconv.ParseUint(c.Morton, 10, 64)
		if err != nil {
			t.Fatalf("case %d: cannot parse morton %q: %v", i, c.Morton, err)
		}
		m := MortonFromNdsCoordinates(c.X, c.Y)
		if m.Value() != want {
			t.Errorf("case %d (x=%d y=%d): morton = %d, want %d", i, c.X, c.Y, m.Value(), want)
		}
		dx, dy := NewMortonCode(want).ToNdsCoordinates()
		if dx != c.DecodedX || dy != c.DecodedY {
			t.Errorf("case %d: decode(%d) = (%d,%d), want (%d,%d)", i, want, dx, dy, c.DecodedX, c.DecodedY)
		}
	}
}

func TestParityPackedTileFromIndex(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.PackedTileFromIndex {
		tile, err := PackedTileIdFromTileIndex(c.MortonNumber, c.Level)
		if err != nil {
			t.Fatalf("case %d: PackedTileIdFromTileIndex(%d,%d) error: %v", i, c.MortonNumber, c.Level, err)
		}
		if tile.Value() != c.Value {
			t.Errorf("case %d: value = %d, want %d", i, tile.Value(), c.Value)
		}
		if tile.Level() != c.ComputedLevel {
			t.Errorf("case %d: level = %d, want %d", i, tile.Level(), c.ComputedLevel)
		}
		if tile.MortonNumber() != c.ComputedMortonNumber {
			t.Errorf("case %d: morton = %d, want %d", i, tile.MortonNumber(), c.ComputedMortonNumber)
		}
		if tile.X() != c.GridX || tile.Y() != c.GridY {
			t.Errorf("case %d: grid = (%d,%d), want (%d,%d)", i, tile.X(), tile.Y(), c.GridX, c.GridY)
		}
		if uint64(tile.Size()) != c.Size {
			t.Errorf("case %d: size = %d, want %d", i, tile.Size(), c.Size)
		}
		swX, swY := tile.SouthWestCorner()
		if swX != c.SW[0] || swY != c.SW[1] {
			t.Errorf("case %d: sw = (%d,%d), want (%d,%d)", i, swX, swY, c.SW[0], c.SW[1])
		}
		neX, neY := tile.NorthEastCorner()
		if neX != c.NE[0] || neY != c.NE[1] {
			t.Errorf("case %d: ne = (%d,%d), want (%d,%d)", i, neX, neY, c.NE[0], c.NE[1])
		}
		cX, cY := tile.Center()
		if cX != c.Center[0] || cY != c.Center[1] {
			t.Errorf("case %d: center = (%d,%d), want (%d,%d)", i, cX, cY, c.Center[0], c.Center[1])
		}

		// Constructing from the signed value must reproduce the same tile.
		fromSigned, err := NewPackedTileId(c.Value)
		if err != nil {
			t.Fatalf("case %d: NewPackedTileId(%d) error: %v", i, c.Value, err)
		}
		if fromSigned.Value() != c.Value {
			t.Errorf("case %d: NewPackedTileId round-trip value = %d, want %d", i, fromSigned.Value(), c.Value)
		}
		fromValue, err := PackedTileIdFromValue(c.Value)
		if err != nil {
			t.Fatalf("case %d: PackedTileIdFromValue(%d) error: %v", i, c.Value, err)
		}
		if fromValue.Value() != c.Value {
			t.Errorf("case %d: PackedTileIdFromValue value = %d, want %d", i, fromValue.Value(), c.Value)
		}
		fromXY, err := PackedTileIdFromTileXY(c.GridX, c.GridY, c.Level)
		if err != nil {
			t.Fatalf("case %d: PackedTileIdFromTileXY error: %v", i, err)
		}
		if fromXY.Value() != c.Value {
			t.Errorf("case %d: PackedTileIdFromTileXY value = %d, want %d", i, fromXY.Value(), c.Value)
		}
	}
}

func TestParityTileNeighbours(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.TileNeighbours {
		tile, err := PackedTileIdFromTileIndex(c.MortonNumber, c.Level)
		if err != nil {
			t.Fatalf("case %d: setup error: %v", i, err)
		}
		if got := tile.WestNeighbour().Value(); got != c.West {
			t.Errorf("case %d: west = %d, want %d", i, got, c.West)
		}
		if got := tile.EastNeighbour().Value(); got != c.East {
			t.Errorf("case %d: east = %d, want %d", i, got, c.East)
		}
		if got := tile.SouthNeighbour().Value(); got != c.South {
			t.Errorf("case %d: south = %d, want %d", i, got, c.South)
		}
		if got := tile.NorthNeighbour().Value(); got != c.North {
			t.Errorf("case %d: north = %d, want %d", i, got, c.North)
		}
	}
}

func TestParityFromMortonAndLevel(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.FromMortonAndLevel {
		m := MortonFromNdsCoordinates(c.X, c.Y)
		tile, err := PackedTileIdFromMortonAndLevel(m, c.Level)
		if err != nil {
			t.Fatalf("case %d: error: %v", i, err)
		}
		if tile.Value() != c.Value {
			t.Errorf("case %d: value = %d, want %d", i, tile.Value(), c.Value)
		}
		if tile.Level() != c.ComputedLevel {
			t.Errorf("case %d: level = %d, want %d", i, tile.Level(), c.ComputedLevel)
		}
		if tile.MortonNumber() != c.ComputedMortonNumber {
			t.Errorf("case %d: morton = %d, want %d", i, tile.MortonNumber(), c.ComputedMortonNumber)
		}
		fromNds, err := PackedTileIdFromNdsCoordinates(c.X, c.Y, c.Level)
		if err != nil {
			t.Fatalf("case %d: PackedTileIdFromNdsCoordinates error: %v", i, err)
		}
		if fromNds.Value() != c.Value {
			t.Errorf("case %d: PackedTileIdFromNdsCoordinates value = %d, want %d", i, fromNds.Value(), c.Value)
		}
	}
}

func TestParityPackedTileFromWgs84(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.PackedTileFromWgs84 {
		tile, err := PackedTileIdFromWgs84(c.Lon, c.Lat, c.Level)
		if err != nil {
			t.Fatalf("case %d: PackedTileIdFromWgs84 error: %v", i, err)
		}
		if tile.Value() != c.Value {
			t.Errorf("case %d: value = %d, want %d", i, tile.Value(), c.Value)
		}
		if tile.MortonNumber() != c.ComputedMortonNumber {
			t.Errorf("case %d: morton = %d, want %d", i, tile.MortonNumber(), c.ComputedMortonNumber)
		}
		if tile.X() != c.GridX || tile.Y() != c.GridY {
			t.Errorf("case %d: grid = (%d,%d), want (%d,%d)", i, tile.X(), tile.Y(), c.GridX, c.GridY)
		}
	}
}

func TestParityTilesForBbox(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.TilesForBbox {
		tiles := GetTileIdsForBoundingBox(c.SwX, c.SwY, c.NeX, c.NeY, c.Level)
		if len(tiles) != len(c.TileValues) {
			t.Errorf("case %d: got %d tiles, want %d", i, len(tiles), len(c.TileValues))
			continue
		}
		for j, tile := range tiles {
			if tile.Value() != c.TileValues[j] {
				t.Errorf("case %d tile %d: value = %d, want %d", i, j, tile.Value(), c.TileValues[j])
			}
		}
	}
}

func TestParityBboxFromTiles(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.BboxFromTiles {
		tiles := make([]PackedTileId, 0, len(c.TileValues))
		for _, v := range c.TileValues {
			tile, err := NewPackedTileId(v)
			if err != nil {
				t.Fatalf("case %d: NewPackedTileId(%d) error: %v", i, v, err)
			}
			tiles = append(tiles, tile)
		}
		minX, minY, maxX, maxY, err := BoundingBoxFromTileIds(tiles)
		if err != nil {
			t.Fatalf("case %d: error: %v", i, err)
		}
		if minX != c.Result[0] || minY != c.Result[1] || maxX != c.Result[2] || maxY != c.Result[3] {
			t.Errorf("case %d: bbox = (%d,%d,%d,%d), want (%d,%d,%d,%d)",
				i, minX, minY, maxX, maxY, c.Result[0], c.Result[1], c.Result[2], c.Result[3])
		}
	}
}

func TestParityNdsBboxOps(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.NdsBboxOps {
		a := NdsBoundingBox{MinX: c.A[0], MinY: c.A[1], MaxX: c.A[2], MaxY: c.A[3]}
		b := NdsBoundingBox{MinX: c.B[0], MinY: c.B[1], MaxX: c.B[2], MaxY: c.B[3]}
		if got := a.Intersects(b); got != c.Intersects {
			t.Errorf("case %d: a.Intersects(b) = %v, want %v", i, got, c.Intersects)
		}
		if got := a.Contains(b); got != c.AContainsB {
			t.Errorf("case %d: a.Contains(b) = %v, want %v", i, got, c.AContainsB)
		}
	}
}

func TestParityNdsBboxFromWgs84(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.NdsBboxFromWgs84 {
		sw := NewWgs84(c.SW[0], c.SW[1], 0)
		ne := NewWgs84(c.NE[0], c.NE[1], 0)
		box := NdsBoundingBoxFromWgs84Corners(sw, ne)
		if box.MinX != c.MinX || box.MinY != c.MinY || box.MaxX != c.MaxX || box.MaxY != c.MaxY {
			t.Errorf("case %d: box = (%d,%d,%d,%d), want (%d,%d,%d,%d)",
				i, box.MinX, box.MinY, box.MaxX, box.MaxY, c.MinX, c.MinY, c.MaxX, c.MaxY)
		}
	}
}

func TestParityDistanceBearing(t *testing.T) {
	data := loadParity(t)
	tol := data.Meta.FloatTolerance
	for i, c := range data.DistanceBearing {
		a := NewWgs84(c.A[0], c.A[1], 0)
		b := NewWgs84(c.B[0], c.B[1], 0)
		// Python: a.distance_to(b) and a.bearing_from(b).
		if d := a.DistanceTo(b); !floatClose(d, c.DistanceM, tol) {
			t.Errorf("case %d: distance = %v, want %v", i, d, c.DistanceM)
		}
		if br := a.BearingFrom(b); !floatClose(br, c.BearingRad, tol) {
			t.Errorf("case %d: bearing = %v, want %v", i, br, c.BearingRad)
		}
	}
}

func TestParityNdsDistanceToMeters(t *testing.T) {
	data := loadParity(t)
	tol := data.Meta.FloatTolerance
	for i, c := range data.NdsDistanceToMeters {
		w, h := NdsDistanceToMeters(c.NdsX, c.NdsY, c.AtLatitude)
		if !floatClose(w, c.WidthM, tol) {
			t.Errorf("case %d: width = %v, want %v", i, w, c.WidthM)
		}
		if !floatClose(h, c.HeightM, tol) {
			t.Errorf("case %d: height = %v, want %v", i, h, c.HeightM)
		}
	}
}

// vertsFromPairs builds a slice of Wgs84 vertices from [[lon, lat], ...] pairs.
func vertsFromPairs(pairs [][]float64) []Wgs84 {
	verts := make([]Wgs84, len(pairs))
	for i, p := range pairs {
		verts[i] = NewWgs84(p[0], p[1], 0)
	}
	return verts
}

func TestParityWgs84Aabb(t *testing.T) {
	data := loadParity(t)
	tol := data.Meta.FloatTolerance

	checkPoint := func(name string, got Wgs84, want [2]float64) {
		t.Helper()
		if !floatClose(got.Longitude(), want[0], tol) || !floatClose(got.Latitude(), want[1], tol) {
			t.Errorf("%s = (%v,%v), want (%v,%v)", name, got.Longitude(), got.Latitude(), want[0], want[1])
		}
	}

	for _, c := range data.Wgs84Aabb {
		box := NewWgs84AABB(NewWgs84(c.SwLon, c.SwLat, 0), Vec2{X: c.SizeX, Y: c.SizeY})

		if box.Valid() != c.Valid {
			t.Errorf("%s: valid = %v, want %v", c.Name, box.Valid(), c.Valid)
		}
		if !floatClose(box.Size().X, c.StoredSize[0], tol) || !floatClose(box.Size().Y, c.StoredSize[1], tol) {
			t.Errorf("%s: stored size = (%v,%v), want (%v,%v)", c.Name, box.Size().X, box.Size().Y, c.StoredSize[0], c.StoredSize[1])
		}

		checkPoint(c.Name+".sw", box.SW(), c.SW)
		checkPoint(c.Name+".se", box.SE(), c.SE)
		checkPoint(c.Name+".ne", box.NE(), c.NE)
		checkPoint(c.Name+".nw", box.NW(), c.NW)
		checkPoint(c.Name+".center", box.Center(), c.Center)

		verts := box.Vertices()
		if len(verts) != len(c.Vertices) {
			t.Errorf("%s: %d vertices, want %d", c.Name, len(verts), len(c.Vertices))
		} else {
			for j, v := range verts {
				if !floatClose(v.Longitude(), c.Vertices[j][0], tol) || !floatClose(v.Latitude(), c.Vertices[j][1], tol) {
					t.Errorf("%s.vertices[%d] = (%v,%v), want (%v,%v)", c.Name, j, v.Longitude(), v.Latitude(), c.Vertices[j][0], c.Vertices[j][1])
				}
			}
		}

		if box.ContainsAntiMeridian() != c.ContainsAntiMeridian {
			t.Errorf("%s: containsAntiMeridian = %v, want %v", c.Name, box.ContainsAntiMeridian(), c.ContainsAntiMeridian)
		}

		left, right, ok := box.SplitOverAntiMeridian()
		if c.SplitOverAntiMeridian == nil {
			if ok {
				t.Errorf("%s: split returned ok=true, want none", c.Name)
			}
		} else {
			if !ok {
				t.Errorf("%s: split returned ok=false, want a split", c.Name)
			} else {
				checkPoint(c.Name+".split.left_sw", left.SW(), c.SplitOverAntiMeridian.LeftSW)
				checkPoint(c.Name+".split.right_sw", right.SW(), c.SplitOverAntiMeridian.RightSW)
				if !floatClose(left.Size().X, c.SplitOverAntiMeridian.LeftSize[0], tol) ||
					!floatClose(left.Size().Y, c.SplitOverAntiMeridian.LeftSize[1], tol) {
					t.Errorf("%s: left size = (%v,%v), want (%v,%v)", c.Name,
						left.Size().X, left.Size().Y, c.SplitOverAntiMeridian.LeftSize[0], c.SplitOverAntiMeridian.LeftSize[1])
				}
				if !floatClose(right.Size().X, c.SplitOverAntiMeridian.RightSize[0], tol) ||
					!floatClose(right.Size().Y, c.SplitOverAntiMeridian.RightSize[1], tol) {
					t.Errorf("%s: right size = (%v,%v), want (%v,%v)", c.Name,
						right.Size().X, right.Size().Y, c.SplitOverAntiMeridian.RightSize[0], c.SplitOverAntiMeridian.RightSize[1])
				}
			}
		}

		for lv, want := range c.NumTileIds {
			if got := box.NumTileIds(lv); got != want {
				t.Errorf("%s: numTileIds(%d) = %d, want %d", c.Name, lv, got, want)
			}
		}
		if got := box.TileLevel(8); got != c.TileLevelMin8 {
			t.Errorf("%s: tileLevel(8) = %d, want %d", c.Name, got, c.TileLevelMin8)
		}
		if got := box.TileLevel(2); got != c.TileLevelMin2 {
			t.Errorf("%s: tileLevel(2) = %d, want %d", c.Name, got, c.TileLevelMin2)
		}
	}
}

// boxesByName reconstructs every named AABB from the wgs84_aabb section so the
// contains / intersects sections can reference them by name.
func boxesByName(data parityData) map[string]Wgs84AABB {
	m := make(map[string]Wgs84AABB, len(data.Wgs84Aabb))
	for _, c := range data.Wgs84Aabb {
		m[c.Name] = NewWgs84AABB(NewWgs84(c.SwLon, c.SwLat, 0), Vec2{X: c.SizeX, Y: c.SizeY})
	}
	return m
}

func TestParityWgs84AabbContains(t *testing.T) {
	data := loadParity(t)
	boxes := boxesByName(data)
	for i, c := range data.Wgs84AabbContains {
		box, okBox := boxes[c.Box]
		if !okBox {
			t.Fatalf("case %d: unknown box %q", i, c.Box)
		}
		got := box.Contains(NewWgs84(c.PointLon, c.PointLat, 0))
		if got != c.Contains {
			t.Errorf("case %d: %s.contains(%v,%v) = %v, want %v", i, c.Box, c.PointLon, c.PointLat, got, c.Contains)
		}
	}
}

func TestParityWgs84AabbIntersects(t *testing.T) {
	data := loadParity(t)
	boxes := boxesByName(data)
	for i, c := range data.Wgs84AabbIntersects {
		a, okA := boxes[c.A]
		b, okB := boxes[c.B]
		if !okA || !okB {
			t.Fatalf("case %d: unknown box(es) %q / %q", i, c.A, c.B)
		}
		if got := a.Intersects(b); got != c.Intersects {
			t.Errorf("case %d: %s.intersects(%s) = %v, want %v", i, c.A, c.B, got, c.Intersects)
		}
	}
}

func TestParityPolygonOrientation(t *testing.T) {
	data := loadParity(t)
	for _, c := range data.PolygonOrientation {
		poly := NewPolygonWithVertices(PolygonType(c.PolygonType), vertsFromPairs(c.Vertices))
		if got := int(poly.Orientation()); got != c.Orientation {
			t.Errorf("%s: orientation = %d, want %d", c.Name, got, c.Orientation)
		}
		if got := poly.IsValid(); got != c.IsValid {
			t.Errorf("%s: isValid = %v, want %v", c.Name, got, c.IsValid)
		}
	}
}

func TestParityWgs84Polygon(t *testing.T) {
	data := loadParity(t)
	tol := data.Meta.FloatTolerance
	for _, c := range data.Wgs84Polygon {
		poly := NewWgs84PolygonWithVertices(vertsFromPairs(c.Vertices))

		if got := poly.IsValid(); got != c.IsValid {
			t.Errorf("%s: isValid = %v, want %v", c.Name, got, c.IsValid)
		}

		aabb := poly.AaBb()
		if !floatClose(aabb.SW().Longitude(), c.AabbSW[0], tol) || !floatClose(aabb.SW().Latitude(), c.AabbSW[1], tol) {
			t.Errorf("%s: aabb sw = (%v,%v), want (%v,%v)", c.Name,
				aabb.SW().Longitude(), aabb.SW().Latitude(), c.AabbSW[0], c.AabbSW[1])
		}
		if !floatClose(aabb.Size().X, c.AabbSize[0], tol) || !floatClose(aabb.Size().Y, c.AabbSize[1], tol) {
			t.Errorf("%s: aabb size = (%v,%v), want (%v,%v)", c.Name,
				aabb.Size().X, aabb.Size().Y, c.AabbSize[0], c.AabbSize[1])
		}

		med := poly.Median()
		if !floatClose(med.Longitude(), c.MedianLon, tol) || !floatClose(med.Latitude(), c.MedianLat, tol) {
			t.Errorf("%s: median = (lon=%v,lat=%v), want (lon=%v,lat=%v)", c.Name,
				med.Longitude(), med.Latitude(), c.MedianLon, c.MedianLat)
		}
	}
}

func TestParityWgs84PolygonCollision(t *testing.T) {
	data := loadParity(t)
	for i, c := range data.Wgs84PolygonCollision {
		a := NewWgs84PolygonWithVertices(vertsFromPairs(c.AVertices))
		b := NewWgs84PolygonWithVertices(vertsFromPairs(c.BVertices))
		if got := a.CollidesWith(b); got != c.ACollidesB {
			t.Errorf("case %d (%s vs %s): a.collidesWith(b) = %v, want %v", i, c.A, c.B, got, c.ACollidesB)
		}
		if got := b.CollidesWith(a); got != c.BCollidesA {
			t.Errorf("case %d (%s vs %s): b.collidesWith(a) = %v, want %v", i, c.A, c.B, got, c.BCollidesA)
		}
	}
}
