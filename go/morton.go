// SPDX-License-Identifier: MIT

package ndslivemath

// MortonCode implements Morton encoding (Z-order curve) for 2D NDS
// coordinates. It wraps a 64-bit unsigned value and provides conversion
// to and from NDS integer coordinates.
type MortonCode struct {
	value uint64
}

// NewMortonCode constructs a MortonCode from a raw 64-bit code value.
//
// Most callers use MortonFromNdsCoordinates instead; this constructor is for
// round-tripping a previously computed code. The value is stored as-is (it is
// already 64-bit unsigned in Go, so no masking is needed for the full width).
func NewMortonCode(value uint64) MortonCode {
	return MortonCode{value: value}
}

// Value returns the raw 64-bit Morton code value (matches the C++/Python API).
func (m MortonCode) Value() uint64 {
	return m.value
}

// MortonFromNdsCoordinates encodes NDS integer coordinates into a Morton
// (Z-order) code. It is the inverse of MortonCode.ToNdsCoordinates.
//
// x is NDS longitude (signed 32-bit), y is NDS latitude (signed 31-bit); both
// are wrapped into range before encoding. Bit 63 is masked off, matching the
// Python/C++ reference (morton_code &= ~(1 << 63)).
//
// The interleave loop is ported verbatim from morton.py. Note that the
// arithmetic is performed on signed 64-bit values (mirroring Python's
// arbitrary-precision ints and C++'s int64_t), then OR-ed into the unsigned
// accumulator. Using int64 here is essential: the X high bit is extracted at
// bit position 62 during the 32nd X step, and y is shifted left by 1 up front,
// so values can exceed the int32 range during the loop.
func MortonFromNdsCoordinates(xIn, yIn int32) MortonCode {
	const xBase int64 = 1 << 31
	const yBase int64 = 1 << 30

	x := int64(xIn)
	y := int64(yIn)

	for x >= xBase {
		x -= 1 << 32
	}
	for x < -xBase {
		x += 1 << 32
	}
	for y >= yBase {
		y -= 1 << 31
	}
	for y < -yBase {
		y += 1 << 31
	}

	y <<= 1

	var bit int64 = 1
	var morton uint64

	for i := 0; i < 31; i++ {
		morton |= uint64(x & bit)
		x <<= 1
		bit <<= 1

		morton |= uint64(y & bit)
		y <<= 1
		bit <<= 1
	}

	morton |= uint64(x & bit)
	x <<= 1
	bit <<= 1

	morton &^= 1 << 63 // clear bit 63 (Go's AND NOT)

	return MortonCode{value: morton}
}

// ToNdsCoordinates decodes this Morton code back into NDS integer coordinates.
// It is the inverse of MortonFromNdsCoordinates and returns (x, y) as signed
// NDS longitude (32-bit) and latitude (31-bit).
//
// The deinterleave loop is ported verbatim from morton.py. The accumulators x
// and y are computed as int64 (the same width the encoder used) and then
// sign-adjusted against XBASE / YBASE before being narrowed to int32.
func (m MortonCode) ToNdsCoordinates() (int32, int32) {
	const yBase uint64 = 1 << 30
	const xBase uint64 = 1 << 31

	var bit uint64 = 1
	morton := m.value
	var x, y uint64

	for i := 0; i < 31; i++ {
		x |= morton & bit
		morton >>= 1
		y |= morton & bit
		bit <<= 1
	}

	x |= morton & bit
	morton >>= 1

	// Sign-adjust: x has up to 32 magnitude bits, y up to 31. Convert the
	// extracted unsigned magnitudes back into signed NDS coordinates.
	xs := int64(x)
	ys := int64(y)
	if y >= yBase {
		ys -= 1 << 31
	}
	if x >= xBase {
		xs -= 1 << 32
	}

	return int32(xs), int32(ys)
}
