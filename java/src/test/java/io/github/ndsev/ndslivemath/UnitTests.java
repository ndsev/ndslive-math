// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Arrays;
import java.util.List;
import java.util.Optional;
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

	// --- Wgs84 geometry additions ---

	@Test
	void wgs84GeometryConstants() {
		assertEquals(8.381903171539307e-08, Wgs84.LON_NDS_DELTA_POW2, 1e-20);
		assertEquals(8.381903171539307e-08, Wgs84.LAT_NDS_DELTA_POW2, 1e-20);
		assertEquals(-180.0, Wgs84.LON_MIN, 0.0);
		assertEquals(179.99999991618097, Wgs84.LON_MAX, 1e-12);
		assertEquals(-90.0, Wgs84.LAT_MIN, 0.0);
		assertEquals(90.0 - Wgs84.LAT_NDS_DELTA_POW2, Wgs84.LAT_MAX, 0.0);
		// The pow2 delta must differ from the (2^n - 1) delta (load-bearing).
		assertNotEquals(Wgs84.LON_NDS_DELTA, Wgs84.LON_NDS_DELTA_POW2);
	}

	@Test
	void wgs84Accessors() {
		Wgs84 w = new Wgs84(12.5, -7.25);
		assertEquals(12.5, w.longitude(), EPS);
		assertEquals(-7.25, w.latitude(), EPS);
		assertEquals(12.5, w.dx(), EPS);
		assertEquals(-7.25, w.dy(), EPS);
	}

	@Test
	void wgs84VectorArithmetic() {
		Wgs84 a = new Wgs84(10.0, 20.0);
		Wgs84 b = new Wgs84(2.0, 4.0);
		assertEquals(new Wgs84(12.0, 24.0), a.add(b));
		assertEquals(new Wgs84(8.0, 16.0), a.sub(b));
		assertEquals(new Wgs84(20.0, 80.0), a.mul(b));
		assertEquals(new Wgs84(5.0, 5.0), a.div(b));
	}

	@Test
	void wgs84FromMortonCodeScalesBothAxesEqually() {
		// fromMortonCode scales both x and y by 360 / 2^32.
		MortonCode m = MortonCode.fromNdsCoordinates(0, 0);
		Wgs84 origin = Wgs84.fromMortonCode(m);
		assertEquals(0.0, origin.longitude(), EPS);
		assertEquals(0.0, origin.latitude(), EPS);

		long step = 1L << 24;
		Wgs84 w = Wgs84.fromMortonCode(MortonCode.fromNdsCoordinates(step, step));
		double expected = step * (360.0 / Math.pow(2, 32));
		assertEquals(expected, w.longitude(), 1e-9);
		// y uses the SAME 360/2^32 factor (unlike fromNdsCoordinates).
		assertEquals(expected, w.latitude(), 1e-9);
	}

	// --- Vec2 ---

	@Test
	void vec2Basics() {
		Vec2 v = new Vec2(3.0, -4.0);
		assertEquals(3.0, v.x, EPS);
		assertEquals(-4.0, v.y, EPS);
		assertEquals(new Vec2(0.0, 0.0), new Vec2());
		assertEquals(new Vec2(4.0, -2.0), v.add(new Vec2(1.0, 2.0)));
		assertEquals(new Vec2(2.0, -6.0), v.sub(new Vec2(1.0, 2.0)));
		assertEquals(new Vec2(6.0, -8.0), v.mul(2.0));
		assertEquals(new Vec2(3.0, 4.0), v.abs());
	}

	@Test
	void vec2EqualsHashCodeToString() {
		Vec2 a = new Vec2(1.0, 2.0);
		Vec2 b = new Vec2(1.0, 2.0);
		assertEquals(a, b);
		assertEquals(a.hashCode(), b.hashCode());
		assertNotEquals(a, new Vec2(1.0, 3.0));
		assertNotEquals(a, "x");
		assertEquals(a, a);
		assertTrue(a.toString().contains("Vec2"));
	}

	@Test
	void vec2EqualsShortCircuitsOnX() {
		// Differing x must make equals() false via the FIRST Double.compare
		// (the (1,3) case in vec2EqualsHashCodeToString only differs in y, so it
		// never exercises the x-mismatch side of the && in equals()).
		Vec2 a = new Vec2(1.0, 2.0);
		assertNotEquals(a, new Vec2(5.0, 2.0));
		// And a vector differing in both components is still not equal.
		assertNotEquals(a, new Vec2(5.0, 9.0));
	}

	@Test
	void vec2ToStringContainsComponents() {
		String s = new Vec2(3.5, -4.25).toString();
		assertTrue(s.contains("3.5"));
		assertTrue(s.contains("-4.25"));
	}

	// --- Polygon ---

	@Test
	void polygonDefaultAndAccessors() {
		Polygon p = new Polygon();
		assertEquals(Polygon.PolygonType.UNKNOWN, p.type());
		assertFalse(p.isValid());
		assertEquals(0, p.size());

		p.setType(Polygon.PolygonType.SIMPLE_POLYGON);
		assertEquals(Polygon.PolygonType.SIMPLE_POLYGON, p.type());

		p.addVertex(new Wgs84(0, 0));
		p.addVertices(Arrays.asList(new Wgs84(1, 0), new Wgs84(0, 1)));
		assertEquals(3, p.size());
		assertTrue(p.isValid());
		assertEquals(new Wgs84(1, 0), p.get(1));

		p.set(1, new Wgs84(2, 0));
		assertEquals(new Wgs84(2, 0), p.get(1));
		assertEquals(3, p.vertices().size());
	}

	@Test
	void polygonEnumValues() {
		assertEquals(-1, Polygon.Orientation.CLOCKWISE.value());
		assertEquals(0, Polygon.Orientation.INVALID_ORIENTATION.value());
		assertEquals(1, Polygon.Orientation.COUNTERCLOCKWISE.value());
		assertEquals(0, Polygon.PolygonType.SIMPLE_POLYGON.value());
		assertEquals(1, Polygon.PolygonType.TRIANGLE_STRIP.value());
		assertEquals(2, Polygon.PolygonType.TRIANGLE_FAN.value());
		assertEquals(3, Polygon.PolygonType.TRIANGLE_LIST.value());
		assertEquals(4, Polygon.PolygonType.UNKNOWN.value());
	}

	@Test
	void polygonOrientationTypeOnlyConstructor() {
		Polygon p = new Polygon(Polygon.PolygonType.TRIANGLE_FAN);
		assertEquals(Polygon.PolygonType.TRIANGLE_FAN, p.type());
		assertEquals(Polygon.Orientation.INVALID_ORIENTATION, p.orientation());
	}

	@Test
	void polygonOrientationVariants() {
		Polygon ccw = new Polygon(Polygon.PolygonType.SIMPLE_POLYGON,
				Arrays.asList(new Wgs84(0, 0), new Wgs84(1, 0), new Wgs84(0, 1)));
		assertEquals(Polygon.Orientation.COUNTERCLOCKWISE, ccw.orientation());

		Polygon cw = new Polygon(Polygon.PolygonType.SIMPLE_POLYGON,
				Arrays.asList(new Wgs84(0, 0), new Wgs84(0, 1), new Wgs84(1, 0)));
		assertEquals(Polygon.Orientation.CLOCKWISE, cw.orientation());

		Polygon collinear = new Polygon(Polygon.PolygonType.SIMPLE_POLYGON,
				Arrays.asList(new Wgs84(0, 0), new Wgs84(1, 1), new Wgs84(2, 2)));
		assertEquals(Polygon.Orientation.INVALID_ORIENTATION, collinear.orientation());

		// Multi-triangle TRIANGLE_LIST (4 verts) is unsupported.
		Polygon multi = new Polygon(Polygon.PolygonType.TRIANGLE_LIST,
				Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(4, 4), new Wgs84(0, 4)));
		assertEquals(Polygon.Orientation.INVALID_ORIENTATION, multi.orientation());

		// Single-triangle TRIANGLE_LIST is allowed.
		Polygon single = new Polygon(Polygon.PolygonType.TRIANGLE_LIST,
				Arrays.asList(new Wgs84(0, 0), new Wgs84(1, 0), new Wgs84(0, 1)));
		assertEquals(Polygon.Orientation.COUNTERCLOCKWISE, single.orientation());
	}

	// --- Wgs84Aabb ---

	@Test
	void aabbDefaultIsValidEmpty() {
		Wgs84Aabb def = new Wgs84Aabb();
		assertTrue(def.valid());
		assertEquals(new Wgs84(0, 0), def.sw());
		assertEquals(new Vec2(0, 0), def.size());
	}

	@Test
	void aabbCornersAndCenter() {
		Wgs84Aabb box = new Wgs84Aabb(new Wgs84(0, 10), new Vec2(20, 10));
		assertEquals(new Wgs84(0, 10), box.sw());
		assertEquals(new Wgs84(20, 20), box.ne());
		assertEquals(new Wgs84(0, 20), box.nw());
		assertEquals(new Wgs84(20, 10), box.se());
		assertEquals(new Wgs84(10, 15), box.center());
		assertEquals(new Vec2(20, 10), box.size());
		List<Wgs84> verts = box.vertices();
		assertEquals(4, verts.size());
		assertEquals(new Wgs84(0, 10), verts.get(0));
		assertEquals(new Wgs84(20, 10), verts.get(1));
		assertEquals(new Wgs84(20, 20), verts.get(2));
		assertEquals(new Wgs84(0, 20), verts.get(3));
	}

	@Test
	void aabbExcessHeightClamp() {
		Wgs84Aabb clamp = new Wgs84Aabb(new Wgs84(0, 85), new Vec2(10, 10));
		assertEquals(10.0, clamp.size().x, EPS);
		assertEquals(5.0, clamp.size().y, EPS);
		assertTrue(clamp.valid());
	}

	@Test
	void aabbInvalidBoxNotClamped() {
		Wgs84Aabb bad = new Wgs84Aabb(new Wgs84(0, 85), new Vec2(-1, 10));
		assertFalse(bad.valid());
		assertEquals(-1.0, bad.size().x, EPS);
		assertEquals(10.0, bad.size().y, EPS);
	}

	@Test
	void aabbValidRejectsEachOutOfRangeSize() {
		// valid() is `size.x>=0 && size.y>=0 && size.x<=360 && size.y<=180`.
		// aabbInvalidBoxNotClamped only fails the first clause (size.x<0). These
		// cover the remaining three clauses' false sides individually.
		// size.y < 0 (third clause fails)
		assertFalse(new Wgs84Aabb(new Wgs84(0, 0), new Vec2(10, -1)).valid());
		// size.x > 360 (second clause fails)
		assertFalse(new Wgs84Aabb(new Wgs84(0, 0), new Vec2(361, 10)).valid());
		// size.y > 180 (fourth clause fails)
		assertFalse(new Wgs84Aabb(new Wgs84(0, 0), new Vec2(10, 181)).valid());
		// Boundary values (size.x==360, size.y==180) are still valid.
		assertTrue(new Wgs84Aabb(new Wgs84(0, -90), new Vec2(360, 180)).valid());
	}

	@Test
	void aabbContainsInclusive() {
		Wgs84Aabb box = new Wgs84Aabb(new Wgs84(0, 10), new Vec2(20, 10));
		assertTrue(box.contains(new Wgs84(5, 15)));
		assertFalse(box.contains(new Wgs84(50, 50)));
		assertTrue(box.contains(new Wgs84(0, 10)));
		assertTrue(box.contains(new Wgs84(20, 20)));
	}

	@Test
	void aabbContainsLatitudeOutOfRange() {
		// (50,50) above short-circuits on the longitude clause, so the latitude
		// comparisons in contains() never see a false. Use points whose longitude
		// is inside the box but whose latitude is out of range, to take the
		// latitude clauses' false branches.
		Wgs84Aabb box = new Wgs84Aabb(new Wgs84(0, 10), new Vec2(20, 10));
		// longitude in [0,20], latitude below 10
		assertFalse(box.contains(new Wgs84(5, 5)));
		// longitude in [0,20], latitude above 20
		assertFalse(box.contains(new Wgs84(5, 25)));
	}

	@Test
	void aabbIntersectsCrossShaped() {
		Wgs84Aabb wide = new Wgs84Aabb(new Wgs84(-5, 14), new Vec2(40, 2));
		Wgs84Aabb tall = new Wgs84Aabb(new Wgs84(8, 0), new Vec2(2, 40));
		assertTrue(wide.intersects(tall));
		assertTrue(tall.intersects(wide));

		Wgs84Aabb far = new Wgs84Aabb(new Wgs84(100, 60), new Vec2(5, 5));
		assertFalse(wide.intersects(far));
		assertFalse(far.intersects(wide));
	}

	@Test
	void aabbNumTileIdsAndTileLevel() {
		Wgs84Aabb box = new Wgs84Aabb(new Wgs84(0, 10), new Vec2(20, 10));
		assertEquals(1, box.numTileIds(0));
		assertEquals(2, box.numTileIds(4));
		assertEquals(8, box.numTileIds(5));
		assertEquals(435, box.numTileIds(8));
		assertEquals(5, box.tileLevel(8));
		assertEquals(5, box.tileLevel());
		assertEquals(4, box.tileLevel(2));
		// A tiny box never reaches the threshold -> falls back to 15.
		Wgs84Aabb tiny = new Wgs84Aabb(new Wgs84(0, 0), new Vec2(0.0001, 0.0001));
		assertEquals(15, tiny.tileLevel(8));
	}

	@Test
	void aabbAntiMeridianSplit() {
		Wgs84Aabb am = new Wgs84Aabb(new Wgs84(175, 0), new Vec2(10, 5));
		assertTrue(am.containsAntiMeridian());
		Optional<Wgs84Aabb[]> split = am.splitOverAntiMeridian();
		assertTrue(split.isPresent());
		Wgs84Aabb left = split.get()[0];
		Wgs84Aabb right = split.get()[1];
		assertEquals(175.0, left.sw().longitude(), EPS);
		assertEquals(4.999999916180968, left.size().x, 1e-6);
		assertEquals(-180.0, right.sw().longitude(), EPS);
		assertEquals(5.000000083819032, right.size().x, 1e-6);

		Wgs84Aabb box = new Wgs84Aabb(new Wgs84(0, 10), new Vec2(20, 10));
		assertFalse(box.containsAntiMeridian());
		assertTrue(box.splitOverAntiMeridian().isEmpty());
	}

	@Test
	void aabbFromTilePathA() {
		// Tile (morton 0, level 10): width = 2^21 * 360/2^32 = 0.17578125 deg.
		PackedTileId tile = PackedTileId.fromTileIndex(0, 10);
		Wgs84Aabb box = new Wgs84Aabb(tile);
		assertEquals(0.0, box.sw().longitude(), EPS);
		assertEquals(0.0, box.sw().latitude(), EPS);
		assertEquals(0.17578125, box.size().x, 1e-9);
		assertEquals(0.17578125, box.size().y, 1e-9);
		assertTrue(box.valid());
	}

	@Test
	void aabbFromCenterAndTileLimit() {
		Wgs84Aabb box = Wgs84Aabb.fromCenterAndTileLimit(new Wgs84(0, 0), 16, 10);
		// targetSize = sqrt(16) * (180/2^10) = 4 * 0.17578125 = 0.703125.
		// width = 0.703125 / 0.7, height = 0.703125 * 0.7.
		assertEquals(0.703125 / 0.7, box.size().x, 1e-9);
		assertEquals(0.703125 * 0.7, box.size().y, 1e-9);
		assertTrue(box.valid());
	}

	@Test
	void aabbAvgMercatorStretchIsFinite() {
		Wgs84Aabb box = new Wgs84Aabb(new Wgs84(0, 10), new Vec2(20, 10));
		double s = box.avgMercatorStretch();
		assertTrue(Double.isFinite(s), "mercator stretch must be finite");
		assertTrue(s > 0, "mercator stretch sign positive for this box");
	}

	// --- Wgs84Polygon ---

	@Test
	void wgs84PolygonConstructorsAndValidity() {
		assertEquals(Polygon.PolygonType.SIMPLE_POLYGON, new Wgs84Polygon().type());
		assertFalse(new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(1, 0))).isValid());
		assertTrue(new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(1, 0), new Wgs84(0, 1))).isValid());

		Wgs84Polygon typed = new Wgs84Polygon(Polygon.PolygonType.TRIANGLE_LIST);
		assertEquals(Polygon.PolygonType.TRIANGLE_LIST, typed.type());

		Wgs84Polygon typedVerts = new Wgs84Polygon(Polygon.PolygonType.TRIANGLE_LIST,
				Arrays.asList(new Wgs84(0, 0), new Wgs84(1, 0), new Wgs84(0, 1)));
		assertEquals(3, typedVerts.size());
	}

	@Test
	void wgs84PolygonEqualsAndHashCode() {
		Wgs84Polygon tri = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(0, 4)));
		Wgs84Polygon same = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(0, 4)));
		Wgs84Polygon diff = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(1, 4)));
		Wgs84Polygon shorter = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0)));
		assertEquals(tri, same);
		assertEquals(tri.hashCode(), same.hashCode());
		assertNotEquals(tri, diff);
		assertNotEquals(tri, shorter);
		assertNotEquals(tri, "x");
		assertEquals(tri, tri);
	}

	@Test
	void wgs84PolygonMedianCentroid() {
		// Centroid of an asymmetric triangle: mean_lon=10, mean_lat=20.
		Wgs84 m = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(30, 0), new Wgs84(0, 60))).median();
		assertEquals(10.0, m.longitude(), 1e-9);
		assertEquals(20.0, m.latitude(), 1e-9);
	}

	@Test
	void wgs84PolygonAabbInvalidIsDefault() {
		Wgs84Aabb bb = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(1, 0))).aaBb();
		assertEquals(new Wgs84(0, 0), bb.sw());
		assertEquals(new Vec2(0, 0), bb.size());
		assertTrue(bb.valid());
	}

	@Test
	void wgs84PolygonEarthWrapperCollidesWithEverything() {
		Wgs84Polygon earth = Wgs84Polygon.earthWrappingPoly();
		assertEquals(4, earth.size());
		Wgs84Polygon tri = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(0, 4)));
		assertTrue(tri.collidesWith(earth));
		assertTrue(earth.collidesWith(tri));
	}

	@Test
	void wgs84PolygonCollisionOverlapAndDisjoint() {
		Wgs84Polygon tri = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(0, 4)));
		Wgs84Polygon overlap = new Wgs84Polygon(Arrays.asList(new Wgs84(1, 1), new Wgs84(5, 1), new Wgs84(1, 5)));
		Wgs84Polygon apart = new Wgs84Polygon(Arrays.asList(new Wgs84(20, 20), new Wgs84(24, 20), new Wgs84(20, 24)));
		assertTrue(tri.collidesWith(overlap));
		assertTrue(overlap.collidesWith(tri));
		assertFalse(tri.collidesWith(apart));
		assertFalse(apart.collidesWith(tri));
	}

	@Test
	void wgs84PolygonEqualsForeignTypeNotEqual() {
		// equals() against a non-Wgs84Polygon must report not-equal (the
		// `instanceof` false branch), mirroring Python's NotImplemented.
		Wgs84Polygon poly = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(0, 4)));
		assertNotEquals(poly, Integer.valueOf(3));
		assertNotEquals(poly, "not a polygon");
	}

	@Test
	void wgs84PolygonCollisionSeparatedByOtherAxis() {
		// self and other overlap on both the x- and y-ranges, so self's
		// axis-aligned edge normals find NO separating axis (first SAT pass
		// areSeparate(other, this) returns false). They are only separated along
		// other's own diagonal edge-normal, so the SECOND SAT pass
		// areSeparate(other, other) finds the separating axis and collidesWith
		// must return false via that second check (line ~203-204).
		Wgs84Polygon self = new Wgs84Polygon(
				Arrays.asList(new Wgs84(0, 0), new Wgs84(10, 0), new Wgs84(10, 10), new Wgs84(0, 10)));
		Wgs84Polygon other = new Wgs84Polygon(Arrays.asList(new Wgs84(13, 9), new Wgs84(9, 13), new Wgs84(15, 15)));
		assertFalse(self.collidesWith(other));
	}

	// --- PolygonTriangulation (UNIT only; not in parity vectors) ---

	@Test
	void triangulationTriangleUnchanged() {
		PolygonTriangulation tri = new PolygonTriangulation();
		Wgs84Polygon triangle = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(0, 4)));
		Wgs84Polygon r = tri.triangulateByEarClipping(triangle);
		assertEquals(Polygon.PolygonType.TRIANGLE_LIST, r.type());
		assertEquals(3, r.vertices().size());
	}

	@Test
	void triangulationConvexQuad() {
		PolygonTriangulation tri = new PolygonTriangulation();
		Wgs84Polygon quad = new Wgs84Polygon(
				Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(4, 4), new Wgs84(0, 4)));
		Wgs84Polygon r = tri.triangulateByEarClipping(quad);
		assertEquals(Polygon.PolygonType.TRIANGLE_LIST, r.type());
		assertEquals(6, r.vertices().size());
	}

	@Test
	void triangulationConcaveWithReflexVertex() {
		PolygonTriangulation tri = new PolygonTriangulation();
		// Reflex vertex at (2,2): 5 vertices -> 3 * (5-2) = 9.
		Wgs84Polygon concave = new Wgs84Polygon(
				Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(4, 4), new Wgs84(2, 2), new Wgs84(0, 4)));
		Wgs84Polygon r = tri.triangulateByEarClipping(concave);
		assertEquals(Polygon.PolygonType.TRIANGLE_LIST, r.type());
		assertEquals(9, r.vertices().size());
	}

	@Test
	void triangulationTooFewVertices() {
		PolygonTriangulation tri = new PolygonTriangulation();
		Wgs84Polygon tooFew = new Wgs84Polygon(Arrays.asList(new Wgs84(0, 0), new Wgs84(1, 0)));
		assertEquals(Polygon.PolygonType.UNKNOWN, tri.triangulateByEarClipping(tooFew).type());
	}

	@Test
	void triangulationWrongType() {
		PolygonTriangulation tri = new PolygonTriangulation();
		Wgs84Polygon notSimple = new Wgs84Polygon(Polygon.PolygonType.TRIANGLE_LIST,
				Arrays.asList(new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(0, 4)));
		assertEquals(Polygon.PolygonType.UNKNOWN, tri.triangulateByEarClipping(notSimple).type());
	}

	@Test
	void triangulationClockwiseWindingFindsNoEar() {
		// A CLOCKWISE (wrong-winding) simple polygon of >= 4 vertices: every
		// vertex is non-convex, so isEar is never set, no ear is ever found, and
		// triangulation bails out returning the UNKNOWN polygon type (the
		// "!earFound -> return UNKNOWN" branch in the ear-clipping loop).
		PolygonTriangulation tri = new PolygonTriangulation();
		Wgs84Polygon cw = new Wgs84Polygon(
				Arrays.asList(new Wgs84(0, 0), new Wgs84(0, 4), new Wgs84(4, 4), new Wgs84(4, 0)));
		assertEquals(Polygon.PolygonType.UNKNOWN, tri.triangulateByEarClipping(cw).type());
	}

	@Test
	void triangulationAsymmetricConvexEarTieBreak() {
		// An asymmetric convex quad whose candidate ears have DIFFERENT angles
		// exercises the "pick the more-extruded ear" branch
		// (angle[j] > angle[ear]). The vertices are ordered so a LATER ear (v2)
		// has a strictly larger angle than the first-found ear (v0/v1), which is
		// what forces the '>' comparison to evaluate true and reassign `ear`.
		// A symmetric quad has equal angles and never takes that '>' branch.
		// Trapezoid [(2,0),(8,0),(10,5),(0,5)]: ear angles are
		// [-0.371, -0.371, +0.371, +0.371], so v2 beats the running best v0.
		PolygonTriangulation tri = new PolygonTriangulation();
		Wgs84Polygon asym = new Wgs84Polygon(
				Arrays.asList(new Wgs84(2, 0), new Wgs84(8, 0), new Wgs84(10, 5), new Wgs84(0, 5)));
		Wgs84Polygon r = tri.triangulateByEarClipping(asym);
		assertEquals(Polygon.PolygonType.TRIANGLE_LIST, r.type());
		assertEquals(6, r.vertices().size());
	}

	@Test
	void triangulationDuplicateVertexHitsZeroLengthEdgeGuard() {
		// A duplicate consecutive vertex produces a zero-length edge. When the
		// updateVertex step normalizes that edge vector, the internal normalize()
		// hits its n == 0 guard and returns (0, 0) instead of dividing by zero.
		// Triangulation still completes (4 input vertices -> 3*(4-2) = 6).
		PolygonTriangulation tri = new PolygonTriangulation();
		Wgs84Polygon dup = new Wgs84Polygon(
				Arrays.asList(new Wgs84(0, 0), new Wgs84(0, 0), new Wgs84(4, 0), new Wgs84(0, 4)));
		Wgs84Polygon r = tri.triangulateByEarClipping(dup);
		assertEquals(Polygon.PolygonType.TRIANGLE_LIST, r.type());
		assertEquals(6, r.vertices().size());
	}
}
