// SPDX-License-Identifier: MIT
package io.github.ndsev.ndslivemath;

/**
 * Represents a point on the Earth's surface using the WGS84 coordinate system.
 *
 * <p>
 * Provides methods for coordinate conversion, normalization, and distance
 * calculations. This is an idiomatic Java port of the Python reference
 * implementation in {@code python/src/ndslive/math/wgs84.py}.
 * </p>
 *
 * <p>
 * Coordinates are stored in degrees: {@link #x} is longitude, {@link #y} is
 * latitude and {@link #z} is altitude in meters. Longitude is wrapped into
 * {@code [-180, 180)} and latitude is clamped to {@code [-90, 90)} on
 * construction.
 * </p>
 */
public final class Wgs84 {

	/** Approximate radius of Earth in meters. */
	public static final double EARTH_RADIUS_IN_METERS = 6371000.8;

	/** Longitude quantization step of the NDS coordinate grid. */
	public static final double LON_NDS_DELTA = 360.0 / (Math.pow(2, 32) - 1);

	/** Latitude quantization step of the NDS coordinate grid. */
	public static final double LAT_NDS_DELTA = 180.0 / (Math.pow(2, 31) - 1);

	private static final double METERS_PER_DEGREE = 111320.0;
	private static final double TWO_POW_31 = 2147483648.0; // 2^31
	private static final double TWO_POW_32 = 4294967296.0; // 2^32

	/** Longitude in degrees, wrapped into {@code [-180, 180)}. */
	public double x;

	/** Latitude in degrees, clamped into {@code [-90, 90)}. */
	public double y;

	/** Altitude in meters above the WGS84 ellipsoid. */
	public double z;

	/** Construct a WGS84 point at the origin (0, 0, 0). */
	public Wgs84() {
		this(0.0, 0.0, 0.0);
	}

	/**
	 * Construct a WGS84 point.
	 *
	 * @param lon
	 *            longitude in degrees, wrapped into {@code [-180, 180)}
	 * @param lat
	 *            latitude in degrees, clamped into {@code [-90, 90)}
	 */
	public Wgs84(double lon, double lat) {
		this(lon, lat, 0.0);
	}

	/**
	 * Construct a WGS84 point.
	 *
	 * @param lon
	 *            longitude in degrees, wrapped into {@code [-180, 180)}
	 * @param lat
	 *            latitude in degrees, clamped into {@code [-90, 90)}
	 * @param alt
	 *            altitude in meters above the WGS84 ellipsoid
	 */
	public Wgs84(double lon, double lat, double alt) {
		this.x = lon;
		this.y = lat;
		this.z = alt;
		normalize();
	}

	/**
	 * Wrap longitude into {@code [-180, 180)} and clamp latitude into
	 * {@code [-90, 90)}. Called automatically by the constructors; call explicitly
	 * after mutating {@link #x} or {@link #y} directly.
	 */
	public void normalize() {
		// Use Java's double % operator which has the same truncated-remainder
		// semantics as Python's math.fmod / C++ std::fmod (sign of dividend).
		this.x = this.x % 360.0;

		// Snap values very close to +180 down slightly (consistent with C++ lonMax).
		if (Math.abs(this.x - (180.0 - LON_NDS_DELTA)) < LON_NDS_DELTA) {
			this.x = 180.0 - LON_NDS_DELTA;
		}

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
			this.y = 90.0 - LAT_NDS_DELTA;
		} else if (this.y < -90.0) {
			this.y = -90.0;
		}
	}

	/**
	 * Convert WGS84 coordinates to NDS integer coordinates.
	 *
	 * <p>
	 * Uses {@link Math#floor} (not truncation), as recommended by NDS for
	 * consistency with the tiling scheme. Negative coordinates floor toward
	 * negative infinity.
	 * </p>
	 *
	 * @return a {@code long[]} of {@code {x_nds, y_nds}}
	 */
	public long[] toNdsCoordinates() {
		long xNds = (long) Math.floor((this.x / 360.0) * TWO_POW_32);
		long yNds = (long) Math.floor((this.y / 180.0) * TWO_POW_31);
		return new long[]{xNds, yNds};
	}

	/**
	 * Construct a {@link Wgs84} point from NDS integer coordinates. Inverse of
	 * {@link #toNdsCoordinates()}.
	 *
	 * @param x
	 *            NDS longitude (signed 32-bit integer)
	 * @param y
	 *            NDS latitude (signed 31-bit integer)
	 * @return a WGS84 point with longitude/latitude in degrees and {@code alt=0}
	 */
	public static Wgs84 fromNdsCoordinates(long x, long y) {
		double lonMultiplier = 360.0 / TWO_POW_32;
		double latMultiplier = 180.0 / TWO_POW_31;
		double lon = x * lonMultiplier;
		double lat = y * latMultiplier;
		return new Wgs84(lon, lat);
	}

	/**
	 * Convert degree distances to meters at a given latitude.
	 *
	 * @param lonDegrees
	 *            longitude distance in degrees
	 * @param latDegrees
	 *            latitude distance in degrees
	 * @param atLatitude
	 *            the latitude where the measurement is taken
	 * @return a {@code double[]} of {@code {width_meters, height_meters}}
	 */
	public static double[] degreesToMeters(double lonDegrees, double latDegrees, double atLatitude) {
		double lonMeters = Math.abs(lonDegrees) * METERS_PER_DEGREE * Math.cos(Math.toRadians(atLatitude));
		double latMeters = Math.abs(latDegrees) * METERS_PER_DEGREE;
		return new double[]{lonMeters, latMeters};
	}

	/**
	 * Convert NDS coordinate distances to meters at a given latitude.
	 *
	 * @param ndsXDistance
	 *            X (longitude) distance in NDS units
	 * @param ndsYDistance
	 *            Y (latitude) distance in NDS units
	 * @param atLatitude
	 *            the latitude where the measurement is taken
	 * @return a {@code double[]} of {@code {width_meters, height_meters}}
	 */
	public static double[] ndsDistanceToMeters(double ndsXDistance, double ndsYDistance, double atLatitude) {
		double lonDegrees = (ndsXDistance / TWO_POW_32) * 360.0;
		double latDegrees = (ndsYDistance / TWO_POW_31) * 180.0;
		return degreesToMeters(lonDegrees, latDegrees, atLatitude);
	}

	/**
	 * Format this point as degrees-minutes-seconds strings.
	 *
	 * @return a {@code String[]} of {@code {lat_str, lon_str}} in the form
	 *         {@code "DD° MM' SS.ss\" N|S"} and {@code "DDD° MM' SS.ss\" E|W"}
	 */
	public String[] toDegreeMinutesSeconds() {
		String lat = convertDms(Math.abs(this.y)) + (this.y < 0 ? " S" : " N");
		String lon = convertDms(Math.abs(this.x)) + (this.x < 0 ? " W" : " E");
		return new String[]{lat, lon};
	}

	private static String convertDms(double value) {
		int degrees = (int) value; // truncation toward zero, matches Python int()
		int minutes = (int) ((value - degrees) * 60);
		double seconds = (value - degrees - minutes / 60.0) * 3600.0;
		return String.format(java.util.Locale.ROOT, "%d° %d' %.2f\"", degrees, minutes, seconds);
	}

	/**
	 * Great-circle distance to another point, computed via the haversine formula.
	 *
	 * @param other
	 *            another WGS84 point
	 * @return distance in meters along the Earth's surface
	 */
	public double distanceTo(Wgs84 other) {
		double dlat = Math.toRadians(other.y - this.y);
		double dlon = Math.toRadians(other.x - this.x);
		double a = Math.pow(Math.sin(dlat / 2), 2) + Math.cos(Math.toRadians(this.y))
				* Math.cos(Math.toRadians(other.y)) * Math.pow(Math.sin(dlon / 2), 2);
		double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
		return EARTH_RADIUS_IN_METERS * c;
	}

	/**
	 * Initial bearing (forward azimuth) from {@code other} toward this point.
	 *
	 * @param other
	 *            another WGS84 point — the starting point
	 * @return bearing in radians, measured clockwise from true north
	 */
	public double bearingFrom(Wgs84 other) {
		double lat1 = Math.toRadians(this.y);
		double lon1 = Math.toRadians(this.x);
		double lat2 = Math.toRadians(other.y);
		double lon2 = Math.toRadians(other.x);
		double y = Math.sin(lon2 - lon1) * Math.cos(lat2);
		double x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(lon2 - lon1);
		return Math.atan2(y, x);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj) {
			return true;
		}
		if (!(obj instanceof Wgs84)) {
			return false;
		}
		Wgs84 other = (Wgs84) obj;
		return isClose(this.x, other.x) && isClose(this.y, other.y);
	}

	// Mirror of Python math.isclose(rel_tol=1e-12, abs_tol=0.0).
	private static boolean isClose(double a, double b) {
		double relTol = 1e-12;
		return Math.abs(a - b) <= relTol * Math.max(Math.abs(a), Math.abs(b));
	}

	@Override
	public int hashCode() {
		// Quantize to the comparison tolerance so equal points hash equally.
		long hx = Math.round(this.x / 1e-9);
		long hy = Math.round(this.y / 1e-9);
		return Long.hashCode(hx) * 31 + Long.hashCode(hy);
	}

	@Override
	public String toString() {
		return "Wgs84(lon=" + this.x + ", lat=" + this.y + ")";
	}
}
