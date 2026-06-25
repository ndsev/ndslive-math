// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

import java.util.ArrayList;
import java.util.List;

/**
 * A set of vertices with a topology type and an orientation query.
 *
 * <p>
 * Port of {@code cpp/include/ndsmath/polygon.h}. The C++ class is a template
 * over a vertex container; here it is specialized directly to a list of
 * {@link Wgs84} vertices. Orientation is computed on the raw {@code (lon, lat)}
 * plane (no WGS84 normalization, no antimeridian handling).
 * </p>
 *
 * <p>
 * The base {@link #isValid()} requires at least one vertex; subclasses (e.g.
 * {@link Wgs84Polygon}) may override it.
 * </p>
 */
public class Polygon {

	/** Winding order of a polygon. Integer values match the C++ enum. */
	public enum Orientation {
		/** Clockwise winding ({@code -1}). */
		CLOCKWISE(-1),
		/** Invalid or undefined orientation ({@code 0}). */
		INVALID_ORIENTATION(0),
		/** Counter-clockwise winding ({@code 1}). */
		COUNTERCLOCKWISE(1);

		private final int value;

		Orientation(int value) {
			this.value = value;
		}

		/**
		 * @return the integer value matching the C++ enum
		 */
		public int value() {
			return this.value;
		}
	}

	/** Polygon topology. Integer values match the C++ enum. */
	public enum PolygonType {
		/**
		 * A simple polygon with an arbitrary number of vertices and no holes; the last
		 * vertex connects back to the first ({@code 0}).
		 */
		SIMPLE_POLYGON(0),
		/** A triangle strip ({@code 1}). */
		TRIANGLE_STRIP(1),
		/** A triangle fan ({@code 2}). */
		TRIANGLE_FAN(2),
		/**
		 * A set of independent triangles; three consecutive vertices form one
		 * ({@code 3}).
		 */
		TRIANGLE_LIST(3),
		/** Illegal polygon type, used to signal failure ({@code 4}). */
		UNKNOWN(4);

		private final int value;

		PolygonType(int value) {
			this.value = value;
		}

		/**
		 * @return the integer value matching the C++ enum
		 */
		public int value() {
			return this.value;
		}
	}

	/** The polygon topology type. */
	protected PolygonType polygonType;

	/** The polygon vertices. */
	protected final List<Wgs84> vertices;

	/** Construct an empty polygon of type {@code UNKNOWN}. */
	public Polygon() {
		this(PolygonType.UNKNOWN, null);
	}

	/**
	 * Construct an empty polygon of the given type.
	 *
	 * @param polygonType
	 *            the polygon topology
	 */
	public Polygon(PolygonType polygonType) {
		this(polygonType, null);
	}

	/**
	 * Construct a polygon with an initial vertex list (copied).
	 *
	 * @param polygonType
	 *            the polygon topology
	 * @param vertices
	 *            optional initial vertices (copied); may be {@code null}
	 */
	public Polygon(PolygonType polygonType, List<Wgs84> vertices) {
		this.polygonType = polygonType;
		this.vertices = (vertices != null) ? new ArrayList<>(vertices) : new ArrayList<>();
	}

	/**
	 * Append a single vertex.
	 *
	 * @param position
	 *            the vertex to append
	 */
	public void addVertex(Wgs84 position) {
		this.vertices.add(position);
	}

	/**
	 * Append a list of vertices, in order.
	 *
	 * @param vs
	 *            the vertices to append
	 */
	public void addVertices(List<Wgs84> vs) {
		this.vertices.addAll(vs);
	}

	/**
	 * Array-subscript access to a vertex (no bounds check beyond the list itself,
	 * like C++).
	 *
	 * @param index
	 *            the vertex index
	 * @return the vertex at {@code index}
	 */
	public Wgs84 get(int index) {
		return this.vertices.get(index);
	}

	/**
	 * Replace a vertex.
	 *
	 * @param index
	 *            the vertex index
	 * @param value
	 *            the replacement vertex
	 */
	public void set(int index, Wgs84 value) {
		this.vertices.set(index, value);
	}

	/**
	 * @return the number of vertices
	 */
	public int size() {
		return this.vertices.size();
	}

	/**
	 * @return the polygon type
	 */
	public PolygonType type() {
		return this.polygonType;
	}

	/**
	 * Set the polygon type.
	 *
	 * @param polygonType
	 *            the new polygon topology
	 */
	public void setType(PolygonType polygonType) {
		this.polygonType = polygonType;
	}

	/**
	 * Whether this is a valid polygon.
	 *
	 * <p>
	 * Base implementation: at least one vertex. Overridden by {@link Wgs84Polygon}
	 * to require {@code >= 3}.
	 * </p>
	 *
	 * @return {@code true} if the polygon has at least one vertex
	 */
	public boolean isValid() {
		return !this.vertices.isEmpty();
	}

	/**
	 * @return the (mutable) list of vertices
	 */
	public List<Wgs84> vertices() {
		return this.vertices;
	}

	/**
	 * Compute the winding order via the signed shoelace formula.
	 *
	 * <p>
	 * Only works for {@code SIMPLE_POLYGON} and a single-triangle
	 * {@code TRIANGLE_LIST} (exactly 3 vertices). All other types return
	 * {@code INVALID_ORIENTATION} without computing area. Collinear vertices (zero
	 * area) also return {@code INVALID_ORIENTATION}. Uses raw {@code (lon, lat)}
	 * doubles; no normalization.
	 * </p>
	 *
	 * @return the polygon's orientation
	 */
	public Orientation orientation() {
		if (this.polygonType != PolygonType.SIMPLE_POLYGON
				&& !(this.polygonType == PolygonType.TRIANGLE_LIST && this.vertices.size() == 3)) {
			return Orientation.INVALID_ORIENTATION;
		}

		int n = this.vertices.size();
		double area = 0.0;
		for (int i = 0; i < n; i++) {
			int j = (i + 1 == n) ? 0 : i + 1;
			area += this.vertices.get(i).dx() * this.vertices.get(j).dy();
			area -= this.vertices.get(i).dy() * this.vertices.get(j).dx();
		}

		if (area > 0) {
			return Orientation.COUNTERCLOCKWISE;
		} else if (area < 0) {
			return Orientation.CLOCKWISE;
		} else {
			return Orientation.INVALID_ORIENTATION;
		}
	}
}
