import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Course, StudentCourse

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        role=User.Role.ADMIN
    )


@pytest.fixture
def course(db):
    """Create a test course"""
    return Course.objects.create(
        name='Web Development',
        code_prefix='WD'
    )


@pytest.fixture
def another_course(db):
    """Create another test course"""
    return Course.objects.create(
        name='Mobile Development',
        code_prefix='MD'
    )


@pytest.fixture
def student_user(db, course):
    """Create a student user with a course"""
    user = User.objects.create_user(
        username='STEPH000001',
        email='student@test.com',
        password='testpass123',
        role=User.Role.STUDENT,
        first_name='John',
        last_name='Doe'
    )
    StudentCourse.objects.create(
        student=user,
        course=course,
        admission_year=2024,
        is_primary=True
    )
    return user


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.mark.django_db
class TestStudentCourseModel:
    """Test StudentCourse model"""

    def test_create_student_course(self, student_user, course):
        """Test creating a StudentCourse"""
        sc = StudentCourse.objects.get(student=student_user, course=course)
        assert sc.enrollment_id is not None
        assert sc.admission_year == 2024
        assert sc.is_primary is True
        assert sc.status == StudentCourse.Status.ACTIVE

    def test_enrollment_id_generation(self, student_user, course):
        """Test automatic enrollment ID generation"""
        sc = StudentCourse.objects.get(student=student_user, course=course)
        # Format: WD/24/0001
        assert sc.enrollment_id.startswith('WD/24/')

    def test_multiple_courses_per_student(self, db, student_user, another_course):
        """Test student can have multiple courses"""
        StudentCourse.objects.create(
            student=student_user,
            course=another_course,
            admission_year=2024,
            is_primary=False
        )
        courses = student_user.courses.all()
        assert courses.count() == 2

    def test_course_status_per_course(self, db, student_user, course, another_course):
        """Test course status is independent per course"""
        sc1 = StudentCourse.objects.get(student=student_user, course=course)
        sc2 = StudentCourse.objects.create(
            student=student_user,
            course=another_course,
            admission_year=2024,
            status=StudentCourse.Status.COMPLETED
        )
        assert sc1.status == StudentCourse.Status.ACTIVE
        assert sc2.status == StudentCourse.Status.COMPLETED


@pytest.mark.django_db
class TestStudentCreationAPI:
    """Test student creation with courses"""

    def test_create_student_with_course(self, api_client, admin_user, course):
        """Test creating a student with a course"""
        api_client.force_authenticate(user=admin_user)
        payload = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@test.com',
            'course_id': course.id,
            'admission_year': 2024,
            'is_primary': True,
        }
        response = api_client.post('/api/v1/admin/students/', payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'temporary_password' in response.data
        assert 'student_details' in response.data
        # Verify StudentCourse was created
        user = User.objects.get(email='jane@test.com')
        assert user.courses.count() == 1

    def test_student_list_includes_courses(self, api_client, admin_user, student_user):
        """Test student list includes course history"""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/admin/students/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
        student_data = response.data['results'][0]
        assert 'courses' in student_data
        assert len(student_data['courses']) > 0


@pytest.mark.django_db
class TestStudentCourseManagementAPI:
    """Test StudentCourse management endpoints"""

    def test_list_student_courses(self, api_client, admin_user, student_user):
        """Test listing student's courses"""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(
            f'/api/v1/admin/students/{student_user.id}/courses/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_add_course_to_student(self, api_client, admin_user, student_user, another_course):
        """Test adding a course to existing student"""
        api_client.force_authenticate(user=admin_user)
        payload = {
            'course': another_course.id,
            'admission_year': 2024,
            'is_primary': False,
        }
        response = api_client.post(
            f'/api/v1/admin/students/{student_user.id}/courses/',
            payload
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert student_user.courses.count() == 2

    def test_update_course_status(self, api_client, admin_user, student_user):
        """Test updating course status"""
        api_client.force_authenticate(user=admin_user)
        sc = student_user.courses.first()
        payload = {
            'status': StudentCourse.Status.COMPLETED,
            'completed_at': '2024-12-31'
        }
        response = api_client.patch(
            f'/api/v1/admin/students/{student_user.id}/courses/{sc.id}/',
            payload
        )
        assert response.status_code == status.HTTP_200_OK
        sc.refresh_from_db()
        assert sc.status == StudentCourse.Status.COMPLETED

    def test_remove_course_from_student(self, api_client, admin_user, student_user):
        """Test removing a course from student"""
        api_client.force_authenticate(user=admin_user)
        sc = student_user.courses.first()
        response = api_client.delete(
            f'/api/v1/admin/students/{student_user.id}/courses/{sc.id}/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert student_user.courses.count() == 0


@pytest.mark.django_db
class TestCourseDeleteProtection:
    """Test course deletion protection"""

    def test_cannot_delete_course_with_students(self, api_client, admin_user, course, student_user):
        """Test course cannot be deleted if students enrolled"""
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(f'/api/v1/courses/{course.id}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot be deleted' in response.data['detail'].lower()

    def test_can_delete_course_without_students(self, api_client, admin_user, another_course):
        """Test course can be deleted if no students enrolled"""
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(f'/api/v1/courses/{another_course.id}/')
        assert response.status_code == status.HTTP_200_OK
