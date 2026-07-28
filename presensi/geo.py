import math

EARTH_RADIUS_M = 6_371_000


def jarak_meter(lat1, lng1, lat2, lng2):
    """Jarak antara dua titik GPS (meter), dihitung dengan formula Haversine.

    Dipakai sebagai pengganti PostGIS/GDAL, yang tidak tersedia di
    lingkungan dev proyek ini (lihat CLAUDE.md bagian 2). Untuk cek geofence
    berskala puluhan-ratusan meter, akurasinya cukup (error << 1%).
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def dalam_radius(lat, lng, lokasi):
    """True kalau titik (lat, lng) berada di dalam radius_meter LokasiKantor."""
    jarak = jarak_meter(lat, lng, lokasi.latitude, lokasi.longitude)
    return jarak <= lokasi.radius_meter
