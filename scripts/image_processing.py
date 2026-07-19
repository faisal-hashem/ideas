import io

from PIL import Image, ImageOps


def fit_to_instagram_ratio(image_bytes):
    """Normalize orientation and re-encode as JPEG. No padding or cropping —
    Instagram handles out-of-range aspect ratios on its own."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()
