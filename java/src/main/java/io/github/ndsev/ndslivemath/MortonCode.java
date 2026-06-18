// SPDX-License-Identifier: MIT
package io.github.ndsev.ndslivemath;

/**
 * Implements Morton encoding (Z-order curve) for 2D NDS coordinates.
 *
 * <p>
 * The code is a 64-bit unsigned value stored in a {@code long}. Java has no
 * unsigned 64-bit primitive, so the raw {@code long} carries the same bit
 * pattern as the Python reference's unsigned value; use {@link #value()} to
 * read it and {@link Long#toUnsignedString(long)} to print it.
 * </p>
 *
 * <p>
 * Faithful port of {@code python/src/ndslive/math/morton.py}.
 * </p>
 */
public final class MortonCode {

	private final long mortonCode;

	/** Construct a MortonCode of value 0. */
	public MortonCode() {
		this(0L);
	}

	/**
	 * Construct a MortonCode from a raw 64-bit code value.
	 *
	 * @param mortonCode
	 *            the 64-bit Morton (Z-order) code value
	 */
	public MortonCode(long mortonCode) {
		// All 64 bits are significant; nothing to mask for a 64-bit container.
		this.mortonCode = mortonCode;
	}

	/**
	 * Encode NDS integer coordinates into a Morton (Z-order) code.
	 *
	 * @param x
	 *            NDS longitude (signed 32-bit integer); wrapped if out of range
	 * @param y
	 *            NDS latitude (signed 31-bit integer); wrapped if out of range
	 * @return a MortonCode encoding the interleaved bits of {@code (x, y)}
	 */
	public static MortonCode fromNdsCoordinates(long x, long y) {
		final long xBase = 1L << 31;
		final long yBase = 1L << 30;
		long bit = 1L;
		long mortonCode = 0L;

		while (x >= xBase) {
			x -= (1L << 32);
		}
		while (x < -xBase) {
			x += (1L << 32);
		}
		while (y >= yBase) {
			y -= (1L << 31);
		}
		while (y < -yBase) {
			y += (1L << 31);
		}

		y <<= 1;

		for (int i = 0; i < 31; i++) {
			mortonCode |= x & bit;
			x <<= 1;
			bit <<= 1;

			mortonCode |= y & bit;
			y <<= 1;
			bit <<= 1;
		}

		mortonCode |= x & bit;

		mortonCode &= ~(1L << 63);

		return new MortonCode(mortonCode);
	}

	/**
	 * Decode this Morton code back into NDS integer coordinates. Inverse of
	 * {@link #fromNdsCoordinates(long, long)}.
	 *
	 * @return a {@code long[]} of signed {@code {x, y}} — NDS longitude (32-bit)
	 *         and NDS latitude (31-bit)
	 */
	public long[] toNdsCoordinates() {
		final long yBase = 1L << 30;
		final long xBase = 1L << 31;
		long bit = 1L;
		long code = this.mortonCode;
		long x = 0L;
		long y = 0L;

		for (int i = 0; i < 31; i++) {
			x |= code & bit;
			code >>>= 1;
			y |= code & bit;
			bit <<= 1;
		}

		x |= code & bit;
		code >>>= 1;

		if (y >= yBase) {
			y -= (1L << 31);
		}
		if (x >= xBase) {
			x -= (1L << 32);
		}

		return new long[]{x, y};
	}

	/**
	 * Get the Morton code value (matches the C++/Python API). The returned
	 * {@code long} carries the unsigned bit pattern.
	 *
	 * @return the raw 64-bit Morton code value
	 */
	public long value() {
		return this.mortonCode;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj) {
			return true;
		}
		if (!(obj instanceof MortonCode)) {
			return false;
		}
		return this.mortonCode == ((MortonCode) obj).mortonCode;
	}

	@Override
	public int hashCode() {
		return Long.hashCode(this.mortonCode);
	}

	@Override
	public String toString() {
		return "MortonCode(value=" + Long.toUnsignedString(this.mortonCode) + ")";
	}
}
