// SPDX-License-Identifier: BSD-3-Clause

const MASK_64 = (1n << 64n) - 1n;
const BIT_63 = 1n << 63n;

/**
 * Implements Morton encoding (Z-order curve) for 2D coordinates.
 * Provides methods to convert between NDS coordinates and Morton codes.
 *
 * The code is a 64-bit value held as a `bigint`, because a JS `number` cannot
 * hold 2^63 and bitwise operators on `number` are limited to 32 bits.
 *
 * Faithful port of the Python reference (`python/src/ndslive/math/morton.py`).
 */
export class MortonCode {
  private readonly mortonCode: bigint;

  /**
   * Construct a MortonCode from a raw 64-bit code value.
   *
   * Most callers use {@link MortonCode.fromNdsCoordinates} instead; this
   * constructor is for round-tripping a previously computed code.
   *
   * @param mortonCode 64-bit Morton (Z-order) code value (number or bigint).
   *   Higher bits are masked off to ensure 64-bit unsigned semantics.
   */
  constructor(mortonCode: bigint | number = 0n) {
    const v = typeof mortonCode === 'bigint' ? mortonCode : BigInt(mortonCode);
    this.mortonCode = v & MASK_64; // Ensure 64-bit unsigned
  }

  /**
   * Encode NDS integer coordinates into a Morton (Z-order) code.
   * Inverse of {@link MortonCode.toNdsCoordinates}.
   *
   * @param x NDS longitude (signed 32-bit integer). Wrapped if outside range.
   * @param y NDS latitude (signed 31-bit integer). Wrapped if outside range.
   * @returns MortonCode encoding the interleaved bit positions of `(x, y)`.
   */
  static fromNdsCoordinates(x: number | bigint, y: number | bigint): MortonCode {
    const xBase = 1n << 31n;
    const yBase = 1n << 30n;
    let bit = 1n;
    let mortonCode = 0n;

    let xi = BigInt(x);
    let yi = BigInt(y);

    while (xi >= xBase) xi -= 1n << 32n;
    while (xi < -xBase) xi += 1n << 32n;
    while (yi >= yBase) yi -= 1n << 31n;
    while (yi < -yBase) yi += 1n << 31n;

    yi <<= 1n;

    for (let i = 0; i < 31; i++) {
      mortonCode |= xi & bit;
      xi <<= 1n;
      bit <<= 1n;

      mortonCode |= yi & bit;
      yi <<= 1n;
      bit <<= 1n;
    }

    mortonCode |= xi & bit;

    mortonCode &= ~BIT_63;

    return new MortonCode(mortonCode);
  }

  /**
   * Decode this Morton code back into NDS integer coordinates.
   * Inverse of {@link MortonCode.fromNdsCoordinates}.
   *
   * @returns Tuple of `[x, y]` as signed integers — NDS longitude (32-bit)
   *   and NDS latitude (31-bit).
   */
  toNdsCoordinates(): [number, number] {
    const YBASE = 1n << 30n;
    const XBASE = 1n << 31n;
    let bit = 1n;
    let mortonCode = this.mortonCode;
    let x = 0n;
    let y = 0n;

    for (let i = 0; i < 31; i++) {
      x |= mortonCode & bit;
      mortonCode >>= 1n;
      y |= mortonCode & bit;
      bit <<= 1n;
    }

    x |= mortonCode & bit;

    if (y >= YBASE) {
      y -= 1n << 31n;
    }
    if (x >= XBASE) {
      x -= 1n << 32n;
    }

    return [Number(x), Number(y)];
  }

  /** Get the morton code value (matches the C++/Python API). */
  value(): bigint {
    return this.mortonCode;
  }

  toString(): string {
    return `MortonCode(value=${this.mortonCode})`;
  }
}
