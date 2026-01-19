"""Observer/source helpers (placeholder for future expansion)."""

from pathlib import Path
from dataclasses import dataclass

try:
    from exiftool import ExifToolHelper
    EXIF_AVAILABLE = True
except ImportError:
    EXIF_AVAILABLE = False

@dataclass
class PhotoMetadata:
    pos: dict
    fov: tuple


def import_photo(filename: str) -> PhotoMetadata:
    """
    Minimal EXIF reader for DJI-style imagery.
    Returns lat/lon/alt and FOV if exiftool is available.
    """
    if not EXIF_AVAILABLE:
        raise RuntimeError("exiftool not installed; cannot read photo metadata")
    photo_path = Path(filename)
    if not photo_path.exists():
        raise RuntimeError(f"Photo not found: {photo_path}")
    with ExifToolHelper() as et:
        metadata = et.get_metadata(str(photo_path))[0]
    abs_alt = float(metadata.get("XMP:RelativeAltitude", metadata.get("EXIF:GPSAltitude", 0.0)))
    gps = metadata["Composite:GPSPosition"].split(" ")
    lat = float(gps[0])
    lon = float(gps[1])
    fov = float(metadata.get("Composite:FOV", 0.0))
    width = float(metadata.get("EXIF:ExifImageWidth", 1) or 1)
    height = float(metadata.get("EXIF:ExifImageHeight", 1) or 1)
    fov_tuple = (fov, fov / (width / height)) if fov else (0.0, 0.0)
    return PhotoMetadata(
        pos={"lat": lat, "lon": lon, "alt": abs_alt},
        fov=fov_tuple,
    )


__all__ = ["import_photo", "PhotoMetadata"]
