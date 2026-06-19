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
import java.util.List;
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

	// --- helpers ---

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
