import base64
import binascii

from app.core.exceptions import ValidationFailedError


def encode_offset_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode("ascii")).decode("ascii").rstrip("=")


def decode_offset_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0

    padded = cursor + ("=" * (-len(cursor) % 4))
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
        offset = int(decoded)
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise ValidationFailedError(
            details=[
                {
                    "location": ["query", "cursor"],
                    "message": "Cursor is invalid.",
                    "type": "value_error.cursor",
                }
            ]
        ) from error

    if offset < 0:
        raise ValidationFailedError(
            details=[
                {
                    "location": ["query", "cursor"],
                    "message": "Cursor is invalid.",
                    "type": "value_error.cursor",
                }
            ]
        )
    return offset
