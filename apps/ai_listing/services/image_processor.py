from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .exceptions import ImageValidationError


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}
Image.MAX_IMAGE_PIXELS = 40_000_000


@dataclass(frozen=True)
class PreparedImage:
    filename: str
    mime_type: str
    data: bytes
    fingerprint: str
    width: int
    height: int


def _flatten_alpha(image: Image.Image) -> Image.Image:
    if image.mode in {"RGBA", "LA"}:
        background = Image.new("RGB", image.size, "white")
        alpha = image.getchannel("A")
        background.paste(image.convert("RGB"), mask=alpha)
        return background
    if image.mode == "P" and "transparency" in image.info:
        return _flatten_alpha(image.convert("RGBA"))
    return image.convert("RGB")


def prepare_images(files, *, max_images: int, max_image_size_mb: int, max_dimension: int = 1600) -> list[PreparedImage]:
    files = list(files)
    if not files:
        raise ImageValidationError("Analiz için en az bir fotoğraf seçmelisin.")
    if len(files) > max_images:
        raise ImageValidationError(f"En fazla {max_images} fotoğraf analiz edilebilir.")

    prepared: list[PreparedImage] = []
    max_bytes = max_image_size_mb * 1024 * 1024
    for uploaded in files:
        extension = Path(getattr(uploaded, "name", "image")).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ImageValidationError("Yalnızca JPG, JPEG, PNG ve WEBP fotoğraflar desteklenir.")
        if getattr(uploaded, "size", 0) > max_bytes:
            raise ImageValidationError(f"Her fotoğraf en fazla {max_image_size_mb} MB olabilir.")
        try:
            uploaded.seek(0)
            raw = uploaded.read()
            image = Image.open(BytesIO(raw))
            image.load()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise ImageValidationError("Fotoğraf dosyası güvenli biçimde açılamadı.") from exc
        if image.format not in SUPPORTED_FORMATS:
            raise ImageValidationError("Fotoğrafın gerçek dosya türü desteklenmiyor.")

        image = ImageOps.exif_transpose(image)
        image = _flatten_alpha(image)
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="JPEG", quality=82, optimize=True, progressive=True)
        data = output.getvalue()
        prepared.append(
            PreparedImage(
                filename=f"analysis-{len(prepared) + 1}.jpg",
                mime_type="image/jpeg",
                data=data,
                fingerprint=sha256(data).hexdigest(),
                width=image.width,
                height=image.height,
            )
        )
    return prepared
