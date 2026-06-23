// SPDX-License-Identifier: BSD-3-Clause

// Package ndslivemath provides NDS.Live mathematical utilities for geographic
// tiling: WGS84 coordinate handling, Morton (Z-order) codes, packed tile IDs
// and NDS-coordinate bounding boxes.
//
// This is the Go port of the reference Python and C++ implementations. The
// public surface mirrors the Python package ndslive.math, adapted to idiomatic
// Go (errors instead of exceptions, multiple return values instead of tuples).
package ndslivemath

import (
	"fmt"
	"math"
)

// WGS84 / NDS conversion constants. These mirror the Python reference exactly.
const (
	// EarthRadiusInMeters is the approximate radius of Earth used for
	// great-circle (haversine) distance calculations.
	EarthRadiusInMeters = 6371000.8

	// MetersPerDegree is the approximate number of meters per degree of
	// latitude (and of longitude at the equator).
	MetersPerDegree = 111320.0
)

// LonNdsDelta and LatNdsDelta are the smallest representable angular steps in
// the NDS coordinate system. They are defined as package-level variables (not
// const) because they involve floating-point division.
var (
	// LonNdsDelta is 360 / (2^32 - 1).
	LonNdsDelta = 360.0 / float64((uint64(1)<<32)-1)
	// LatNdsDelta is 180 / (2^31 - 1).
	LatNdsDelta = 180.0 / float64((uint64(1)<<31)-1)
)

// Wgs84 represents a point on the Earth's surface using the WGS84 coordinate
// system. Lon (X) and Lat (Y) are in degrees; Alt (Z) is meters above the
// WGS84 ellipsoid.
type Wgs84 struct {
	Lon float64 // longitude in degrees, normalized into [-180, 180)
	Lat float64 // latitude in degrees, clamped into [-90, 90 - LatNdsDelta]
	Alt float64 // altitude in meters above the WGS84 ellipsoid
}

// NewWgs84 constructs a WGS84 point in degrees and normalizes it:
// longitude is wrapped into [-180, 180) and latitude is clamped into
// [-90, 90 - LatNdsDelta].
func NewWgs84(lon, lat, alt float64) Wgs84 {
	w := Wgs84{Lon: lon, Lat: lat, Alt: alt}
	w.Normalize()
	return w
}

// Normalize wraps longitude into [-180, 180) and clamps latitude into
// [-90, 90 - LatNdsDelta]. It is called automatically by NewWgs84; call it
// explicitly after mutating Lon or Lat directly.
//
// This mirrors the Python Wgs84.normalize() logic precisely, including the
// math.Mod (fmod) sign-preserving wrap and the boundary snapping for values
// very close to the positive limit.
func (w *Wgs84) Normalize() {
	// Use math.Mod (fmod) to preserve the sign, matching std::fmod / Python.
	w.Lon = math.Mod(w.Lon, 360.0)

	// Snap values very close to +180 down to 180 - LonNdsDelta.
	if math.Abs(w.Lon-(180.0-LonNdsDelta)) < LonNdsDelta {
		w.Lon = 180.0 - LonNdsDelta
	}

	// Wrap values outside [-180, 180).
	if w.Lon >= 180.0 {
		w.Lon -= 360.0
	} else if w.Lon < -180.0 {
		w.Lon += 360.0
	}

	// Latitude normalization.
	if math.Abs(w.Lat-(90.0-LatNdsDelta)) < LatNdsDelta {
		w.Lat = 90.0 - LatNdsDelta
	}
	if w.Lat > 90.0-LatNdsDelta {
		w.Lat = 90.0 - LatNdsDelta // clamp to max lat
	} else if w.Lat < -90.0 {
		w.Lat = -90.0 // clamp to min lat
	}
}

// ToNdsCoordinates converts this WGS84 point to NDS integer coordinates.
//
// NDS allows floor, truncate, or round for this conversion. Floor is used here
// (as recommended by NDS and matching the reference implementations). This is
// significant for negative coordinates, which floor toward negative infinity
// rather than truncating toward zero.
func (w Wgs84) ToNdsCoordinates() (int32, int32) {
	xNds := math.Floor((w.Lon / 360.0) * math.Exp2(32))
	yNds := math.Floor((w.Lat / 180.0) * math.Exp2(31))
	return int32(xNds), int32(yNds)
}

// Wgs84FromNdsCoordinates constructs a Wgs84 point (with Alt=0) from NDS
// integer coordinates. It is the inverse of ToNdsCoordinates.
func Wgs84FromNdsCoordinates(x, y int32) Wgs84 {
	lonMultiplier := 360.0 / math.Exp2(32)
	latMultiplier := 180.0 / math.Exp2(31)
	lon := float64(x) * lonMultiplier
	lat := float64(y) * latMultiplier
	return NewWgs84(lon, lat, 0.0)
}

// DegreesToMeters converts degree distances to meters at a given latitude.
//
// Longitude distance shrinks toward the poles (scaled by cos(latitude));
// latitude distance is constant. Returns (widthMeters, heightMeters).
func DegreesToMeters(lonDegrees, latDegrees, atLatitude float64) (float64, float64) {
	lonMeters := math.Abs(lonDegrees) * MetersPerDegree * math.Cos(degToRad(atLatitude))
	latMeters := math.Abs(latDegrees) * MetersPerDegree
	return lonMeters, latMeters
}

// NdsDistanceToMeters converts NDS coordinate distances to meters at a given
// latitude. Returns (widthMeters, heightMeters).
func NdsDistanceToMeters(ndsXDistance, ndsYDistance, atLatitude float64) (float64, float64) {
	lonDegrees := (ndsXDistance / math.Exp2(32)) * 360.0
	latDegrees := (ndsYDistance / math.Exp2(31)) * 180.0
	return DegreesToMeters(lonDegrees, latDegrees, atLatitude)
}

// DistanceTo returns the great-circle distance in meters to another point,
// computed via the haversine formula using EarthRadiusInMeters.
func (w Wgs84) DistanceTo(other Wgs84) float64 {
	dlat := degToRad(other.Lat - w.Lat)
	dlon := degToRad(other.Lon - w.Lon)
	a := math.Pow(math.Sin(dlat/2), 2) +
		math.Cos(degToRad(w.Lat))*math.Cos(degToRad(other.Lat))*math.Pow(math.Sin(dlon/2), 2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	return EarthRadiusInMeters * c
}

// BearingFrom returns the initial bearing (forward azimuth) in radians from
// other toward this point, measured clockwise from true north.
func (w Wgs84) BearingFrom(other Wgs84) float64 {
	lat1 := degToRad(w.Lat)
	lon1 := degToRad(w.Lon)
	lat2 := degToRad(other.Lat)
	lon2 := degToRad(other.Lon)
	y := math.Sin(lon2-lon1) * math.Cos(lat2)
	x := math.Cos(lat1)*math.Sin(lat2) - math.Sin(lat1)*math.Cos(lat2)*math.Cos(lon2-lon1)
	return math.Atan2(y, x)
}

// ToDegreeMinutesSeconds formats this point as degrees-minutes-seconds strings.
// It returns (latStr, lonStr) in the form "DD° MM' SS.ss\" N|S" and
// "DDD° MM' SS.ss\" E|W".
func (w Wgs84) ToDegreeMinutesSeconds() (string, string) {
	latStr := dms(math.Abs(w.Lat))
	if w.Lat < 0 {
		latStr += " S"
	} else {
		latStr += " N"
	}
	lonStr := dms(math.Abs(w.Lon))
	if w.Lon < 0 {
		lonStr += " W"
	} else {
		lonStr += " E"
	}
	return latStr, lonStr
}

// dms formats a non-negative degree value as "D° M' S.ss\"", matching the
// Python convert() helper which truncates degrees and minutes toward zero
// (int() of a non-negative value == floor).
func dms(value float64) string {
	degrees := int(value)
	minutes := int((value - float64(degrees)) * 60)
	seconds := (value - float64(degrees) - float64(minutes)/60.0) * 3600
	return fmt.Sprintf("%d° %d' %.2f\"", degrees, minutes, seconds)
}

// Equals reports whether two points have approximately equal longitude and
// latitude (relative tolerance 1e-12), mirroring Python's math.isclose.
func (w Wgs84) Equals(other Wgs84) bool {
	return isClose(w.Lon, other.Lon, 1e-12) && isClose(w.Lat, other.Lat, 1e-12)
}

func degToRad(deg float64) float64 {
	return deg * math.Pi / 180.0
}

// isClose mirrors Python's math.isclose with rel_tol and abs_tol=0.0.
func isClose(a, b, relTol float64) bool {
	return math.Abs(a-b) <= relTol*math.Max(math.Abs(a), math.Abs(b))
}
