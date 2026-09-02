from django.http import FileResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ..models import (
    Attendance,
    Certificate,
    Cohort,
    Course,
    Enrollment,
    Registration,
    Student,
    StudentGrades,
    Submission,
)


def index(request):
    # Staff members go to cohorts page as their home
    return render(request, "app/public_home.html")


def privacy(request):
    return render(request, "app/privacy.html")

def terms(request):
    return render(request, "app/terms.html")

def list_courses(request):
    courses = Course.objects.filter(is_visible=True).all()
    return render(request, 'app/courses/index.html', {
        'items': courses
    })

def detail_courses(request, google_id):
    course = Course.objects.get(google_id=google_id)
    courses = Course.objects.filter(is_visible=True).all()
    return render(request, 'app/courses/detail.html', {
        'items': courses,
        'item': course
    })




@login_required
def issues(request):
    """Issues landing page - show all issue categories"""

    # For now, no automatic issues since Attendance uses proper FKs
    # Future issue detection can be added here

    issue_categories = [
        # Future issue types can be added here
        # {
        #     'title': 'Duplicate Enrollments',
        #     'description': 'Students enrolled multiple times in the same course',
        #     'count': 0,
        #     'url': 'issues_duplicate_enrollments',
        #     'icon': 'users',
        #     'severity': 'warning',
        # },
    ]

    context = {
        "issue_categories": issue_categories,
        "total_issues": sum(cat["count"] for cat in issue_categories),
    }
    return render(request, "app/issues.html", context)


@login_required
def enroll_in_course(request, course_id):
    """Enroll student in a course within their cohort"""
    if request.method != "POST":
        return redirect("home")

    # Get cohort_id from POST data
    cohort_id = request.POST.get("cohort_id")
    if not cohort_id:
        messages.error(request, "Cohort information missing.")
        return redirect("home")

    # Get student
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("home")

    # Get course and cohort
    course = get_object_or_404(Course, id=course_id)
    cohort = get_object_or_404(Cohort, id=cohort_id)

    # Verify student has approved registration for this cohort
    registration = Registration.objects.filter(
        student=student, cohort=cohort, status="APPROVED"
    ).first()

    if not registration:
        messages.error(request, f"You are not registered for the {cohort.name} cohort.")
        return redirect("home")

    # Check if already enrolled
    existing = Enrollment.objects.filter(
        registration__student=student, course=course
    ).first()

    if existing:
        existing.status = Enrollment.StatusChoices.IN_PROGRESS
        existing.save()
        messages.info(request, f"You have been re-enrolled in {course.name}.")
        return redirect("home")

    # Check enrollment limit (max 5 courses per cohort)
    current_enrollment_count = Enrollment.objects.filter(
        registration=registration
    ).count()
    if current_enrollment_count >= 5:
        messages.error(
            request,
            f"You cannot enroll in more than 5 courses in the {cohort.name} cohort.",
        )
        return redirect("home")

    # Create enrollment
    Enrollment.objects.create(
        course=course, registration=registration, status="IN_PROGRESS"
    )

    messages.success(request, f"Successfully enrolled in {course.name}!")
    return redirect("home")


# @login_required
# def unenroll_from_course(request, enrollment_id):
#     """Allow student to unenroll from a course"""
#     if request.method != 'POST':
#         return redirect('home')
#
#     # Get student
#     try:
#         student = Student.objects.get(user=request.user)
#     except Student.DoesNotExist:
#         messages.error(request, 'Student profile not found.')
#         return redirect('home')
#
#     # Get enrollment and verify it belongs to this student
#     enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=student)
#
#     course_name = enrollment.course.name
#
#     # Delete the enrollment
#     enrollment.delete()
#
#     messages.success(request, f'Successfully unenrolled from {course_name}.')
#     return redirect('home')
# Disabled: Students cannot unenroll from courses


@login_required
def my_certificates(request):
    """Display certificates for the logged-in student"""
    # Get student
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("home")

    # Get all enrollments with certificate info
    enrollments = (
        Enrollment.objects.filter(student=student)
        .select_related("course", "cohort", "registration", "certificate")
        .order_by("-cohort__start_date", "course__name")
    )

    # Build data structure with certificates and eligibility info
    certificates_data = []
    for enrollment in enrollments:
        # Get certificate if it exists (using the OneToOne relationship)
        course_cert = (
            enrollment.certificate if hasattr(enrollment, "certificate") else None
        )

        certificates_data.append(
            {
                "enrollment": enrollment,
                "course": enrollment.course,
                "cohort": enrollment.cohort,
                "is_eligible": enrollment.certificate_eligible,
                "eligibility_notes": enrollment.certificate_eligibility_notes,
                "certificate": course_cert,
                "completion_rate": enrollment.completion_rate,
                "average_score": enrollment.overall_average_score,
            }
        )

    context = {
        "student": student,
        "certificates_data": certificates_data,
    }
    return render(request, "app/my_certificates.html", context)


@staff_member_required
def issue_certificate(request, enrollment_id):
    """Issue a certificate for an enrollment"""
    from datetime import date

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("home")

    # Get the enrollment
    enrollment = get_object_or_404(
        Enrollment.objects.select_related(
            "registration__student", "course", "registration"
        ),
        id=enrollment_id,
    )

    # Check eligibility
    if not enrollment.certificate_eligible:
        messages.error(
            request,
            f"Student is not eligible for certificate for {enrollment.course.name}. {enrollment.certificate_eligibility_notes}",
        )
        return redirect(request.META.get("HTTP_REFERER", "home"))

    # Check if certificate already exists
    if hasattr(enrollment, "certificate"):
        messages.warning(
            request,
            f"Certificate already issued for {enrollment.student.full_name} - {enrollment.course.name}",
        )
        return redirect(request.META.get("HTTP_REFERER", "home"))

    # Create certificate
    try:
        from ..services import generate_certificate

        cert = Certificate.objects.create(
            enrollment=enrollment,
            issued_date=date.today(),
            completion_percentage=enrollment.completion_rate or 0,
            average_grade=enrollment.overall_average_score,
            notes=f"Issued by {request.user.username}",
        )

        # Generate and save certificate file
        certificate_file = generate_certificate(cert)
        cert.certificate_file.save(certificate_file.name, certificate_file, save=True)

        messages.success(
            request,
            f"Certificate issued for {enrollment.student.full_name} - {enrollment.course.name}",
        )
    except Exception as e:
        messages.error(request, f"Error issuing certificate: {str(e)}")

    return redirect(request.META.get("HTTP_REFERER", "home"))


@staff_member_required
def delete_certificate(request, certificate_id):
    """Delete a certificate record (staff only)"""
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("home")

    # Get the certificate
    certificate = get_object_or_404(Certificate, id=certificate_id)

    student_name = certificate.registration.student.full_name
    course_name = certificate.course.name if certificate.course else "Cohort"

    try:
        # Delete the file if it exists
        if certificate.certificate_file:
            certificate.certificate_file.delete(save=False)

        # Delete the certificate record
        certificate.delete()

        messages.success(
            request, f"Certificate deleted for {student_name} - {course_name}"
        )
    except Exception as e:
        messages.error(request, f"Error deleting certificate: {str(e)}")

    return redirect(request.META.get("HTTP_REFERER", "home"))


def test_certificate(request):
    """Test view to preview certificate template"""
    context = {
        "name": "Jane Doe",
        "course": "Digital Marketing Fundamentals",
        "period": "January 2026 - May 2026",
    }

    return render(request, "certificate/certificate.html", context)


def view_certificate(request, student_google_id, course_google_id):
    """View a student's certificate for a specific course"""
    from django.shortcuts import get_object_or_404

    # Get the student and course
    student = get_object_or_404(Student, google_id=student_google_id)
    course = get_object_or_404(Course, google_id=course_google_id)

    # Find the certificate for this student and course
    certificate = (
        Certificate.objects.filter(
            enrollment__registration__student=student, enrollment__course=course
        )
        .select_related(
            "enrollment__registration__student",
            "enrollment__course",
            "enrollment__registration__cohort",
        )
        .first()
    )

    if not certificate:
        messages.error(request, "Certificate not found")
        return redirect("home")

    # Get cohort dates
    cohort = certificate.enrollment.cohort
    period = (
        f"{cohort.start_date.strftime('%B %Y')} - {cohort.end_date.strftime('%B %Y')}"
    )

    context = {
        "name": student.full_name,
        "course": certificate.enrollment.course.name,
        "period": period,
    }

    return render(request, "certificate/certificate.html", context)


# =============================================================================
# STAFF VIEWS FOR REGISTRATIONS
# =============================================================================
