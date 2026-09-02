from django.db.models import Q, Prefetch
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.conf import settings
from app.models import (
    Student,
    Registration,
    Enrollment,
    Cohort,
)

@login_required
@staff_member_required
def students_list(request):
    """List all students with their progress across all courses - requires staff access"""

    # Get search query
    search_query = request.GET.get("q", "").strip()
    cohort_query = request.GET.get("cohort", "").strip()

    # Get all students with approved registrations
    all_students = Student.objects.filter(
        registrations__status="APPROVED",
    )

    # Apply search filter if query provided
    if search_query:
        all_students = all_students.filter(
            Q(full_name__icontains=search_query) | Q(email__icontains=search_query)
        )

    if cohort_query:
        cohort_query = int(cohort_query)
        all_students = all_students.filter(
            Q(registrations__cohort=cohort_query)
        )

    # Paginate students (20 per page)
    paginator = Paginator(all_students, settings.PER_PAGE)
    page = request.GET.get("page", 1)

    try:
        students_page = paginator.page(page)
    except PageNotAnInteger:
        students_page = paginator.page(1)
    except EmptyPage:
        students_page = paginator.page(paginator.num_pages)

    context = {
        "students": students_page,
        "cohorts": Cohort.objects.all().order_by('id'),
        "total_students": len(all_students),
        "search_query": search_query,
        "cohort_query": cohort_query,
    }
    return render(request, "app/student_list.html", context)

@login_required
@staff_member_required
def student_detail(request, google_id):
    """Detailed view of a student across all their course enrollments - requires staff access"""
    # from django.db.models import Prefetch
    # from app.models import Attendance

    # Get student with comprehensive prefetching
    student = Student.objects.get(google_id=google_id)
    registrations = Registration.objects.filter(student=student).prefetch_related('cohort')
    enrollments = Enrollment.objects.filter(registration__in=registrations).prefetch_related('course','certificate','registration__student')


    # Group enrollments by cohort
    # from collections import defaultdict

    # enrollments_by_cohort = defaultdict(list)
    # for enrollment in Enrollment.objects.filter(
    #     registration__student=student, status__in=["IN_PROGRESS", "COMPLETED"]
    # ):
    #     enrollments_by_cohort[enrollment.cohort].append(enrollment)

    # # Sort cohorts by start date (most recent first)
    # sorted_cohorts = sorted(
    #     enrollments_by_cohort.items(),
    #     key=lambda x: x[0].start_date if x[0] else "",
    #     reverse=True,
    # )

    context = {
        "student": student,
        "enrollments": enrollments,
        "registrations": registrations,
        # "total_enrollments": student.enrollment_count,
        # "avg_completion": student.average_completion_rate,
        # "avg_score": student.average_score,
        # "avg_improvement": student.average_improvement,
        # "has_improvement": student.has_improvement_data,
        # "avg_on_time": student.average_on_time_rate,
        # "attendance_rate": student.attendance_rate,
        # "attendance_records": student.attendance.all().order_by("date"),
        # "total_hours": student.total_attendance_hours,
        # "total_weeks": student.total_attendance_weeks,
    }
    return render(request, "app/student_detail.html", context)
