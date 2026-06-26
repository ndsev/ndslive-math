// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

import java.util.ArrayList;
import java.util.List;

/**
 * Ear-clipping polygon triangulation.
 *
 * <p>
 * Port of the C++ {@code PolygonTriangulation}
 * ({@code cpp/include/ndsmath/polygontriangulation.h} and {@code .cpp}). The
 * C++ implementation uses a pointer-linked ring of partition vertices; this
 * port uses an index-linked list of {@link PartitionVertex} ({@code previous} /
 * {@code next} integer indices) to avoid manual memory management while
 * reproducing the same traversal.
 * </p>
 *
 * <p>
 * <strong>Note:</strong> the <em>set</em> of output triangles is deterministic,
 * but the ordering of triangles and the rotation of each triangle's three
 * vertices are implementation-specific (driven by the "most extruded ear"
 * tie-break and floating-point {@code angle} comparisons). Triangulation output
 * is therefore <strong>not</strong> part of the cross-language parity vectors;
 * tests assert structure (type and vertex count) only.
 * </p>
 */
public final class PolygonTriangulation {

	/** A node in the ear-clipping ring (index-linked replacement for pointers). */
	private static final class PartitionVertex {
		boolean isActive;
		boolean isConvex;
		boolean isEar;
		Wgs84 p;
		double angle;
		int previous;
		int next;
	}

	/**
	 * Triangulate a CCW simple polygon into a {@code TRIANGLE_LIST}.
	 *
	 * @param polygon
	 *            a {@code SIMPLE_POLYGON} with at least 3 vertices, in
	 *            counter-clockwise order
	 * @return a {@link Wgs84Polygon} of type {@code TRIANGLE_LIST} on success
	 *         ({@code 3 * (n - 2)} vertices), or a polygon of type {@code UNKNOWN}
	 *         on failure (wrong type, too few vertices, or no ear found)
	 */
	public Wgs84Polygon triangulateByEarClipping(Wgs84Polygon polygon) {
		Wgs84Polygon result = new Wgs84Polygon(Polygon.PolygonType.TRIANGLE_LIST);

		if (polygon.type() != Polygon.PolygonType.SIMPLE_POLYGON || polygon.vertices().size() < 3) {
			return new Wgs84Polygon(Polygon.PolygonType.UNKNOWN);
		}

		int numVertices = polygon.vertices().size();

		// Nothing to do for a single triangle.
		if (numVertices == 3) {
			result.addVertices(new ArrayList<>(polygon.vertices()));
			return result;
		}

		List<PartitionVertex> vertices = new ArrayList<>(numVertices);
		for (int i = 0; i < numVertices; i++) {
			PartitionVertex pv = new PartitionVertex();
			pv.isActive = true;
			pv.isConvex = false;
			pv.isEar = false;
			pv.p = polygon.get(i);
			pv.angle = 0.0;
			pv.next = (i == numVertices - 1) ? 0 : i + 1;
			pv.previous = (i == 0) ? numVertices - 1 : i - 1;
			vertices.add(pv);
		}

		for (int i = 0; i < numVertices; i++) {
			updateVertex(i, vertices, numVertices);
		}

		int ear = -1;
		for (int i = 0; i < numVertices - 3; i++) {
			boolean earFound = false;

			// Find the most extruded ear (largest angle; first wins ties).
			for (int j = 0; j < numVertices; j++) {
				if (!vertices.get(j).isActive || !vertices.get(j).isEar) {
					continue;
				}
				if (!earFound) {
					earFound = true;
					ear = j;
				} else if (vertices.get(j).angle > vertices.get(ear).angle) {
					ear = j;
				}
			}

			if (!earFound) {
				return new Wgs84Polygon(Polygon.PolygonType.UNKNOWN);
			}

			PartitionVertex earV = vertices.get(ear);
			result.addVertex(vertices.get(earV.previous).p);
			result.addVertex(earV.p);
			result.addVertex(vertices.get(earV.next).p);

			earV.isActive = false;
			vertices.get(earV.previous).next = earV.next;
			vertices.get(earV.next).previous = earV.previous;

			if (i == numVertices - 4) {
				break;
			}

			updateVertex(earV.previous, vertices, numVertices);
			updateVertex(earV.next, vertices, numVertices);
		}

		for (int i = 0; i < numVertices; i++) {
			if (vertices.get(i).isActive) {
				result.addVertex(vertices.get(vertices.get(i).previous).p);
				result.addVertex(vertices.get(i).p);
				result.addVertex(vertices.get(vertices.get(i).next).p);
				break;
			}
		}

		return result;
	}

	private static Wgs84 normalize(Wgs84 p) {
		double n = Math.sqrt(p.x * p.x + p.y * p.y);
		if (n != 0.0) {
			return new Wgs84(p.x / n, p.y / n);
		}
		return new Wgs84(0.0, 0.0);
	}

	private static boolean isConvex(Wgs84 p1, Wgs84 p2, Wgs84 p3) {
		return (p3.y - p1.y) * (p2.x - p1.x) - (p3.x - p1.x) * (p2.y - p1.y) > 0.0;
	}

	private static boolean isInside(Wgs84 p1, Wgs84 p2, Wgs84 p3, Wgs84 p) {
		return !isConvex(p1, p, p2) && !isConvex(p2, p, p3) && !isConvex(p3, p, p1);
	}

	private static void updateVertex(int vIdx, List<PartitionVertex> vertices, int numVertices) {
		PartitionVertex v = vertices.get(vIdx);
		PartitionVertex v1 = vertices.get(v.previous);
		PartitionVertex v3 = vertices.get(v.next);
		v.isConvex = isConvex(v1.p, v.p, v3.p);

		Wgs84 vec1 = normalize(v1.p.sub(v.p));
		Wgs84 vec3 = normalize(v3.p.sub(v.p));

		v.angle = vec1.x * vec3.x + vec1.y * vec3.y;

		if (v.isConvex) {
			v.isEar = true;
			for (int i = 0; i < numVertices; i++) {
				Wgs84 pi = vertices.get(i).p;
				if (pi.x == v.p.x && pi.y == v.p.y) {
					continue;
				}
				if (pi.x == v1.p.x && pi.y == v1.p.y) {
					continue;
				}
				if (pi.x == v3.p.x && pi.y == v3.p.y) {
					continue;
				}
				if (isInside(v1.p, v.p, v3.p, pi)) {
					v.isEar = false;
					break;
				}
			}
		} else {
			v.isEar = false;
		}
	}
}
