ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_image_file(file):
    """
    Validates a Django UploadedFile for content type, size, and magic bytes.
    Returns None if valid, or an error detail string if invalid.
    Resets the file pointer to 0 before returning either way.
    """
    if file.content_type not in ALLOWED_TYPES:
        return f"File type '{file.content_type}' not allowed. Use JPEG, PNG, or WebP."

    if file.size > MAX_FILE_SIZE:
        return f"File too large. Maximum is 5MB, received {file.size / 1024 / 1024:.1f}MB."

    header = file.read(12)
    file.seek(0)  # reset so downstream code reads the full file

    if not _is_valid_image_bytes(header):
        return "File content does not match a valid image format."

    return None


def _is_valid_image_bytes(header: bytes) -> bool:
    """Check file magic bytes to verify it's actually an image."""
    if header[:3] == b"\xff\xd8\xff":
        return True  # JPEG
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return True  # PNG
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return True  # WebP
    return False
