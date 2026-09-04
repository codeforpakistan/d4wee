from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Prefetch

from app.models import (
    Attendance,
    Cohort,
    Course,
    Enrollment,
    Registration,
    Student,
)


@login_required
def index(request):
    """Main dashboard view - public home or authenticated dashboard"""

    user = User.objects.get(pk=request.user.id)
    try: 
        student = Student.objects.get(user=user)
    except: 
        student = None

    registrations = Registration.objects.filter(student=student).prefetch_related('cohort')
    enrollments = Enrollment.objects.filter(registration__in=registrations).prefetch_related('course','certificate','registration__student')
    cohorts = Cohort.objects.prefetch_related(
        Prefetch('registrations', queryset=Registration.objects.filter(student=student))
    ).filter(is_open_for_registration=True)
    courses = Course.objects.exclude(enrollments__id__in=enrollments).filter(is_available=True)

    # # Get or create student profile for logged-in user
    # try:
    #     student = Student.objects.prefetch_related(
    #         Prefetch(
    #             "registrations",
    #             queryset=Registration.objects.select_related("cohort")
    #             .prefetch_related(
    #                 Prefetch(
    #                     "enrollments",
    #                     queryset=Enrollment.objects.filter(
    #                         status__in=["IN_PROGRESS", "COMPLETED"]
    #                     )
    #                     .select_related("course", "registration", "certificate")
    #                     .prefetch_related(
    #                         "course__assignments", "submissions__assignment"
    #                     )
    #                     .order_by("course__name"),
    #                 )
    #             )
    #             .order_by("-cohort__start_date"),
    #         )
    #     ).get(user=request.user)
    # except Student.DoesNotExist:
    #     # Try to find existing student by email (from Google Classroom sync or admin creation)
    #     try:
    #         student = Student.objects.prefetch_related(
    #             Prefetch(
    #                 "registrations",
    #                 queryset=Registration.objects.select_related("cohort")
    #                 .prefetch_related(
    #                     Prefetch(
    #                         "enrollments",
    #                         queryset=Enrollment.objects.filter(
    #                             status__in=["IN_PROGRESS", "COMPLETED"]
    #                         )
    #                         .select_related("course", "registration", "certificate")
    #                         .prefetch_related(
    #                             "course__assignments", "submissions__assignment"
    #                         )
    #                         .order_by("course__name"),
    #                     )
    #                 )
    #                 .order_by("-cohort__start_date"),
    #             )
    #         ).get(email=request.user.email)
    #         # Link this existing student to the user account
    #         student.user = request.user
    #         student.save()
    #     except Student.DoesNotExist:
    #         # No student profile - show available cohorts for registration
    #         # Student profile will be auto-created when they register for a cohort
    #         open_cohorts = Cohort.objects.filter(
    #             is_open_for_registration=True
    #         ).order_by("-start_date")

    #         # Build cohort data with registration status
    #         available_cohorts_data = []
    #         for cohort in open_cohorts:
    #             available_cohorts_data.append(
    #                 {
    #                     "cohort": cohort,
    #                     "can_register": cohort.can_accept_registrations,
    #                     "current_count": cohort.total_enrolled_students,
    #                 }
    #             )

    #         return render(
    #             request,
    #             "app/registration_home.html",
    #             {
    #                 "user": request.user,
    #                 "available_cohorts_data": available_cohorts_data,
    #             },
    #         )

    # # Get approved and pending registrations
    # approved_registrations = (
    #     Registration.objects.filter(student=student, status="APPROVED")
    #     .select_related("cohort")
    #     .order_by("-created_at")
    # )

    # pending_registrations = (
    #     Registration.objects.filter(student=student, status="PENDING")
    #     .select_related("cohort")
    #     .order_by("-created_at")
    # )

    # # Get enrolled course IDs
    # enrolled_course_ids = Enrollment.objects.filter(
    #     registration__student=student, status__in=["IN_PROGRESS", "COMPLETED"]
    # ).values_list("course_id", flat=True)

    # # Get available courses (flat list, no cohort grouping)
    # available_courses = []
    # primary_cohort = None
    # primary_cohort_enrollment_count = 0
    # if approved_registrations.exists():
    #     # Use the first approved registration's cohort for enrollment
    #     primary_registration = approved_registrations.first()
    #     primary_cohort = primary_registration.cohort

    #     # Count enrollments in the primary cohort only
    #     primary_cohort_enrollment_count = Enrollment.objects.filter(
    #         registration=primary_registration, status__in=["IN_PROGRESS", "COMPLETED"]
    #     ).count()

    #     # Show ALL visible courses, not just ones with existing enrollments
    #     available_courses = (
    #         Course.objects.filter(is_visible=True, course_state=Course.StatusChoices.ACTIVE)
    #         .exclude(
    #             id__in=enrolled_course_ids  # Exclude already enrolled courses
    #         )
    #         .prefetch_related("assignments")
    #         .order_by("name")
    #     )

    # # Get cohorts available for registration
    # open_cohorts = Cohort.objects.filter(is_open_for_registration=True).order_by(
    #     "-start_date"
    # )

    # # Get student's existing registrations
    # existing_registration_cohort_ids = Registration.objects.filter(
    #     student=student
    # ).values_list("cohort_id", flat=True)

    # # Build available cohorts data
    # available_cohorts_data = []
    # for cohort in open_cohorts:
    #     is_registered = cohort.id in existing_registration_cohort_ids
    #     registration = None
    #     if is_registered:
    #         registration = Registration.objects.filter(
    #             student=student, cohort=cohort
    #         ).first()

    #     available_cohorts_data.append(
    #         {
    #             "cohort": cohort,
    #             "is_registered": is_registered,
    #             "registration": registration,
    #             "can_register": cohort.can_accept_registrations and not is_registered,
    #             "current_count": cohort.total_enrolled_students,
    #         }
    #     )

    # # Check if student can mark attendance this week
    # from datetime import date

    # today = date.today()

    # # Check if already marked for today and get hours
    # today_attendance = Attendance.objects.filter(student=student, date=today).first()

    # marked_today = today_attendance is not None
    # hours_today = today_attendance.hours_spent if today_attendance else 0

    # context = {
    #     "student": student,
    #     "student_name": student.full_name,
    #     "student_email": student.email,
    #     "enrollments": Enrollment.objects.filter(
    #         registration__student=student,
    #         course__is_visible=True,
    #         status__in=["IN_PROGRESS", "COMPLETED"],
    #     ),
    #     "total_enrollments": student.enrollment_count,
    #     "primary_cohort_enrollment_count": primary_cohort_enrollment_count,
    #     "avg_completion": student.average_completion_rate,
    #     "avg_assignment": student.average_score,
    #     "avg_improvement": student.average_improvement,
    #     "has_improvement": student.has_improvement_data,
    #     "avg_on_time": student.average_on_time_rate,
    #     "available_courses": available_courses,
    #     "primary_cohort": primary_cohort,
    #     "has_pending_registration": pending_registrations.exists(),
    #     "available_cohorts_data": available_cohorts_data,
    #     "can_mark_attendance": student.has_active_registration,
    #     "marked_today": marked_today,
    #     "hours_today": hours_today,
    #     "attendance_rate": student.attendance_rate,
    #     "total_hours": student.total_attendance_hours,
    # }

    context = {
        'student': student,
        'enrollments': enrollments,
        'cohorts': cohorts,
        'courses': courses
    }
    return render(request, "app/dashboard.html", context)
