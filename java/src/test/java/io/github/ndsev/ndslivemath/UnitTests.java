// SPDX-License-Identifier: MIT
package io.github.ndsev.ndslivemath;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

/** Hand-written unit tests covering constructors, edge cases and exceptions. */
class UnitTests {

	private static final double EPS = 1e-9;

	// --- Wgs84 ---

	@Test
	void wgs84DefaultConstructorIsOrigin() {
		Wgs84 w = new Wgs84();
		assertEquals(0.0, w.x, EPS);
		assertEquals(0.0, w.y, EPS);
		assertEquals(0.0, w.z, EPS);
	}

	@Test
	void wgs84WrapsLongitude() {
		// 360.5 wraps to 0.5
		Wgs84 w = new Wgs84(360.5, 0.0);
		assertEquals(0.5, w.x, 1e-9);
		Wgs84 w2 = new Wgs84(-360.5, 0.0);
		assertEquals(-0.5, w2.x, 1e-9);
	}

	@Test
	void wgs84ClampsLatitude() {
		Wgs84 w = new Wgs84(0.0, 90.0);
		assertTrue(w.y < 90.0 && w.y > 89.0);
		Wgs84 w2 = new Wgs84(0.0, -90.0);
		assertEquals(-90.0, w2.y, EPS);
	}

	@Test
	void wgs84FloorOnNegativeNearOrigin() {
		// -0.000001 deg should floor to a negative NDS coordinate (not truncate to 0).
		Wgs84 w = new Wgs84(-0.000001, -0.000001);
		long[] nds = w.toNdsCoordinates();
		assertTrue(nds[0] < 0, "lon NDS should be negative due to floor");
		assertTrue(nds[1] < 0, "lat NDS should be negative due to floor");
	}

	@Test
	void wgs84RoundTrip() {
		Wgs84 w = new Wgs84(13.404954, 52.520008);
		long[] nds = w.toNdsCoordinates();
		Wgs84 back = Wgs84.fromNdsCoordinates(nds[0], nds[1]);
		assertTrue(Math.abs(back.x - w.x) < 1e-3);
		assertTrue(Math.abs(back.y - w.y) < 1e-3);
	}

	@Test
	void wgs84EqualsAndHashCode() {
		Wgs84 a = new Wgs84(10.0, 20.0);
		Wgs84 b = new Wgs84(10.0, 20.0);
		Wgs84 c = new Wgs84(10.0, 21.0);
		assertEquals(a, b);
		assertEquals(a.hashCode(), b.hashCode());
		assertNotEquals(a, c);
		assertNotEquals(a, "not a wgs84");
		assertEquals(a, a);
	}

	@Test
	void wgs84DegreesToMetersAndDms() {
		double[] m = Wgs84.degreesToMeters(1.0, 1.0, 0.0);
		assertEquals(111320.0, m[0], 1e-6);
		assertEquals(111320.0, m[1], 1e-6);
		// cos(60deg) = 0.5
		double[] m2 = Wgs84.degreesToMeters(1.0, 1.0, 60.0);
		assertEquals(55660.0, m2[0], 1e-3);

		String[] dms = new Wgs84(-122.4194, 37.7749).toDegreeMinutesSeconds();
		assertTrue(dms[0].endsWith(" N"));
		assertTrue(dms[1].endsWith(" W"));
		assertTrue(dms[0].contains("°"));
	}

	@Test
	void wgs84ToString() {
		assertTrue(new Wgs84(1.0, 2.0).toString().contains("Wgs84"));
	}

	// --- MortonCode ---

	@Test
	void mortonDefaultAndValue() {
		assertEquals(0L, new MortonCode().value());
		MortonCode m = new MortonCode(123456789L);
		assertEquals(123456789L, m.value());
	}

	@Test
	void mortonRoundTrip() {
		MortonCode m = MortonCode.fromNdsCoordinates(12345, 6789);
		long[] xy = m.toNdsCoordinates();
		assertEquals(12345, xy[0]);
		assertEquals(6789, xy[1]);
	}

	@Test
	void mortonBit63MaskedOff() {
		// Negative coordinates produce a code with bit 63 masked off => fits as
		// positive long.
		MortonCode m = MortonCode.fromNdsCoordinates(-12345, -6789);
		assertTrue(m.value() >= 0, "bit 63 should be masked off");
		long[] xy = m.toNdsCoordinates();
		assertEquals(-12345, xy[0]);
		assertEquals(-6789, xy[1]);
	}

	@Test
	void mortonEqualsHashCodeToString() {
		MortonCode a = new MortonCode(42);
		MortonCode b = new MortonCode(42);
		assertEquals(a, b);
		assertEquals(a.hashCode(), b.hashCode());
		assertNotEquals(a, new MortonCode(43));
		assertNotEquals(a, "x");
		assertEquals(a, a);
		assertTrue(a.toString().contains("MortonCode"));
	}

	// --- PackedTileId ---

	@Test
	void tileSignedUnsignedEquivalence() {
		PackedTileId signed = new PackedTileId(-2147483648L);
		PackedTileId unsigned = new PackedTileId(2147483648L);
		assertEquals(signed.value(), unsigned.value());
		assertEquals(-2147483648, signed.value());
		assertEquals(15, signed.level());
		assertEquals(0, signed.mortonNumber());
		assertEquals(signed, unsigned);
		assertEquals(signed.hashCode(), unsigned.hashCode());
	}

	@Test
	void tileLevel15MaxIsMinusOne() {
		PackedTileId t = PackedTileId.fromTileIndex((1L << 31) - 1, 15);
		assertEquals(-1, t.value());
		assertEquals(15, t.level());
	}

	@Test
	void tileLevel14Positive() {
		PackedTileId t = PackedTileId.fromTileIndex(0, 14);
		assertEquals(1073741824, t.value());
		assertEquals(14, t.level());
	}

	@Test
	void tileInvalidLevelThrows() {
		assertThrows(IllegalArgumentException.class, () -> PackedTileId.fromTileIndex(0, 16));
		assertThrows(IllegalArgumentException.class, () -> PackedTileId.fromTileIndex(0, -1));
	}

	@Test
	void tileInvalidMortonThrows() {
		// level 1 allows morton 0..7
		assertThrows(IllegalArgumentException.class, () -> PackedTileId.fromTileIndex(8, 1));
		assertThrows(IllegalArgumentException.class, () -> PackedTileId.fromTileIndex(-1, 1));
	}

	@Test
	void tileInvalidValueThrows() {
		// value below 1<<16 is invalid
		assertThrows(IllegalArgumentException.class, () -> new PackedTileId(0));
		assertThrows(IllegalArgumentException.class, () -> new PackedTileId(100));
	}

	@Test
	void fromMortonAndLevelInvalidLevelThrows() {
		MortonCode m = MortonCode.fromNdsCoordinates(0, 0);
		assertThrows(IllegalArgumentException.class, () -> PackedTileId.fromMortonAndLevel(m, 16));
	}

	@Test
	void tileNeighbourWrapping() {
		// morton 0 at level 1 going west wraps to the easternmost column.
		PackedTileId t = PackedTileId.fromTileIndex(0, 1);
		assertEquals(t.eastNeighbour().value(), 131073);
		assertEquals(t.westNeighbour().value(), 131077);
		assertEquals(t.northNeighbour().value(), 131074);
		assertEquals(t.southNeighbour().value(), 131074);
	}

	@Test
	void tileDimensionsInMetersPositiveAtEquator() {
		PackedTileId t = PackedTileId.fromTileIndex(0, 13);
		double[] dim = t.dimensionsInMeters();
		assertTrue(dim[0] > 0 && dim[1] > 0);
	}

	@Test
	void tileEqualsAndToString() {
		PackedTileId a = PackedTileId.fromTileIndex(4, 2);
		PackedTileId b = PackedTileId.fromTileIndex(4, 2);
		assertEquals(a, b);
		assertNotEquals(a, PackedTileId.fromTileIndex(5, 2));
		assertNotEquals(a, "x");
		assertEquals(a, a);
		assertTrue(a.toString().contains("PackedTileId"));
		assertEquals(4, a.mortonNumber());
	}

	// --- NdsBoundingBox ---

	@Test
	void bboxIntersectsAndContains() {
		NdsBoundingBox a = new NdsBoundingBox(0, 0, 100, 100);
		NdsBoundingBox inside = new NdsBoundingBox(10, 10, 20, 20);
		NdsBoundingBox overlap = new NdsBoundingBox(50, 50, 150, 150);
		NdsBoundingBox apart = new NdsBoundingBox(200, 200, 300, 300);
		assertTrue(a.contains(inside));
		assertTrue(a.intersects(overlap));
		assertFalse(a.contains(overlap));
		assertFalse(a.intersects(apart));
	}

	@Test
	void bboxFromTile() {
		PackedTileId t = PackedTileId.fromTileIndex(0, 14);
		NdsBoundingBox box = NdsBoundingBox.fromTile(t);
		NdsBoundingBox box2 = NdsBoundingBox.fromTile((long) t.value());
		assertEquals(box, box2);
		assertEquals(0, box.minX);
		assertEquals(0, box.minY);
		assertTrue(box.maxX > 0);
	}

	@Test
	void bboxEqualsHashCodeToString() {
		NdsBoundingBox a = new NdsBoundingBox(1, 2, 3, 4);
		NdsBoundingBox b = new NdsBoundingBox(1, 2, 3, 4);
		assertEquals(a, b);
		assertEquals(a.hashCode(), b.hashCode());
		assertNotEquals(a, new NdsBoundingBox(1, 2, 3, 5));
		assertNotEquals(a, "x");
		assertEquals(a, a);
		assertTrue(a.toString().contains("NdsBoundingBox"));
	}

	// --- TileIds ---

	@Test
	void tileIdsEmptyBoundingBoxThrows() {
		assertThrows(IllegalArgumentException.class, () -> TileIds.boundingBoxFromTileIds(List.of()));
		assertThrows(IllegalArgumentException.class, () -> TileIds.boundingBoxFromTileIds(null));
	}

	@Test
	void tileIdsRoundTripSingleTile() {
		PackedTileId tile = PackedTileId.fromTileIndex(3, 2);
		long[] bbox = TileIds.boundingBoxFromTileIds(List.of(tile));
		List<PackedTileId> back = TileIds.getTileIdsForBoundingBox(bbox[0], bbox[1], bbox[2], bbox[3], 2);
		assertEquals(1, back.size());
		assertEquals(tile.value(), back.get(0).value());
	}

	@Test
	void tileIdsMultipleTiles() {
		List<PackedTileId> tiles = TileIds.getTileIdsForBoundingBox(0, 0, (1 << 28), (1 << 28), 3);
		assertEquals(4, tiles.size());
		long[] bbox = TileIds.boundingBoxFromTileIds(tiles);
		// 4 tiles of size 2^28 cover [0, 2^29); tight box max is 2^29 - 1.
		assertArrayEquals(new long[]{0, 0, 536870911, 536870911}, bbox);
	}
}
