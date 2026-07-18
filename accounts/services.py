import cloudinary
import cloudinary.uploader
from django.core.exceptions import ValidationError


class FileUploadService:
    """Handle file uploads to Cloudinary"""
    
    MAX_FILE_SIZES = {
        'profile_picture': 5 * 1024 * 1024,
        'course_thumbnail': 8 * 1024 * 1024,
        'document': 20 * 1024 * 1024,
        'project': 50 * 1024 * 1024,
        'learning_material': 50 * 1024 * 1024,
    }
    
    ALLOWED_EXTENSIONS = {
        'profile_picture': {'jpg', 'jpeg', 'png', 'webp'},
        'course_thumbnail': {'jpg', 'jpeg', 'png', 'webp'},
        'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'},
        'project': {'zip', 'rar', '7z'},
        'learning_material': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'},
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
    def _get_resource_type(file):
        """Return 'video' for video files, 'raw' for everything else (docs, PDFs)."""
        video_exts = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}
        ext = file.name.split('.')[-1].lower()
        return 'video' if ext in video_exts else 'raw'

    @staticmethod
    def upload_learning_material(file, course_id):
        """Upload learning material (doc or video) to Cloudinary (50MB max)"""
        FileUploadService.validate_file(file, 'learning_material')
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=f"stephotec/learning-materials/course_{course_id}",
                resource_type=FileUploadService._get_resource_type(file),
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")
    
    @staticmethod
    def upload_submission(file, student_id):
        """Upload assignment submission to Cloudinary (20MB max)"""
        FileUploadService.validate_file(file, 'document')
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=f"stephotec/submissions/student_{student_id}",
                resource_type="raw",
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")

    @staticmethod
    def upload_certificate(file, cert_id):
        """Upload certificate file to Cloudinary (10MB max)"""
        FileUploadService.validate_file(file, 'document')
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=f"stephotec/certificates",
                public_id=f"cert_{cert_id}_{int(__import__('time').time())}",
                resource_type="raw",
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")

    @staticmethod
    def upload_handout(file, course_id):
        """Upload handout file to Cloudinary (20MB max)"""
        FileUploadService.validate_file(file, 'document')
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=f"stephotec/handouts/course_{course_id}",
                resource_type="raw",
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")

    @staticmethod
    def upload_assignment(file, course_id):
        """Upload assignment instruction file to Cloudinary (10MB max)"""
        FileUploadService.validate_file(file, 'document')
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=f"stephotec/assignments/course_{course_id}",
                resource_type="raw",
            )
            return result['secure_url']
        except Exception as e:
            raise ValidationError(f"Upload failed: {str(e)}")
