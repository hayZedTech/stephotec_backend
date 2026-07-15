# File Upload Restrictions & Configuration

## Overview
All file upload restrictions are centralized in one location for easy management and updates.

## Configuration Location
**Backend**: `c:\stephotec_backend\config\validators.py`

This is the **single source of truth** for all file restrictions across the entire application.

---

## Current File Restrictions

### 1. **Student Assignment Submissions**
- **Max Size**: 10MB
- **Allowed Types**: 
  - Documents: `.pdf`, `.doc`, `.docx`, `.txt`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
  - Archives: `.zip`
- **Validator**: `validate_assignment_submission_file()`
- **Location**: `AssignmentSubmission.file` model field

### 2. **Learning Content (Admin)**
- **Max Size**: 50MB (for videos)
- **Allowed Types**: `.mp4`, `.avi`, `.mov`, `.mkv`, `.flv`, `.wmv`
- **Note**: Admins are encouraged to use `video_url` field for YouTube/external videos instead of uploading
- **Validator**: `validate_video_file()`
- **Location**: `LearningContent.file` model field

### 3. **Assignment Instructions (Admin)**
- **Max Size**: 10MB
- **Allowed Types**: `.pdf`, `.doc`, `.docx`, `.txt`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
- **Validator**: `validate_document_file()`
- **Location**: `Assignment.file` model field

### 4. **Profile Pictures**
- **Max Size**: 2MB
- **Allowed Types**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- **Validator**: `validate_profile_picture()`
- **Location**: `User.profile_picture_url` (stored as Cloudinary URL)

---

## How to Modify Restrictions

### Step 1: Edit `config/validators.py`

```python
# FILE SIZE LIMITS (in bytes)
FILE_SIZE_LIMITS = {
    "document": 10 * 1024 * 1024,      # Change this to increase/decrease
    "video": 50 * 1024 * 1024,         # Change this to increase/decrease
    "profile_picture": 2 * 1024 * 1024, # Change this to increase/decrease
}

# ALLOWED FILE TYPES
ALLOWED_FILE_TYPES = {
    "document": {
        "extensions": [".pdf", ".doc", ".docx", ...],  # Add/remove extensions
        "mime_types": ["application/pdf", ...],        # Add/remove MIME types
    },
    # ... other types
}
```

### Step 2: Examples

**Increase document size to 20MB:**
```python
FILE_SIZE_LIMITS = {
    "document": 20 * 1024 * 1024,  # Changed from 10MB to 20MB
    ...
}
```

**Add `.odt` (OpenDocument) support:**
```python
ALLOWED_FILE_TYPES = {
    "document": {
        "extensions": [".pdf", ".doc", ".docx", ".odt", ...],
        "mime_types": [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.oasis.opendocument.text",  # Add this
            ...
        ],
    },
}
```

**Increase video size to 100MB:**
```python
FILE_SIZE_LIMITS = {
    "video": 100 * 1024 * 1024,  # Changed from 50MB to 100MB
    ...
}
```

### Step 3: No Code Changes Needed
- Changes in `validators.py` automatically apply to:
  - All model validators
  - All serializer validators
  - Frontend validation (update frontend separately if needed)

---

## Where Validators Are Used

### Backend Models
- `learning/models.py`:
  - `LearningContent.file` → `validate_video_file()`
  - `Assignment.file` → `validate_document_file()`
  - `AssignmentSubmission.file` → `validate_assignment_submission_file()`

### Backend Serializers
- `learning/serializers.py`:
  - `LearningContentSerializer.validate_file()`
  - `AssignmentSerializer.validate_file()`
  - `AssignmentSubmissionSerializer.validate_file()`

### Frontend
- `stephotec-portal/src/app/dashboard/assignments/page.js`:
  - File type validation
  - File size validation (10MB)
  - Accepted file types display

---

## Adding New File Types

### Example: Add `.webm` video support

1. Edit `config/validators.py`:
```python
ALLOWED_FILE_TYPES = {
    "video": {
        "extensions": [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"],  # Add .webm
        "mime_types": [
            "video/mp4",
            "video/x-msvideo",
            "video/quicktime",
            "video/x-matroska",
            "video/x-flv",
            "video/x-ms-wmv",
            "video/webm",  # Add this
        ],
    },
}
```

2. Update frontend if needed (optional):
```javascript
accept=".mp4,.avi,.mov,.mkv,.flv,.wmv,.webm"
```

---

## Validation Flow

```
User uploads file
    ↓
Frontend validation (size + type)
    ↓
Backend receives file
    ↓
Serializer validate_file() method
    ↓
Model field validator
    ↓
_validate_file() generic validator
    ↓
Check file size
    ↓
Check file extension
    ↓
Check MIME type
    ↓
File saved or error returned
```

---

## Error Messages

Users will see clear error messages:

- **Size exceeded**: "File size exceeds maximum allowed size of 10.0MB for assignment submission files."
- **Invalid type**: "Invalid file type for assignment submission. Allowed types: .pdf, .doc, .docx, .txt, .xls, .xlsx, .ppt, .pptx, .zip"
- **Invalid MIME**: "Invalid file MIME type. Please upload a valid assignment submission file."

---

## Best Practices

1. **Always update both frontend and backend** when changing restrictions
2. **Test file uploads** after making changes
3. **Document changes** in your version control
4. **Consider storage costs** when increasing file sizes (Cloudinary charges based on storage)
5. **Encourage video URLs** instead of uploads for large media files

---

## Quick Reference

| File Type | Max Size | Allowed Extensions |
|-----------|----------|-------------------|
| Documents | 10MB | .pdf, .doc, .docx, .txt, .xls, .xlsx, .ppt, .pptx |
| Videos | 50MB | .mp4, .avi, .mov, .mkv, .flv, .wmv |
| ZIP | 10MB | .zip |
| Profile Pictures | 2MB | .jpg, .jpeg, .png, .gif, .webp |

---

## Support

For questions or issues with file uploads, check:
1. `config/validators.py` - Configuration
2. `learning/models.py` - Model validators
3. `learning/serializers.py` - Serializer validators
4. `accounts/serializers.py` - Profile picture validation
