import math


class Wgs84:
    """
    Represents a point on the Earth's surface using the WGS84 coordinate system.
    Provides methods for coordinate conversion, normalization, and distance calculations.
    """
    EARTH_RADIUS_IN_METERS = 6371000.8  # Approximate radius of Earth in meters
    LON_NDS_DELTA = 360 / (2 ** 32 - 1)
    LAT_NDS_DELTA = 180 / (2 ** 31 - 1)

    def __init__(self, lon=0.0, lat=0.0, alt=0.0):
        self.x = lon
        self.y = lat
        self.z = alt
        self.normalize()

    def normalize(self):
        # Normalize the coordinates
        self.x = self.x % 360

        if abs(self.x - 180) < self.LON_NDS_DELTA:
            self.x = 180 - self.LON_NDS_DELTA

        if self.x < -180:
            self.x += 360
        elif self.x > 180 - self.LON_NDS_DELTA:
            self.x -= 360

        if abs(self.y - 90) < self.LAT_NDS_DELTA:
            self.y = 90 - self.LAT_NDS_DELTA

        if self.y > 90 - self.LAT_NDS_DELTA:
            self.y = 90 - self.LAT_NDS_DELTA
        elif self.y < -90:
            self.y = -90

    def to_nds_coordinates(self):
        # Convert to NDS coordinate system
        x_nds = int((self.x / 360.0) * (2 ** 32))
        y_nds = int((self.y / 180.0) * (2 ** 31))
        return x_nds, y_nds

    @staticmethod
    def from_nds_coordinates(x, y):
        # Convert from NDS coordinate system
        lon_multiplier = 360.0 / (2 ** 32)
        lat_multiplier = 180.0 / (2 ** 31)
        lon = x * lon_multiplier
        lat = y * lat_multiplier
        return Wgs84(lon, lat)

    def to_degree_minutes_seconds(self):
        def convert(value):
            degrees = int(value)
            minutes = int((value - degrees) * 60)
            seconds = (value - degrees - minutes / 60) * 3600
            return f"{degrees}° {minutes}' {seconds:.2f}\""

        lat = convert(abs(self.y)) + (' S' if self.y < 0 else ' N')
        lon = convert(abs(self.x)) + (' W' if self.x < 0 else ' E')
        return lat, lon

    def distance_to(self, other):
        # Calculate haversine distance
        dlat = math.radians(other.y - self.y)
        dlon = math.radians(other.x - self.x)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(self.y)) * math.cos(math.radians(other.y)) * math.sin(
            dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return self.EARTH_RADIUS_IN_METERS * c

    def bearing_from(self, other):
        # Calculate bearing from another Wgs84 coordinate
        lat1, lon1, lat2, lon2 = map(math.radians, [self.y, self.x, other.y, other.x])
        y = math.sin(lon2 - lon1) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        return math.atan2(y, x)

    def __eq__(self, other):
        return math.isclose(self.x, other.x, rel_tol=1e-12) and math.isclose(self.y, other.y, rel_tol=1e-12)

    def __add__(self, other):
        return Wgs84(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Wgs84(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        return Wgs84(self.x * other.x, self.y * other.y)

    def __truediv__(self, other):
        return Wgs84(self.x / other.x, self.y / other.y)

    def __str__(self):
        return f"Wgs84(lon={self.x}, lat={self.y})"
