import cloudinary
import cloudinary.uploader
from django.core.exceptions import ValidationError


class FileUploadService:
    """Handle file uploads to Cloudinary"""
    
    MAX_FILE_SIZES = {
        'profile_picture': 5 * 1024 * 1024,  # 5MB
        'course_thumbnail': 8 * 1024 * 1024,  # 8MB
        'document': 20 * 1024 * 1024,  # 20MB
        'project': 50 * 1024 * 1024,  # 50MB
    }
    
    ALLOWED_EXTENSIONS = {
        'profile_picture': {'jpg', 'jpeg', 'png', 'webp'},
        'course_thumbnail': {'jpg', 'jpeg', 'png', 'webp'},
        'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'},
        'project': {'zip', 'rar', '7z'},
    }
    
    @staticmethod
    def validate_file(file, file_type):
        """Validate file size and extension"""
        if not file:
            raise ValidationError("No file provided")
        
        max_size = FileUploadService.MAX_FILE_SIZES.get(file_type)
        if max_size and file.size > max_size:
            raise ValidationError(f"File size exceeds {max_size / (1024*1024):.0f}MB limit")
        
        allowed_exts = FileUploadService.ALLOWED_EXTENSIONS.get(file_type, set())
        if allowed_exts:
            file_ext = file.name.split('.')[-1].lower()
            if file_ext not in allowed_exts:
                raise ValidationError(f"File type .{file_ext} not allowed")
        
        return True
    
    @staticmethod
    def upload_profile_picture(file, user_id):
        """Upload profile picture to Cloudinary (5MB max)"""
        FileUploadService.validate_file(file, 'profile_picture')
        
        try:
            result = cloudinary.uploader.upload(
                file,
                folder="stephotec/profiles",
                public_id=f"user_{user_id}",
                overwrite=True,
                resource_type="auto",
                quality="auto",
                fetch_format="auto",
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")
    
    @staticmethod
    def upload_course_thumbnail(file, course_id):
        """Upload course thumbnail to Cloudinary (8MB max)"""
        FileUploadService.validate_file(file, 'course_thumbnail')
        
        try:
            result = cloudinary.uploader.upload(
                file,
                folder="stephotec/course-thumbnails",
                public_id=f"course_{course_id}",
                overwrite=True,
                resource_type="auto",
                quality="auto",
                fetch_format="auto",
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")
    
    @staticmethod
    def upload_document(file, course_id):
        """Upload document to Cloudinary (20MB max)"""
        FileUploadService.validate_file(file, 'document')
        
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=f"stephotec/documents/course_{course_id}",
                resource_type="auto",
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")
    
    @staticmethod
    def upload_project(file, course_id):
        """Upload project file to Cloudinary (50MB max)"""
        FileUploadService.validate_file(file, 'project')
        
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=f"stephotec/projects/course_{course_id}",
                resource_type="auto",
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")
    
    @staticmethod
    def upload_learning_material(file, course_id):
        """Upload learning material to Cloudinary (20MB max)"""
        FileUploadService.validate_file(file, 'document')
        
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=f"stephotec/learning-materials/course_{course_id}",
                resource_type="auto",
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")
    
    @staticmethod
    def delete_file(public_id):
        """Delete file from Cloudinary"""
        try:
            cloudinary.uploader.destroy(public_id)
            return True
        except Exception as e:
            raise ValidationError(f"Delete failed: {str(e)}")
