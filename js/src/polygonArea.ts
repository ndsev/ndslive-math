// SPDX-License-Identifier: BSD-3-Clause
import { Vec2 } from './vec2.js';

/** Closed-rectangle relation; raw planar coordinates are never normalized. */
export enum PolygonAreaRelation {
  OUTSIDE = 0,
  INSIDE = 1,
  BOUNDARY = 2,
}
type Ring = readonly Vec2[];
/** Exact coordinate equality, including the conventional repeated closing vertex. */
function equal(a: Vec2, b: Vec2): boolean {
  return a.x === b.x && a.y === b.y;
}
/** Effective ring size without one repeated closing vertex. */
function size(ring: Ring): number {
  return ring.length > 1 && equal(ring[0], ring[ring.length - 1]) ? ring.length - 1 : ring.length;
}
/** Exact low/high difference, retaining cancellation bits. */
function difference(a: number, b: number): number[] {
  const high = a - b,
    virtualB = a - high;
  return [a - (high + virtualB) + (virtualB - b), high];
}
/** Add a scalar to a nonoverlapping expansion without rounding away its tail. */
function grow(expansion: number[], value: number): void {
  let count = 0;
  for (const term of expansion) {
    const total = value + term,
      virtualTerm = total - value;
    const low = value - (total - virtualTerm) + (term - virtualTerm);
    if (low !== 0) expansion[count++] = low;
    value = total;
  }
  expansion.length = count;
  if (value !== 0) expansion.push(value);
}
/** Orientation sign with an exact expansion fallback for ambiguous determinants. */
function cross(a: Vec2, b: Vec2, c: Vec2): number {
  const left = (b.x - a.x) * (c.y - a.y),
    right = (b.y - a.y) * (c.x - a.x);
  const determinant = left - right;
  if (Math.abs(determinant) > (Math.abs(left) + Math.abs(right)) * 8 * Number.EPSILON)
    return determinant;
  const expansion: number[] = [];
  for (const sign of [1, -1]) {
    const x = sign > 0 ? difference(b.x, a.x) : difference(b.y, a.y);
    const y = sign > 0 ? difference(c.y, a.y) : difference(c.x, a.x);
    for (const u of x)
      for (const v of y) {
        const high = u * v,
          su = 134217729 * u,
          sv = 134217729 * v;
        const uh = su - (su - u),
          vh = sv - (sv - v),
          ul = u - uh,
          vl = v - vh;
        const low = uh * vh - high + uh * vl + ul * vh + ul * vl;
        grow(expansion, sign * low);
        grow(expansion, sign * high);
      }
  }
  return expansion.length ? expansion[expansion.length - 1] : 0;
}
/** Closed segment membership. */
function on(p: Vec2, a: Vec2, b: Vec2): boolean {
  return (
    cross(a, b, p) === 0 &&
    p.x >= Math.min(a.x, b.x) &&
    p.x <= Math.max(a.x, b.x) &&
    p.y >= Math.min(a.y, b.y) &&
    p.y <= Math.max(a.y, b.y)
  );
}
/** Closed segment intersection, including collinear contact. */
function intersects(a: Vec2, b: Vec2, c: Vec2, d: Vec2): boolean {
  const ac = cross(a, b, c),
    ad = cross(a, b, d),
    ca = cross(c, d, a),
    cb = cross(c, d, b);
  return (
    (((ac < 0 && ad > 0) || (ac > 0 && ad < 0)) && ((ca < 0 && cb > 0) || (ca > 0 && cb < 0))) ||
    on(a, c, d) ||
    on(b, c, d) ||
    on(c, a, b) ||
    on(d, a, b)
  );
}
/** Even/odd point containment with boundary included. */
function contains(ring: Ring, p: Vec2): boolean {
  let inside = false;
  const n = size(ring);
  for (let i = 0; i < n; ++i) {
    const a = ring[i],
      b = ring[(i + 1) % n];
    if (on(p, a, b)) return true;
    if (a.y > p.y !== b.y > p.y && cross(a, b, p) > 0 === b.y > a.y) inside = !inside;
  }
  return inside;
}
/** Detect any contact between two boundaries. */
function ringsIntersect(a: Ring, b: Ring): boolean {
  const na = size(a),
    nb = size(b);
  for (let i = 0; i < na; ++i)
    for (let j = 0; j < nb; ++j)
      if (intersects(a[i], a[(i + 1) % na], b[j], b[(j + 1) % nb])) return true;
  return false;
}
/** Validate a finite nondegenerate simple ring without changing winding. */
function validRing(ring: Ring): boolean {
  const n = size(ring);
  if (n < 3) return false;
  let noncollinear = false;
  for (let i = 0; i < n; ++i) {
    const a = ring[i],
      b = ring[(i + 1) % n],
      previous = ring[(i + n - 1) % n];
    if (!Number.isFinite(a.x) || !Number.isFinite(a.y) || equal(a, b)) return false;
    const turn = cross(previous, a, b);
    if (!Number.isFinite(turn) || (turn === 0 && !on(a, previous, b))) return false;
    // Simplicity and a non-collinear turn avoid cancellation of shoelace sums.
    noncollinear ||= turn !== 0;
    for (let j = i + 1; j < n; ++j)
      if (j !== i + 1 && !(i === 0 && j === n - 1) && intersects(a, b, ring[j], ring[(j + 1) % n]))
        return false;
  }
  return noncollinear;
}
/** Validate a simple exterior and disjoint strictly interior holes. */
export function validPolygonArea(exterior: Ring, holes: readonly Ring[] = []): boolean {
  if (!validRing(exterior)) return false;
  for (let i = 0; i < holes.length; ++i) {
    const hole = holes[i];
    if (!validRing(hole) || !contains(exterior, hole[0]) || ringsIntersect(exterior, hole))
      return false;
    for (let j = 0; j < i; ++j)
      if (
        ringsIntersect(hole, holes[j]) ||
        contains(hole, holes[j][0]) ||
        contains(holes[j], hole[0])
      )
        return false;
  }
  return true;
}
/** Intersect prevalidated areas in one plane, including all ring boundaries. */
export function polygonAreasIntersect(
  a: Ring,
  aHoles: readonly Ring[],
  b: Ring,
  bHoles: readonly Ring[],
): boolean {
  if (!a.length || !b.length) return false;
  if ([a, ...aHoles].some((left) => [b, ...bHoles].some((right) => ringsIntersect(left, right))))
    return true;
  return (
    (contains(b, a[0]) && !bHoles.some((hole) => contains(hole, a[0]))) ||
    (contains(a, b[0]) && !aHoles.some((hole) => contains(hole, b[0])))
  );
}
/** Classify a closed rectangle against prevalidated unwrapped rings; hole boundaries count. */
export function classifyPolygonRectangle(
  exterior: Ring,
  holes: readonly Ring[],
  minimum: Vec2,
  maximum: Vec2,
): PolygonAreaRelation {
  if (
    exterior.length < 3 ||
    ![minimum.x, minimum.y, maximum.x, maximum.y].every(Number.isFinite) ||
    minimum.x > maximum.x ||
    minimum.y > maximum.y
  )
    return PolygonAreaRelation.OUTSIDE;
  const rectangle = [
    minimum,
    new Vec2(maximum.x, minimum.y),
    maximum,
    new Vec2(minimum.x, maximum.y),
  ];
  for (const ring of [exterior, ...holes])
    if (
      ring.some(
        (p) => p.x >= minimum.x && p.x <= maximum.x && p.y >= minimum.y && p.y <= maximum.y,
      ) ||
      ringsIntersect(ring, rectangle)
    )
      return PolygonAreaRelation.BOUNDARY;
  const centre = new Vec2((minimum.x + maximum.x) * 0.5, (minimum.y + maximum.y) * 0.5);
  if (!contains(exterior, centre) || holes.some((hole) => contains(hole, centre)))
    return PolygonAreaRelation.OUTSIDE;
  return PolygonAreaRelation.INSIDE;
}
