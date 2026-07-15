from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError


ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
IMAGE_CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}
PDF_CONTENT_TYPE = "application/pdf"


class FileValidationError(ValueError):
    def __init__(self, message_key: str):
        super().__init__(message_key)
        self.message_key = message_key


@dataclass(frozen=True)
class ValidatedUpload:
    extension: str
    content_type: str
    size: int


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def normalized_extension(filename: str) -> str:
    if not allowed_file(filename):
        raise FileValidationError("invalid_file_type")

    extension = filename.rsplit(".", 1)[1].lower()
    return "jpg" if extension == "jpeg" else extension


def validate_upload(file_storage, max_size: int) -> ValidatedUpload:
    extension = normalized_extension(file_storage.filename or "")
    stream = file_storage.stream
    size = _get_stream_size(stream)

    if size == 0:
        raise FileValidationError("empty_file")

    if size > max_size:
        raise FileValidationError("file_too_large")

    if extension == "pdf":
        _validate_pdf(stream)
        content_type = PDF_CONTENT_TYPE
    else:
        content_type = _validate_image(stream, extension)

    stream.seek(0)
    return ValidatedUpload(extension=extension, content_type=content_type, size=size)


def _get_stream_size(stream) -> int:
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)
    return size


def _validate_pdf(stream) -> None:
    stream.seek(0)
    if stream.read(5) != b"%PDF-":
        stream.seek(0)
        raise FileValidationError("invalid_file_type")
    stream.seek(0)


def _validate_image(stream, extension: str) -> str:
    stream.seek(0)
    try:
        with Image.open(stream) as image:
            image.verify()
            image_format = image.format
    except (OSError, UnidentifiedImageError) as error:
        stream.seek(0)
        raise FileValidationError("invalid_file_type") from error

    stream.seek(0)
    if image_format == "JPEG" and extension == "jpg":
        return IMAGE_CONTENT_TYPES[extension]
    if image_format == "PNG" and extension == "png":
        return IMAGE_CONTENT_TYPES[extension]

    raise FileValidationError("invalid_file_type")
