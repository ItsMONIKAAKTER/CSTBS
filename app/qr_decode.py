"""Decode uploaded QR photographs when browser camera scanning is unavailable.

The photo never leaves the CSTBS server. Images are bounded by upload size and
pixel count, and only a token authenticated by ticketing.resolve_ticket_token
can authorize entry. No attendee data is read from QR payloads.
"""
from io import BytesIO


def decode_qr_photo(content):
    """Return decoded QR text, or None for an invalid/unreadable image."""
    if not isinstance(content, bytes) or len(content) > 3 * 1024 * 1024 or not content:
        return None
    from PIL import Image, ImageOps, UnidentifiedImageError
    try:
        Image.MAX_IMAGE_PIXELS = 12_000_000
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > 12_000_000 or min(image.size) < 64:
                return None
            image = ImageOps.exif_transpose(image).convert("RGB")
            if max(image.size) > 2600:
                image.thumbnail((2600, 2600))
            # OpenCV can decode QR from JPEG/PNG/WebP without browser features.
            import cv2
            import numpy as np
            frame = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
            decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(frame)
            return decoded[:1000] if decoded else None
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
        return None
