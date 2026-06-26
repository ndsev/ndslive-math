// SPDX-License-Identifier: BSD-3-Clause

import { MortonCode } from './morton.js';

/**
 * Represents a point on the Earth's surface using the WGS84 coordinate system.
 * Provides methods for coordinate conversion, normalization, and distance
 * calculations.
 *
 * This is a faithful port of the Python reference implementation
 * (`python/src/ndslive/math/wgs84.py`).
 */
export class Wgs84 {
  /** Approximate radius of Earth in meters. */
  static readonly EARTH_RADIUS_IN_METERS = 6371000.8;
  /** Longitude quantization step of the NDS coordinate grid (degrees). */
  static readonly LON_NDS_DELTA = 360 / (2 ** 32 - 1);
  /** Latitude quantization step of the NDS coordinate grid (degrees). */
  static readonly LAT_NDS_DELTA = 180 / (2 ** 31 - 1);

  // Geometry-layer constants mirroring the C++ `Wgs84<double>` static members
  // (`cpp/include/ndsmath/wgs84.h`). These intentionally use a power-of-two
  // denominator (`2^32` / `2^31`) rather than the `LON_NDS_DELTA` /
  // `LAT_NDS_DELTA` above (which use `2^32 - 1` / `2^31 - 1`). The difference
  // shows up in the 13th significant digit, but it is load-bearing for the
  // geometry layer: `Wgs84Aabb` antimeridian handling and tile-from-index
  // construction must match the C++ reference bit-for-bit. Do NOT reuse
  // `LON_NDS_DELTA` / `LAT_NDS_DELTA` in the geometry layer.
  /** Longitude quantization step using a power-of-two denominator. */
  static readonly LON_NDS_DELTA_POW2 = 360.0 / 2 ** 32; // == 8.381903171539307e-08
  /** Latitude quantization step using a power-of-two denominator. */
  static readonly LAT_NDS_DELTA_POW2 = 180.0 / 2 ** 31; // == 8.381903171539307e-08 (equal)
  /** Minimum representable longitude. */
  static readonly LON_MIN = -180.0;
  /** Maximum representable longitude (`180 - LON_NDS_DELTA_POW2`). */
  static readonly LON_MAX = 180.0 - Wgs84.LON_NDS_DELTA_POW2; // == 179.99999991618097
  /** Minimum representable latitude. */
  static readonly LAT_MIN = -90.0;
  /** Maximum representable latitude (`90 - LAT_NDS_DELTA_POW2`). */
  static readonly LAT_MAX = 90.0 - Wgs84.LAT_NDS_DELTA_POW2;

  /** Longitude in degrees, wrapped into `[-180, 180)`. */
  x: number;
  /** Latitude in degrees, clamped to `[-90, 90 - LAT_NDS_DELTA]`. */
  y: number;
  /** Altitude in meters above the WGS84 ellipsoid. */
  z: number;

  /**
   * Construct a WGS84 point in degrees.
   *
   * @param lon Longitude in degrees. Wrapped into `[-180, 180)`.
   * @param lat Latitude in degrees. Clamped to `[-90, 90)`.
   * @param alt Altitude in meters above the WGS84 ellipsoid.
   */
  constructor(lon = 0.0, lat = 0.0, alt = 0.0) {
    this.x = lon;
    this.y = lat;
    this.z = alt;
    this.normalize();
  }

  /** Longitude in degrees (the `x` component). Mirrors the C++ accessor. */
  longitude(): number {
    return this.x;
  }

  /** Latitude in degrees (the `y` component). Mirrors the C++ accessor. */
  latitude(): number {
    return this.y;
  }

  /** The `x` (longitude) component. Mirrors the C++ `dx()` accessor. */
  dx(): number {
    return this.x;
  }

  /** The `y` (latitude) component. Mirrors the C++ `dy()` accessor. */
  dy(): number {
    return this.y;
  }

  /**
   * Wrap longitude into `[-180, 180)` and clamp latitude into `[-90, 90)`.
   *
   * Called automatically by the constructor; call explicitly after mutating
   * `x` (longitude) or `y` (latitude) directly.
   */
  normalize(): void {
    const LON_NDS_DELTA = Wgs84.LON_NDS_DELTA;
    const LAT_NDS_DELTA = Wgs84.LAT_NDS_DELTA;

    // Use a sign-preserving modulo to match Python's math.fmod / C++ std::fmod.
    this.x = fmod(this.x, 360.0);

    // Snap values very close to the maximum representable longitude down.
    if (Math.abs(this.x - (180.0 - LON_NDS_DELTA)) < LON_NDS_DELTA) {
      this.x = 180.0 - LON_NDS_DELTA;
    }

    // Wrap into [-180, 180).
    if (this.x >= 180.0) {
      this.x -= 360.0;
    } else if (this.x < -180.0) {
      this.x += 360.0;
    }

    // Latitude normalization.
    if (Math.abs(this.y - (90.0 - LAT_NDS_DELTA)) < LAT_NDS_DELTA) {
      this.y = 90.0 - LAT_NDS_DELTA;
    }

    if (this.y > 90.0 - LAT_NDS_DELTA) {
      this.y = 90.0 - LAT_NDS_DELTA; // Clamp to max lat
    } else if (this.y < -90.0) {
      this.y = -90.0; // Clamp to min lat
    }
  }

  /**
   * Convert WGS84 coordinates to NDS integer coordinates.
   *
   * NDS spec allows floor, truncate, or round operations for this conversion.
   * Floor is used here as recommended by NDS for consistency with the tiling
   * scheme. Do NOT use truncation (`| 0`, `~~`, `Math.trunc`).
   *
   * @returns Tuple of `[xNds, yNds]` as integers.
   */
  toNdsCoordinates(): [number, number] {
    const xNds = Math.floor((this.x / 360.0) * 2 ** 32);
    const yNds = Math.floor((this.y / 180.0) * 2 ** 31);
    return [xNds, yNds];
  }

  /**
   * Construct a {@link Wgs84} point from NDS integer coordinates.
   * Inverse of {@link Wgs84.toNdsCoordinates}.
   *
   * @param x NDS longitude (signed 32-bit integer).
   * @param y NDS latitude (signed 31-bit integer).
   * @returns Wgs84 point with longitude / latitude in degrees and `alt = 0`.
   */
  static fromNdsCoordinates(x: number, y: number): Wgs84 {
    const lonMultiplier = 360.0 / 2 ** 32;
    const latMultiplier = 180.0 / 2 ** 31;
    const lon = x * lonMultiplier;
    const lat = y * latMultiplier;
    return new Wgs84(lon, lat);
  }

  /**
   * Construct a {@link Wgs84} point from a {@link MortonCode}.
   *
   * Mirrors the C++ `Wgs84<double>::fromMortonCode`
   * (`cpp/include/ndsmath/wgs84.h`). Note that this scales **both** the NDS x
   * (longitude) and the NDS y (latitude) by the same factor `360 / 2^32` —
   * unlike {@link Wgs84.fromNdsCoordinates}, which scales latitude by
   * `180 / 2^31`. This difference is intentional in the reference and is relied
   * upon by the geometry layer (e.g. the `Wgs84Aabb` tile-from-index
   * constructor); do not "fix" it.
   *
   * @param mortonCode A MortonCode encoding NDS integer coordinates.
   * @returns Wgs84 point with longitude / latitude in degrees and `alt = 0`.
   */
  static fromMortonCode(mortonCode: MortonCode): Wgs84 {
    const bitScaling = 360.0 / 2 ** 32;
    const [x, y] = mortonCode.toNdsCoordinates();
    return new Wgs84(x * bitScaling, y * bitScaling);
  }

  /**
   * Convert degree distances to meters at a given latitude.
   *
   * Longitude distance varies by latitude (shrinks toward poles); latitude
   * distance is constant.
   *
   * @param lonDegrees Longitude distance in degrees.
   * @param latDegrees Latitude distance in degrees.
   * @param atLatitude The latitude where measurement is taken (affects longitude distance).
   * @returns Tuple of `[widthMeters, heightMeters]`.
   */
  static degreesToMeters(
    lonDegrees: number,
    latDegrees: number,
    atLatitude: number,
  ): [number, number] {
    const METERS_PER_DEGREE = 111320.0;

    const lonMeters = Math.abs(lonDegrees) * METERS_PER_DEGREE * Math.cos(toRadians(atLatitude));
    const latMeters = Math.abs(latDegrees) * METERS_PER_DEGREE;

    return [lonMeters, latMeters];
  }

  /**
   * Convert NDS coordinate distances to meters at a given latitude.
   *
   * @param ndsXDistance X (longitude) distance in NDS units.
   * @param ndsYDistance Y (latitude) distance in NDS units.
   * @param atLatitude The latitude where measurement is taken.
   * @returns Tuple of `[widthMeters, heightMeters]`.
   */
  static ndsDistanceToMeters(
    ndsXDistance: number,
    ndsYDistance: number,
    atLatitude: number,
  ): [number, number] {
    const lonDegrees = (ndsXDistance / 2 ** 32) * 360.0;
    const latDegrees = (ndsYDistance / 2 ** 31) * 180.0;

    return Wgs84.degreesToMeters(lonDegrees, latDegrees, atLatitude);
  }

  /**
   * Format this point as degrees-minutes-seconds strings.
   *
   * @returns Tuple of `[latStr, lonStr]` in the form
   *   `"DD° MM' SS.ss\" N|S"` and `"DDD° MM' SS.ss\" E|W"`.
   */
  toDegreeMinutesSeconds(): [string, string] {
    const convert = (value: number): string => {
      const degrees = Math.trunc(value);
      const minutes = Math.trunc((value - degrees) * 60);
      const seconds = (value - degrees - minutes / 60) * 3600;
      return `${degrees}° ${minutes}' ${seconds.toFixed(2)}"`;
    };

    const lat = convert(Math.abs(this.y)) + (this.y < 0 ? ' S' : ' N');
    const lon = convert(Math.abs(this.x)) + (this.x < 0 ? ' W' : ' E');
    return [lat, lon];
  }

  /**
   * Great-circle distance to another point, computed via the haversine formula.
   *
   * @param other Another {@link Wgs84} point.
   * @returns Distance in meters along the Earth's surface
   *   (uses {@link Wgs84.EARTH_RADIUS_IN_METERS}).
   */
  distanceTo(other: Wgs84): number {
    const dlat = toRadians(other.y - this.y);
    const dlon = toRadians(other.x - this.x);
    const a =
      Math.sin(dlat / 2) ** 2 +
      Math.cos(toRadians(this.y)) * Math.cos(toRadians(other.y)) * Math.sin(dlon / 2) ** 2;
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return Wgs84.EARTH_RADIUS_IN_METERS * c;
  }

  /**
   * Initial bearing (forward azimuth) from `other` toward this point.
   *
   * @param other Another {@link Wgs84} point — the starting point.
   * @returns Bearing in radians, measured clockwise from true north.
   */
  bearingFrom(other: Wgs84): number {
    const lat1 = toRadians(this.y);
    const lon1 = toRadians(this.x);
    const lat2 = toRadians(other.y);
    const lon2 = toRadians(other.x);
    const y = Math.sin(lon2 - lon1) * Math.cos(lat2);
    const x =
      Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(lon2 - lon1);
    return Math.atan2(y, x);
  }

  /** Component-wise equality within a small relative tolerance (1e-12). */
  equals(other: Wgs84): boolean {
    return isClose(this.x, other.x) && isClose(this.y, other.y);
  }

  /** Component-wise addition of longitude/latitude (returns a new point). */
  add(other: Wgs84): Wgs84 {
    return new Wgs84(this.x + other.x, this.y + other.y);
  }

  /** Component-wise subtraction of longitude/latitude (returns a new point). */
  sub(other: Wgs84): Wgs84 {
    return new Wgs84(this.x - other.x, this.y - other.y);
  }

  /** Component-wise multiplication of longitude/latitude (returns a new point). */
  mul(other: Wgs84): Wgs84 {
    return new Wgs84(this.x * other.x, this.y * other.y);
  }

  /** Component-wise division of longitude/latitude (returns a new point). */
  div(other: Wgs84): Wgs84 {
    return new Wgs84(this.x / other.x, this.y / other.y);
  }

  toString(): string {
    return `Wgs84(lon=${this.x}, lat=${this.y})`;
  }
}

/** Sign-preserving floating-point modulo, equivalent to C/Python `fmod`. */
function fmod(a: number, b: number): number {
  return a - Math.trunc(a / b) * b;
}

function toRadians(deg: number): number {
  return (deg * Math.PI) / 180;
}

/** Mirror of Python's `math.isclose(a, b, rel_tol=1e-12)`. */
function isClose(a: number, b: number, relTol = 1e-12): boolean {
  return Math.abs(a - b) <= relTol * Math.max(Math.abs(a), Math.abs(b));
}
