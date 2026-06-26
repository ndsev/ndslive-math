// SPDX-License-Identifier: BSD-3-Clause

package ndslivemath

import "math"

// Vec2 is a plain, un-normalized 2D vector (X, Y).
//
// The geometry layer (Wgs84AABB in particular) needs a raw (dx, dy) extent that
// can legitimately exceed 360 / 180 degrees or be negative — unlike Wgs84,
// whose constructor wraps longitude and clamps latitude. Reusing Wgs84 for a
// size/extent would silently corrupt those values via normalization, so this
// small struct is used instead.
//
// It mirrors the role of glm::dvec2 (used as Wgs84<T>::vec2_t) in the C++
// reference (cpp/include/ndsmath/wgs84aabb.h). X is the longitude/horizontal
// component, Y the latitude/vertical component.
type Vec2 struct {
	X float64
	Y float64
}

// NewVec2 constructs a Vec2 from its X and Y components.
func NewVec2(x, y float64) Vec2 {
	return Vec2{X: x, Y: y}
}

// Add returns the component-wise sum of this vector and other.
func (v Vec2) Add(other Vec2) Vec2 {
	return Vec2{X: v.X + other.X, Y: v.Y + other.Y}
}

// Sub returns the component-wise difference of this vector and other.
func (v Vec2) Sub(other Vec2) Vec2 {
	return Vec2{X: v.X - other.X, Y: v.Y - other.Y}
}

// Scale returns this vector with both components multiplied by scalar.
func (v Vec2) Scale(scalar float64) Vec2 {
	return Vec2{X: v.X * scalar, Y: v.Y * scalar}
}

// Abs returns the component-wise absolute value of this vector.
func (v Vec2) Abs() Vec2 {
	return Vec2{X: math.Abs(v.X), Y: math.Abs(v.Y)}
}
