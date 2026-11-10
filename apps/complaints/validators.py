from pathlib import Path

from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
_IMAGE_FORMATS = {
	".jpg": ("JPEG", {"image/jpeg"}),
	".jpeg": ("JPEG", {"image/jpeg"}),
	".png": ("PNG", {"image/png"}),
	".webp": ("WEBP", {"image/webp"}),
}


def validate_upload(upload, *, max_size=MAX_UPLOAD_SIZE, allowed_types=None):
	normalized_name = upload.name.replace("\\", "/")
	filename = Path(normalized_name).name
	if (
		not filename
		or filename in {".", ".."}
		or any(ord(char) < 32 for char in filename)
	):
		raise ValidationError({"file": "Invalid filename."})
	upload.name = filename

	extension = Path(filename).suffix.lower()
	if extension not in ALLOWED_EXTENSIONS:
		raise ValidationError({"file": "Unsupported file type."})
	if allowed_types:
		accepted = {str(value).lower().lstrip(".") for value in allowed_types}
		if extension.lstrip(".") not in accepted:
			raise ValidationError({"file": "This file type is not allowed for this document."})
	if upload.size > min(max_size, MAX_UPLOAD_SIZE):
		raise ValidationError({"file": "Maximum upload size is 10 MB."})

	upload.seek(0)
	header = upload.read(32)
	if not header:
		raise ValidationError({"file": "Empty files are not allowed."})

	if extension == ".pdf":
		upload.seek(max(0, upload.size - 2048))
		trailer = upload.read()
		if not header.startswith(b"%PDF-") or b"%%EOF" not in trailer:
			raise ValidationError({"file": "The uploaded file is not a valid PDF."})
		content_type = getattr(upload, "content_type", None)
		if content_type and content_type not in {"application/pdf", "application/octet-stream"}:
			raise ValidationError({"file": "File content does not match its extension."})
	else:
		expected_format, content_types = _IMAGE_FORMATS[extension]
		content_type = getattr(upload, "content_type", None)
		if content_type and content_type not in content_types:
			raise ValidationError({"file": "File content does not match its extension."})
		upload.seek(0)
		try:
			with Image.open(upload) as image:
				if image.format != expected_format:
					raise ValidationError({"file": "File content does not match its extension."})
				image.verify()
		except (UnidentifiedImageError, OSError, ValueError):
			raise ValidationError({"file": "The uploaded image is invalid or corrupted."})

	upload.seek(0)
	return upload
