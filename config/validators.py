"""
Centralized file upload validators and configurations.
All file restrictions can be modified in one place.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ============================================
# FILE SIZE LIMITS (in bytes)
# ============================================
FILE_SIZE_LIMITS = {
    "document": 10 * 1024 * 1024,      # 10MB for documents
    "video": 50 * 1024 * 1024,         # 50MB for videos
    "profile_picture": 5 * 1024 * 1024, # 5MB for profile pictures
}


# ============================================
# ALLOWED FILE TYPES
# ============================================
ALLOWED_FILE_TYPES = {
    "document": {
        "extensions": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"],
        "mime_types": [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ],
    },
    "zip": {
        "extensions": [".zip"],
        "mime_types": ["application/zip", "application/x-zip-compressed"],
    },
    "video": {
        "extensions": [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"],
        "mime_types": [
            "video/mp4",
            "video/x-msvideo",
            "video/quicktime",
            "video/x-matroska",
            "video/x-flv",
            "video/x-ms-wmv",
        ],
    },
    "profile_picture": {
        "extensions": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
        "mime_types": ["image/jpeg", "image/png", "image/gif", "image/webp"],
    },
}


# ============================================
# VALIDATOR FUNCTIONS
# ============================================
def validate_document_file(file):
    """Validate document files (PDF, Word, Excel, etc.)"""
    return _validate_file(
        file,
        ALLOWED_FILE_TYPES["document"],
        FILE_SIZE_LIMITS["document"],
        "document"
    )


def validate_zip_file(file):
    """Validate ZIP files"""
    return _validate_file(
        file,
        ALLOWED_FILE_TYPES["zip"],
        FILE_SIZE_LIMITS["document"],
        "ZIP"
    )


def validate_assignment_submission_file(file):
    """Validate assignment submission files (documents + zip)"""
    allowed_types = {
        "extensions": ALLOWED_FILE_TYPES["document"]["extensions"] + ALLOWED_FILE_TYPES["zip"]["extensions"],
        "mime_types": ALLOWED_FILE_TYPES["document"]["mime_types"] + ALLOWED_FILE_TYPES["zip"]["mime_types"],
    }
    return _validate_file(
        file,
        allowed_types,
        FILE_SIZE_LIMITS["document"],
        "assignment submission"
    )


def validate_video_file(file):
    """Validate video files"""
    return _validate_file(
        file,
        ALLOWED_FILE_TYPES["video"],
        FILE_SIZE_LIMITS["video"],
        "video"
    )


def validate_learning_content_file(file):
    """Validate learning content files (documents or videos)"""
    if not file:
        return
    allowed_types = {
        "extensions": ALLOWED_FILE_TYPES["document"]["extensions"] + ALLOWED_FILE_TYPES["video"]["extensions"],
        "mime_types": ALLOWED_FILE_TYPES["document"]["mime_types"] + ALLOWED_FILE_TYPES["video"]["mime_types"],
    }
    return _validate_file(
        file,
        allowed_types,
        FILE_SIZE_LIMITS["video"],  # use the larger limit
        "learning content"
    )


def validate_profile_picture(file):
    """Validate profile picture files"""
    return _validate_file(
        file,
        ALLOWED_FILE_TYPES["profile_picture"],
        FILE_SIZE_LIMITS["profile_picture"],
        "profile picture"
    )


def _validate_file(file, allowed_types, max_size, file_type_name):
    """
    Generic file validator
    
    Args:
        file: The file object to validate
        allowed_types: Dict with 'extensions' and 'mime_types' lists
        max_size: Maximum file size in bytes
        file_type_name: Human-readable name of file type
    """
    if not file:
        return
    
    # Check file size
    if file.size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise ValidationError(
            _(f"File size exceeds maximum allowed size of {max_size_mb:.1f}MB for {file_type_name} files.")
        )
    
    # Check file extension
    file_name = file.name.lower()
    file_extension = None
    for ext in allowed_types["extensions"]:
        if file_name.endswith(ext):
            file_extension = ext
            break
    
    if not file_extension:
        allowed_exts = ", ".join(allowed_types["extensions"])
        raise ValidationError(
            _(f"Invalid file type for {file_type_name}. Allowed types: {allowed_exts}")
        )
    
    # Check MIME type if available
    if hasattr(file, 'content_type') and file.content_type:
        if file.content_type not in allowed_types["mime_types"]:
            raise ValidationError(
                _(f"Invalid file MIME type. Please upload a valid {file_type_name} file.")
            )
