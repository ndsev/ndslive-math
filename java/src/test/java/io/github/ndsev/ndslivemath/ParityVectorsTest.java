// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Loads the language-neutral golden vectors from
 * {@code test-vectors/parity_vectors.json} and asserts that the Java
 * implementation matches the Python reference for every section.
 *
 * <p>
 * Integer fields must be exact; float fields are compared within
 * {@code _meta.float_tolerance}; Morton values are decimal strings (they can
 * exceed 2^53) and compared as unsigned 64-bit values.
 * </p>
 */
class ParityVectorsTest {

	private static JSONObject data;
	private static double floatTolerance;

	@BeforeAll
	static void load() throws IOException {
		Path jsonPath = locateVectors();
		assertNotNull(jsonPath, "Could not locate parity_vectors.json");
		String content = new String(Files.readAllBytes(jsonPath), StandardCharsets.UTF_8);
		data = new JSONObject(content);
		floatTolerance = data.getJSONObject("_meta").getDouble("float_tolerance");
	}

	/**
	 * Resolve parity_vectors.json relative to the repo root from several anchors.
	 */
	private static Path locateVectors() {
		List<Path> candidates = new ArrayList<>();
		// Allow override via system property.
		String prop = System.getProperty("parity.vectors");
		if (prop != null) {
			candidates.add(Paths.get(prop));
		}
		Path cwd = Paths.get("").toAbsolutePath();
		// Walk up from cwd looking for test-vectors/parity_vectors.json.
		Path p = cwd;
		for (int i = 0; i < 8 && p != null; i++) {
			candidates.add(p.resolve("test-vectors").resolve("parity_vectors.json"));
			candidates.add(p.resolve("parity_vectors.json"));
			p = p.getParent();
		}
		for (Path c : candidates) {
			if (c != null && Files.isRegularFile(c)) {
				return c;
			}
		}
		return null;
	}

	@Test
	void wgs84ToNds() {
		JSONArray arr = data.getJSONArray("wgs84_to_nds");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			Wgs84 w = new Wgs84(e.getDouble("lon"), e.getDouble("lat"));
			assertClose(e.getDouble("normalized_lon"), w.x, "normalized_lon @" + i);
			assertClose(e.getDouble("normalized_lat"), w.y, "normalized_lat @" + i);
			long[] nds = w.toNdsCoordinates();
			assertEquals(e.getLong("nds_x"), nds[0], "nds_x @" + i);
			assertEquals(e.getLong("nds_y"), nds[1], "nds_y @" + i);
		}
	}

	@Test
	void ndsToWgs84() {
		JSONArray arr = data.getJSONArray("nds_to_wgs84");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			Wgs84 w = Wgs84.fromNdsCoordinates(e.getLong("x"), e.getLong("y"));
			assertClose(e.getDouble("lon"), w.x, "lon @" + i);
			assertClose(e.getDouble("lat"), w.y, "lat @" + i);
		}
	}

	@Test
	void morton() {
		JSONArray arr = data.getJSONArray("morton");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			MortonCode m = MortonCode.fromNdsCoordinates(e.getLong("x"), e.getLong("y"));
			assertEquals(e.getString("morton"), Long.toUnsignedString(m.value()), "morton @" + i);
			long[] dec = m.toNdsCoordinates();
			assertEquals(e.getLong("decoded_x"), dec[0], "decoded_x @" + i);
			assertEquals(e.getLong("decoded_y"), dec[1], "decoded_y @" + i);
		}
	}

	@Test
	void packedTileFromIndex() {
		JSONArray arr = data.getJSONArray("packed_tile_from_index");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			PackedTileId t = PackedTileId.fromTileIndex(e.getLong("morton_number"), e.getInt("level"));
			assertEquals(e.getInt("value"), t.value(), "value @" + i);
			assertEquals(e.getInt("computed_level"), t.level(), "level @" + i);
			assertEquals(e.getLong("computed_morton_number"), t.mortonNumber(), "morton_number @" + i);
			assertEquals(e.getLong("size"), t.size(), "size @" + i);
			assertPair(e.getJSONArray("sw"), t.southWestCorner(), "sw @" + i);
			assertPair(e.getJSONArray("ne"), t.northEastCorner(), "ne @" + i);
			assertPair(e.getJSONArray("center"), t.center(), "center @" + i);
		}
	}

	@Test
	void tileNeighbours() {
		JSONArray arr = data.getJSONArray("tile_neighbours");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			PackedTileId t = PackedTileId.fromTileIndex(e.getLong("morton_number"), e.getInt("level"));
			assertEquals(e.getInt("west"), t.westNeighbour().value(), "west @" + i);
			assertEquals(e.getInt("east"), t.eastNeighbour().value(), "east @" + i);
			assertEquals(e.getInt("south"), t.southNeighbour().value(), "south @" + i);
			assertEquals(e.getInt("north"), t.northNeighbour().value(), "north @" + i);
		}
	}

	@Test
	void fromMortonAndLevel() {
		JSONArray arr = data.getJSONArray("from_morton_and_level");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			MortonCode m = MortonCode.fromNdsCoordinates(e.getLong("x"), e.getLong("y"));
			PackedTileId t = PackedTileId.fromMortonAndLevel(m, e.getInt("level"));
			assertEquals(e.getInt("value"), t.value(), "value @" + i);
			assertEquals(e.getInt("computed_level"), t.level(), "level @" + i);
			assertEquals(e.getLong("computed_morton_number"), t.mortonNumber(), "morton_number @" + i);
		}
	}

	@Test
	void tilesForBbox() {
		JSONArray arr = data.getJSONArray("tiles_for_bbox");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			List<PackedTileId> tiles = TileIds.getTileIdsForBoundingBox(e.getLong("sw_x"), e.getLong("sw_y"),
					e.getLong("ne_x"), e.getLong("ne_y"), e.getInt("level"));
			JSONArray expected = e.getJSONArray("tile_values");
			assertEquals(expected.length(), tiles.size(), "tile count @" + i);
			for (int j = 0; j < expected.length(); j++) {
				assertEquals(expected.getInt(j), tiles.get(j).value(), "tile[" + j + "] @" + i);
			}
		}
	}

	@Test
	void bboxFromTiles() {
		JSONArray arr = data.getJSONArray("bbox_from_tiles");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			JSONArray vals = e.getJSONArray("tile_values");
			List<PackedTileId> tiles = new ArrayList<>();
			for (int j = 0; j < vals.length(); j++) {
				tiles.add(new PackedTileId(vals.getLong(j)));
			}
			long[] result = TileIds.boundingBoxFromTileIds(tiles);
			JSONArray expected = e.getJSONArray("result");
			assertEquals(expected.getLong(0), result[0], "result[0] @" + i);
			assertEquals(expected.getLong(1), result[1], "result[1] @" + i);
			assertEquals(expected.getLong(2), result[2], "result[2] @" + i);
			assertEquals(expected.getLong(3), result[3], "result[3] @" + i);
		}
	}

	@Test
	void ndsBboxOps() {
		JSONArray arr = data.getJSONArray("nds_bbox_ops");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			NdsBoundingBox a = boxOf(e.getJSONArray("a"));
			NdsBoundingBox b = boxOf(e.getJSONArray("b"));
			assertEquals(e.getBoolean("intersects"), a.intersects(b), "intersects @" + i);
			assertEquals(e.getBoolean("a_contains_b"), a.contains(b), "a_contains_b @" + i);
		}
	}

	@Test
	void ndsBboxFromWgs84() {
		JSONArray arr = data.getJSONArray("nds_bbox_from_wgs84");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			JSONArray sw = e.getJSONArray("sw");
			JSONArray ne = e.getJSONArray("ne");
			NdsBoundingBox box = NdsBoundingBox.fromWgs84Corners(new Wgs84(sw.getDouble(0), sw.getDouble(1)),
					new Wgs84(ne.getDouble(0), ne.getDouble(1)));
			assertEquals(e.getLong("min_x"), box.minX, "min_x @" + i);
			assertEquals(e.getLong("min_y"), box.minY, "min_y @" + i);
			assertEquals(e.getLong("max_x"), box.maxX, "max_x @" + i);
			assertEquals(e.getLong("max_y"), box.maxY, "max_y @" + i);
		}
	}

	@Test
	void distanceBearing() {
		JSONArray arr = data.getJSONArray("distance_bearing");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			JSONArray a = e.getJSONArray("a");
			JSONArray b = e.getJSONArray("b");
			Wgs84 wa = new Wgs84(a.getDouble(0), a.getDouble(1));
			Wgs84 wb = new Wgs84(b.getDouble(0), b.getDouble(1));
			assertClose(e.getDouble("distance_m"), wa.distanceTo(wb), "distance_m @" + i);
			assertClose(e.getDouble("bearing_rad"), wa.bearingFrom(wb), "bearing_rad @" + i);
		}
	}

	@Test
	void ndsDistanceToMeters() {
		JSONArray arr = data.getJSONArray("nds_distance_to_meters");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			double[] wh = Wgs84.ndsDistanceToMeters(e.getDouble("nds_x"), e.getDouble("nds_y"),
					e.getDouble("at_latitude"));
			assertClose(e.getDouble("width_m"), wh[0], "width_m @" + i);
			assertClose(e.getDouble("height_m"), wh[1], "height_m @" + i);
		}
	}

	// --- geometry: Polygon.orientation / isValid ---

	@Test
	void polygonOrientation() {
		JSONArray arr = data.getJSONArray("polygon_orientation");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			Polygon.PolygonType type = polygonTypeOf(e.getInt("polygon_type"));
			Polygon p = new Polygon(type, wgs84List(e.getJSONArray("vertices")));
			assertEquals(e.getInt("orientation"), p.orientation().value(),
					"orientation @" + i + " (" + e.getString("name") + ")");
			assertEquals(e.getBoolean("is_valid"), p.isValid(), "is_valid @" + i + " (" + e.getString("name") + ")");
		}
	}

	// --- geometry: Wgs84Aabb construction, corners, predicates ---

	@Test
	void wgs84Aabb() {
		JSONArray arr = data.getJSONArray("wgs84_aabb");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			String name = e.getString("name");
			Wgs84Aabb box = aabbOf(e);

			assertEquals(e.getBoolean("valid"), box.valid(), "valid @" + name);
			assertVec2(e.getJSONArray("stored_size"), box.size(), "stored_size @" + name);
			assertWgs84(e.getJSONArray("sw"), box.sw(), "sw @" + name);
			assertWgs84(e.getJSONArray("se"), box.se(), "se @" + name);
			assertWgs84(e.getJSONArray("ne"), box.ne(), "ne @" + name);
			assertWgs84(e.getJSONArray("nw"), box.nw(), "nw @" + name);
			assertWgs84(e.getJSONArray("center"), box.center(), "center @" + name);

			JSONArray verts = e.getJSONArray("vertices");
			List<Wgs84> actualVerts = box.vertices();
			assertEquals(verts.length(), actualVerts.size(), "vertices count @" + name);
			for (int j = 0; j < verts.length(); j++) {
				assertWgs84(verts.getJSONArray(j), actualVerts.get(j), "vertices[" + j + "] @" + name);
			}

			assertEquals(e.getBoolean("contains_anti_meridian"), box.containsAntiMeridian(),
					"contains_anti_meridian @" + name);

			Optional<Wgs84Aabb[]> split = box.splitOverAntiMeridian();
			if (e.isNull("split_over_anti_meridian")) {
				assertTrue(split.isEmpty(), "split should be empty @" + name);
			} else {
				assertTrue(split.isPresent(), "split should be present @" + name);
				JSONObject s = e.getJSONObject("split_over_anti_meridian");
				Wgs84Aabb left = split.get()[0];
				Wgs84Aabb right = split.get()[1];
				assertWgs84(s.getJSONArray("left_sw"), left.sw(), "left_sw @" + name);
				assertVec2(s.getJSONArray("left_size"), left.size(), "left_size @" + name);
				assertWgs84(s.getJSONArray("right_sw"), right.sw(), "right_sw @" + name);
				assertVec2(s.getJSONArray("right_size"), right.size(), "right_size @" + name);
			}

			JSONArray numTiles = e.getJSONArray("num_tile_ids");
			for (int lv = 0; lv < numTiles.length(); lv++) {
				assertEquals(numTiles.getLong(lv), box.numTileIds(lv), "num_tile_ids[" + lv + "] @" + name);
			}
			assertEquals(e.getInt("tile_level_min8"), box.tileLevel(8), "tile_level_min8 @" + name);
			assertEquals(e.getInt("tile_level_min2"), box.tileLevel(2), "tile_level_min2 @" + name);
		}
	}

	@Test
	void wgs84AabbContains() {
		Map<String, Wgs84Aabb> boxes = namedBoxes();
		JSONArray arr = data.getJSONArray("wgs84_aabb_contains");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			Wgs84Aabb box = boxes.get(e.getString("box"));
			assertNotNull(box, "unknown box " + e.getString("box"));
			Wgs84 point = new Wgs84(e.getDouble("point_lon"), e.getDouble("point_lat"));
			assertEquals(e.getBoolean("contains"), box.contains(point),
					"contains @" + i + " box=" + e.getString("box") + " point=" + e.getString("point"));
		}
	}

	@Test
	void wgs84AabbIntersects() {
		Map<String, Wgs84Aabb> boxes = namedBoxes();
		JSONArray arr = data.getJSONArray("wgs84_aabb_intersects");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			Wgs84Aabb a = boxes.get(e.getString("a"));
			Wgs84Aabb b = boxes.get(e.getString("b"));
			assertNotNull(a, "unknown box " + e.getString("a"));
			assertNotNull(b, "unknown box " + e.getString("b"));
			assertEquals(e.getBoolean("intersects"), a.intersects(b),
					"intersects @" + i + " a=" + e.getString("a") + " b=" + e.getString("b"));
		}
	}

	// --- geometry: Wgs84Polygon aaBb / median ---

	@Test
	void wgs84Polygon() {
		JSONArray arr = data.getJSONArray("wgs84_polygon");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			String name = e.getString("name");
			Wgs84Polygon poly = new Wgs84Polygon(wgs84List(e.getJSONArray("vertices")));

			assertEquals(e.getBoolean("is_valid"), poly.isValid(), "is_valid @" + name);

			Wgs84Aabb bb = poly.aaBb();
			assertWgs84(e.getJSONArray("aabb_sw"), bb.sw(), "aabb_sw @" + name);
			assertVec2(e.getJSONArray("aabb_size"), bb.size(), "aabb_size @" + name);

			Wgs84 median = poly.median();
			assertClose(e.getDouble("median_lon"), median.longitude(), "median_lon @" + name);
			assertClose(e.getDouble("median_lat"), median.latitude(), "median_lat @" + name);
		}
	}

	// --- geometry: Wgs84Polygon collidesWith ---

	@Test
	void wgs84PolygonCollision() {
		JSONArray arr = data.getJSONArray("wgs84_polygon_collision");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			Wgs84Polygon a = new Wgs84Polygon(wgs84List(e.getJSONArray("a_vertices")));
			Wgs84Polygon b = new Wgs84Polygon(wgs84List(e.getJSONArray("b_vertices")));
			assertEquals(e.getBoolean("a_collides_b"), a.collidesWith(b),
					"a_collides_b @" + i + " a=" + e.getString("a") + " b=" + e.getString("b"));
			assertEquals(e.getBoolean("b_collides_a"), b.collidesWith(a),
					"b_collides_a @" + i + " a=" + e.getString("a") + " b=" + e.getString("b"));
		}
	}

	// --- helpers ---

	private static Polygon.PolygonType polygonTypeOf(int value) {
		for (Polygon.PolygonType t : Polygon.PolygonType.values()) {
			if (t.value() == value) {
				return t;
			}
		}
		throw new IllegalArgumentException("unknown polygon_type " + value);
	}

	private static List<Wgs84> wgs84List(JSONArray arr) {
		List<Wgs84> list = new ArrayList<>(arr.length());
		for (int i = 0; i < arr.length(); i++) {
			JSONArray p = arr.getJSONArray(i);
			list.add(new Wgs84(p.getDouble(0), p.getDouble(1)));
		}
		return list;
	}

	private static Wgs84Aabb aabbOf(JSONObject e) {
		return new Wgs84Aabb(new Wgs84(e.getDouble("sw_lon"), e.getDouble("sw_lat")),
				new Vec2(e.getDouble("size_x"), e.getDouble("size_y")));
	}

	private static Map<String, Wgs84Aabb> namedBoxes() {
		Map<String, Wgs84Aabb> boxes = new HashMap<>();
		JSONArray arr = data.getJSONArray("wgs84_aabb");
		for (int i = 0; i < arr.length(); i++) {
			JSONObject e = arr.getJSONObject(i);
			boxes.put(e.getString("name"), aabbOf(e));
		}
		return boxes;
	}

	private static void assertWgs84(JSONArray expected, Wgs84 actual, String msg) {
		assertClose(expected.getDouble(0), actual.longitude(), msg + ".lon");
		assertClose(expected.getDouble(1), actual.latitude(), msg + ".lat");
	}

	private static void assertVec2(JSONArray expected, Vec2 actual, String msg) {
		assertClose(expected.getDouble(0), actual.x, msg + ".x");
		assertClose(expected.getDouble(1), actual.y, msg + ".y");
	}

	private static NdsBoundingBox boxOf(JSONArray a) {
		return new NdsBoundingBox(a.getLong(0), a.getLong(1), a.getLong(2), a.getLong(3));
	}

	private static void assertPair(JSONArray expected, long[] actual, String msg) {
		assertEquals(expected.getLong(0), actual[0], msg + "[0]");
		assertEquals(expected.getLong(1), actual[1], msg + "[1]");
	}

	private static void assertClose(double expected, double actual, String msg) {
		assertTrue(Math.abs(expected - actual) <= floatTolerance,
				msg + ": expected " + expected + " but was " + actual + " (tol " + floatTolerance + ")");
	}

	@Test
	void sanityFloatComparisonUsesTolerance() {
		// Guards against an accidentally-zero tolerance.
		assertFalse(floatTolerance == 0.0, "float tolerance must be non-zero");
	}
}
