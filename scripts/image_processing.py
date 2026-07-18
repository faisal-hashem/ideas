import io

from PIL import Image, ImageFilter, ImageOps

MIN_RATIO = 0.8   # Instagram's 4:5 portrait limit
MAX_RATIO = 1.91  # Instagram's landscape limit


def _cover_crop(img, target_w, target_h):
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = round(src_w * scale) + 1, round(src_h * scale) + 1
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def fit_to_instagram_ratio(image_bytes):
    """Normalize to JPEG and pad (never crop) so nothing gets cut off by Instagram."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    width, height = img.size
    ratio = width / height

    if ratio < MIN_RATIO:
        target_width, target_height = round(height * MIN_RATIO), height
    elif ratio > MAX_RATIO:
        target_width, target_height = width, round(width / MAX_RATIO)
    else:
        target_width, target_height = width, height

    if (target_width, target_height) != (width, height):
        canvas = _cover_crop(img, target_width, target_height).filter(ImageFilter.GaussianBlur(40))
        canvas.paste(img, ((target_width - width) // 2, (target_height - height) // 2))
    else:
        canvas = img

    buffer = io.BytesIO()
    canvas.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()
