// SPDX-License-Identifier: BSD-3-Clause
//! WGS84 coordinate point with NDS coordinate conversion and geodesic helpers.
//!
//! This is a faithful port of the Python reference implementation
//! (`python/src/ndslive/math/wgs84.py`).

/// Approximate radius of Earth in meters (matches the C++/Python reference).
pub const EARTH_RADIUS_IN_METERS: f64 = 6371000.8;

/// Longitude NDS delta: `360 / (2^32 - 1)`.
pub const LON_NDS_DELTA: f64 = 360.0 / (4294967295.0); // 2^32 - 1
/// Latitude NDS delta: `180 / (2^31 - 1)`.
pub const LAT_NDS_DELTA: f64 = 180.0 / (2147483647.0); // 2^31 - 1

/// Meters per degree of latitude (and longitude at the equator).
pub const METERS_PER_DEGREE: f64 = 111320.0;

/// A point on the Earth's surface in the WGS84 coordinate system.
///
/// Mirrors the Python `Wgs84` class. Internally the Python implementation
/// stores `x` (longitude), `y` (latitude) and `z` (altitude); here those are
/// exposed as [`Wgs84::lon`], [`Wgs84::lat`] and [`Wgs84::alt`].
///
/// Construction normalizes the coordinates: longitude is wrapped into
/// `[-180, 180)` and latitude is clamped to `[-90, 90 - LAT_NDS_DELTA]`.
#[derive(Debug, Clone, Copy)]
pub struct Wgs84 {
    /// Longitude in degrees, normalized into `[-180, 180)`.
    pub lon: f64,
    /// Latitude in degrees, clamped into `[-90, 90 - LAT_NDS_DELTA]`.
    pub lat: f64,
    /// Altitude in meters above the WGS84 ellipsoid.
    pub alt: f64,
}

impl Wgs84 {
    /// Construct a WGS84 point from longitude/latitude in degrees (altitude 0).
    ///
    /// The coordinates are normalized (see [`Wgs84::normalize`]).
    pub fn new(lon: f64, lat: f64) -> Self {
        Self::with_alt(lon, lat, 0.0)
    }

    /// Construct a WGS84 point from longitude/latitude/altitude.
    ///
    /// The longitude/latitude are normalized; altitude is stored as-is.
    pub fn with_alt(lon: f64, lat: f64, alt: f64) -> Self {
        let mut p = Wgs84 { lon, lat, alt };
        p.normalize();
        p
    }

    /// Wrap longitude into `[-180, 180)` and clamp latitude into
    /// `[-90, 90 - LAT_NDS_DELTA]`.
    ///
    /// This is a direct port of the Python `normalize()` method. Call it
    /// explicitly after mutating `lon`/`lat` directly.
    pub fn normalize(&mut self) {
        // Use rem (truncated remainder) to preserve sign, matching Python
        // math.fmod / C++ std::fmod behavior.
        self.lon %= 360.0;

        // Snap a longitude close enough to +180 down to (180 - delta),
        // matching the C++ check against lonMax.
        if (self.lon - (180.0 - LON_NDS_DELTA)).abs() < LON_NDS_DELTA {
            self.lon = 180.0 - LON_NDS_DELTA;
        }

        // Wrap remaining out-of-range values into [-180, 180).
        if self.lon >= 180.0 {
            self.lon -= 360.0;
        } else if self.lon < -180.0 {
            self.lon += 360.0;
        }

        // Latitude clamping.
        if (self.lat - (90.0 - LAT_NDS_DELTA)).abs() < LAT_NDS_DELTA {
            self.lat = 90.0 - LAT_NDS_DELTA;
        }

        self.lat = self.lat.clamp(-90.0, 90.0 - LAT_NDS_DELTA);
    }

    /// Convert WGS84 coordinates to NDS integer coordinates.
    ///
    /// Uses **floor** (not truncation toward zero) per the NDS recommendation,
    /// matching `math.floor` in the Python reference.
    ///
    /// Returns `(x_nds, y_nds)`.
    pub fn to_nds_coordinates(&self) -> (i32, i32) {
        // 2^32 and 2^31 as exact f64 values.
        let x_nds = ((self.lon / 360.0) * 4294967296.0).floor();
        let y_nds = ((self.lat / 180.0) * 2147483648.0).floor();
        (x_nds as i32, y_nds as i32)
    }

    /// Construct a [`Wgs84`] point from NDS integer coordinates.
    ///
    /// Inverse of [`Wgs84::to_nds_coordinates`]. Altitude is set to 0.
    pub fn from_nds_coordinates(x: i32, y: i32) -> Wgs84 {
        let lon_multiplier = 360.0 / 4294967296.0; // 360 / 2^32
        let lat_multiplier = 180.0 / 2147483648.0; // 180 / 2^31
        let lon = (x as f64) * lon_multiplier;
        let lat = (y as f64) * lat_multiplier;
        Wgs84::new(lon, lat)
    }

    /// Convert degree distances to meters at a given latitude.
    ///
    /// Longitude distance shrinks toward the poles (scaled by
    /// `cos(at_latitude)`); latitude distance is constant.
    ///
    /// Returns `(width_meters, height_meters)`.
    pub fn degrees_to_meters(lon_degrees: f64, lat_degrees: f64, at_latitude: f64) -> (f64, f64) {
        let lon_meters = lon_degrees.abs() * METERS_PER_DEGREE * at_latitude.to_radians().cos();
        let lat_meters = lat_degrees.abs() * METERS_PER_DEGREE;
        (lon_meters, lat_meters)
    }

    /// Convert NDS coordinate distances to meters at a given latitude.
    ///
    /// Returns `(width_meters, height_meters)`.
    pub fn nds_distance_to_meters(
        nds_x_distance: i32,
        nds_y_distance: i32,
        at_latitude: f64,
    ) -> (f64, f64) {
        let lon_degrees = ((nds_x_distance as f64) / 4294967296.0) * 360.0; // / 2^32
        let lat_degrees = ((nds_y_distance as f64) / 2147483648.0) * 180.0; // / 2^31
        Wgs84::degrees_to_meters(lon_degrees, lat_degrees, at_latitude)
    }

    /// Format this point as degrees-minutes-seconds strings.
    ///
    /// Returns `(lat_str, lon_str)` in the form `"DD° MM' SS.ss\" N|S"` and
    /// `"DDD° MM' SS.ss\" E|W"`, matching the Python `to_degree_minutes_seconds`.
    pub fn to_degree_minutes_seconds(&self) -> (String, String) {
        fn convert(value: f64) -> String {
            // Mirror Python's int() truncation toward zero. `value` is always
            // non-negative here (callers pass abs()), so `trunc` == floor.
            let degrees = value.trunc() as i64;
            let minutes = ((value - degrees as f64) * 60.0).trunc() as i64;
            let seconds = (value - degrees as f64 - (minutes as f64) / 60.0) * 3600.0;
            format!("{}\u{00b0} {}' {:.2}\"", degrees, minutes, seconds)
        }

        let lat = convert(self.lat.abs()) + if self.lat < 0.0 { " S" } else { " N" };
        let lon = convert(self.lon.abs()) + if self.lon < 0.0 { " W" } else { " E" };
        (lat, lon)
    }

    /// Great-circle distance to another point, in meters (haversine formula).
    pub fn distance_to(&self, other: &Wgs84) -> f64 {
        let dlat = (other.lat - self.lat).to_radians();
        let dlon = (other.lon - self.lon).to_radians();
        let a = (dlat / 2.0).sin().powi(2)
            + self.lat.to_radians().cos()
                * other.lat.to_radians().cos()
                * (dlon / 2.0).sin().powi(2);
        let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());
        EARTH_RADIUS_IN_METERS * c
    }

    /// Initial bearing (forward azimuth) from `other` toward `self`, in radians.
    ///
    /// Measured clockwise from true north. Mirrors the Python
    /// `bearing_from(other)`: the start point is `other`, the destination is
    /// `self`.
    pub fn bearing_from(&self, other: &Wgs84) -> f64 {
        let lat1 = self.lat.to_radians();
        let lon1 = self.lon.to_radians();
        let lat2 = other.lat.to_radians();
        let lon2 = other.lon.to_radians();
        let y = (lon2 - lon1).sin() * lat2.cos();
        let x = lat1.cos() * lat2.sin() - lat1.sin() * lat2.cos() * (lon2 - lon1).cos();
        y.atan2(x)
    }
}

impl PartialEq for Wgs84 {
    /// Mirrors Python `__eq__`: longitude and latitude compared with a
    /// relative tolerance of `1e-12` (altitude is not considered, matching
    /// the reference).
    fn eq(&self, other: &Self) -> bool {
        is_close_rel(self.lon, other.lon, 1e-12) && is_close_rel(self.lat, other.lat, 1e-12)
    }
}

/// Python `math.isclose` with only a relative tolerance (`abs_tol = 0`).
fn is_close_rel(a: f64, b: f64, rel_tol: f64) -> bool {
    (a - b).abs() <= rel_tol * a.abs().max(b.abs())
}

impl std::fmt::Display for Wgs84 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Wgs84(lon={}, lat={})", self.lon, self.lat)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn origin_round_trip() {
        let p = Wgs84::new(0.0, 0.0);
        assert_eq!(p.to_nds_coordinates(), (0, 0));
    }

    #[test]
    fn floor_not_truncation_for_negatives() {
        // -1e-6 degrees must floor to -12, not truncate to 0.
        let p = Wgs84::new(-1e-06, -1e-06);
        assert_eq!(p.to_nds_coordinates(), (-12, -12));
    }

    #[test]
    fn longitude_wrap() {
        let p = Wgs84::new(360.5, 0.0);
        assert!((p.lon - 0.5).abs() < 1e-9);
        let n = Wgs84::new(-360.5, 0.0);
        assert!((n.lon - (-0.5)).abs() < 1e-9);
    }

    #[test]
    fn snap_180() {
        let p = Wgs84::new(180.0, 90.0);
        assert!((p.lon - (180.0 - LON_NDS_DELTA)).abs() < 1e-12);
        assert!((p.lat - (90.0 - LAT_NDS_DELTA)).abs() < 1e-12);
        assert_eq!(p.to_nds_coordinates(), (2147483647, 1073741823));
    }

    #[test]
    fn min_corner() {
        let p = Wgs84::new(-180.0, -90.0);
        assert!((p.lon - (-180.0)).abs() < 1e-12);
        assert!((p.lat - (-90.0)).abs() < 1e-12);
        assert_eq!(p.to_nds_coordinates(), (-2147483648, -1073741824));
    }

    #[test]
    fn dms_format() {
        let p = Wgs84::new(13.404954, 52.520008);
        let (lat, lon) = p.to_degree_minutes_seconds();
        assert!(lat.ends_with(" N"));
        assert!(lon.ends_with(" E"));
    }
}
