// SPDX-License-Identifier: BSD-3-Clause
package io.github.ndsev.ndslivemath;

import java.util.ArrayList;
import java.util.List;

/**
 * Closed rectangle queries in raw planar coordinates, with open hole interiors.
 */
public final class PolygonArea {
	/** Relations have the same numeric codes as the other language ports. */
	public enum Relation {
		OUTSIDE(0), INSIDE(1), BOUNDARY(2);
		public final int value;
		/** Retain the public cross-language code. */
		Relation(int value) {
			this.value = value;
		}
	}
	/** Static geometry operations only. */
	private PolygonArea() {
	}
	/** Exact raw coordinate equality. */
	private static boolean equal(Vec2 a, Vec2 b) {
		return a.x == b.x && a.y == b.y;
	}
	/** Ignore a conventional repeated closing vertex. */
	private static int size(List<Vec2> r) {
		return r.size() > 1 && equal(r.get(0), r.get(r.size() - 1)) ? r.size() - 1 : r.size();
	}
	/** Exact low/high components of a difference. */
	private static double[] difference(double a, double b) {
		double high = a - b, virtualB = a - high;
		return new double[]{(a - (high + virtualB)) + (virtualB - b), high};
	}
	/** Add a scalar to a nonoverlapping expansion without losing bits. */
	private static void grow(ArrayList<Double> expansion, double value) {
		int count = 0;
		for (double term : expansion) {
			double total = value + term, virtualTerm = total - value;
			double low = (value - (total - virtualTerm)) + (term - virtualTerm);
			if (low != 0)
				expansion.set(count++, low);
			value = total;
		}
		expansion.subList(count, expansion.size()).clear();
		if (value != 0)
			expansion.add(value);
	}
	/**
	 * Orientation sign with an exact expansion fallback for ambiguous determinants.
	 */
	private static double cross(Vec2 a, Vec2 b, Vec2 c) {
		double left = (b.x - a.x) * (c.y - a.y), right = (b.y - a.y) * (c.x - a.x), determinant = left - right;
		if (Math.abs(determinant) > (Math.abs(left) + Math.abs(right)) * 8 * Math.ulp(1.0))
			return determinant;
		ArrayList<Double> expansion = new ArrayList<>(16);
		for (double sign : new double[]{1, -1}) {
			double[] x = sign > 0 ? difference(b.x, a.x) : difference(b.y, a.y);
			double[] y = sign > 0 ? difference(c.y, a.y) : difference(c.x, a.x);
			for (double u : x)
				for (double v : y) {
					double high = u * v;
					grow(expansion, sign * Math.fma(u, v, -high));
					grow(expansion, sign * high);
				}
		}
		return expansion.isEmpty() ? 0 : expansion.get(expansion.size() - 1);
	}
	/** Closed segment membership. */
	private static boolean on(Vec2 p, Vec2 a, Vec2 b) {
		return cross(a, b, p) == 0 && p.x >= Math.min(a.x, b.x) && p.x <= Math.max(a.x, b.x)
				&& p.y >= Math.min(a.y, b.y) && p.y <= Math.max(a.y, b.y);
	}
	/** Closed segment intersection, including collinear contact. */
	private static boolean intersects(Vec2 a, Vec2 b, Vec2 c, Vec2 d) {
		double ac = cross(a, b, c), ad = cross(a, b, d), ca = cross(c, d, a), cb = cross(c, d, b);
		return (((ac < 0 && ad > 0) || (ac > 0 && ad < 0)) && ((ca < 0 && cb > 0) || (ca > 0 && cb < 0))) || on(a, c, d)
				|| on(b, c, d) || on(c, a, b) || on(d, a, b);
	}
	/** Even/odd containment with boundary included. */
	private static boolean contains(List<Vec2> r, Vec2 p) {
		int n = size(r);
		boolean inside = false;
		for (int i = 0; i < n; ++i) {
			Vec2 a = r.get(i), b = r.get((i + 1) % n);
			if (on(p, a, b))
				return true;
			if ((a.y > p.y) != (b.y > p.y) && (cross(a, b, p) > 0) == (b.y > a.y))
				inside = !inside;
		}
		return inside;
	}
	/** Detect contact between ring boundaries. */
	private static boolean ringsIntersect(List<Vec2> a, List<Vec2> b) {
		int na = size(a), nb = size(b);
		for (int i = 0; i < na; ++i)
			for (int j = 0; j < nb; ++j)
				if (intersects(a.get(i), a.get((i + 1) % na), b.get(j), b.get((j + 1) % nb)))
					return true;
		return false;
	}
	/** Validate finite nondegenerate simple rings without changing winding. */
	private static boolean validRing(List<Vec2> r) {
		int n = size(r);
		if (n < 3)
			return false;
		boolean noncollinear = false;
		for (int i = 0; i < n; ++i) {
			Vec2 a = r.get(i), b = r.get((i + 1) % n), previous = r.get((i + n - 1) % n);
			if (!Double.isFinite(a.x) || !Double.isFinite(a.y) || equal(a, b))
				return false;
			double turn = cross(previous, a, b);
			if (!Double.isFinite(turn) || (turn == 0 && !on(a, previous, b)))
				return false;
			// Simplicity plus a non-collinear turn avoids a cancelling area sum.
			noncollinear |= turn != 0;
			for (int j = i + 1; j < n; ++j)
				if (j != i + 1 && !(i == 0 && j == n - 1) && intersects(a, b, r.get(j), r.get((j + 1) % n)))
					return false;
		}
		return noncollinear;
	}
	/** Validate a simple exterior and disjoint strictly interior holes. */
	public static boolean validPolygonArea(List<Vec2> exterior, List<List<Vec2>> holes) {
		if (!validRing(exterior))
			return false;
		for (int i = 0; i < holes.size(); ++i) {
			List<Vec2> hole = holes.get(i);
			if (!validRing(hole) || !contains(exterior, hole.get(0)) || ringsIntersect(exterior, hole))
				return false;
			for (int j = 0; j < i; ++j)
				if (ringsIntersect(hole, holes.get(j)) || contains(hole, holes.get(j).get(0))
						|| contains(holes.get(j), hole.get(0)))
					return false;
		}
		return true;
	}
	/** Intersect prevalidated areas in one plane, including all ring boundaries. */
	public static boolean polygonAreasIntersect(List<Vec2> a, List<List<Vec2>> aHoles, List<Vec2> b,
			List<List<Vec2>> bHoles) {
		if (a.isEmpty() || b.isEmpty())
			return false;
		List<List<Vec2>> left = new ArrayList<>(aHoles), right = new ArrayList<>(bHoles);
		left.add(a);
		right.add(b);
		for (List<Vec2> l : left)
			for (List<Vec2> r : right)
				if (ringsIntersect(l, r))
					return true;
		return (contains(b, a.get(0)) && bHoles.stream().noneMatch(hole -> contains(hole, a.get(0))))
				|| (contains(a, b.get(0)) && aHoles.stream().noneMatch(hole -> contains(hole, b.get(0))));
	}
	/** Test vertex or boundary contact with a rectangle. */
	private static boolean touches(List<Vec2> ring, List<Vec2> rectangle, Vec2 minimum, Vec2 maximum) {
		for (Vec2 p : ring)
			if (p.x >= minimum.x && p.x <= maximum.x && p.y >= minimum.y && p.y <= maximum.y)
				return true;
		return ringsIntersect(ring, rectangle);
	}
	/**
	 * Classify a closed rectangle against prevalidated unwrapped rings; all
	 * boundary contact counts.
	 */
	public static Relation classifyPolygonRectangle(List<Vec2> exterior, List<List<Vec2>> holes, Vec2 minimum,
			Vec2 maximum) {
		if (exterior.size() < 3 || !Double.isFinite(minimum.x) || !Double.isFinite(minimum.y)
				|| !Double.isFinite(maximum.x) || !Double.isFinite(maximum.y) || minimum.x > maximum.x
				|| minimum.y > maximum.y)
			return Relation.OUTSIDE;
		List<Vec2> rectangle = List.of(minimum, new Vec2(maximum.x, minimum.y), maximum,
				new Vec2(minimum.x, maximum.y));
		if (touches(exterior, rectangle, minimum, maximum))
			return Relation.BOUNDARY;
		for (List<Vec2> hole : holes)
			if (touches(hole, rectangle, minimum, maximum))
				return Relation.BOUNDARY;
		Vec2 centre = new Vec2((minimum.x + maximum.x) * 0.5, (minimum.y + maximum.y) * 0.5);
		if (!contains(exterior, centre))
			return Relation.OUTSIDE;
		for (List<Vec2> hole : holes)
			if (contains(hole, centre))
				return Relation.OUTSIDE;
		return Relation.INSIDE;
	}
}
