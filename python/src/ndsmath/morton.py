class MortonCode:
    """
    Implements Morton encoding (Z-order curve) for 2D coordinates.
    Provides methods to convert between NDS coordinates and Morton codes.
    """

    def __init__(self, morton_code=0):
        self.morton_code = morton_code & ((1 << 64) - 1)  # Ensure 64-bit unsigned

    @staticmethod
    def from_nds_coordinates(x, y):
        x_base = 1 << 31
        y_base = 1 << 30
        bit = 1
        morton_code = 0

        x = int(x)
        y = int(y)

        while x >= x_base:
            x -= (1 << 32)
        while x < -x_base:
            x += (1 << 32)
        while y >= y_base:
            y -= (1 << 31)
        while y < -y_base:
            y += (1 << 31)

        y <<= 1

        for i in range(31):
            morton_code |= x & bit
            x <<= 1
            bit <<= 1

            morton_code |= y & bit
            y <<= 1
            bit <<= 1

        morton_code |= x & bit
        x <<= 1
        bit <<= 1

        morton_code &= ~(1 << 63)

        return MortonCode(morton_code)

    def to_nds_coordinates(self):
        YBASE = 1 << 30
        XBASE = 1 << 31
        bit = 1
        morton_code = self.morton_code
        x = y = 0

        for i in range(31):
            x |= morton_code & bit
            morton_code >>= 1
            y |= morton_code & bit
            bit <<= 1

        x |= morton_code & bit
        morton_code >>= 1

        if y >= YBASE:
            y -= (1 << 31)
        if x >= XBASE:
            x -= (1 << 32)

        return x, y

    def value(self):
        """Get the morton code value (matches C++ API)."""
        return self.morton_code

    def __str__(self):
        return f"MortonCode(value={self.morton_code})"
