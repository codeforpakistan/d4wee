from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.conf import settings
from ..models import (
    Student,
    Registration,
    Enrollment,
    Submission,
)

@login_required
@staff_member_required
def students_list(request):
    """List all students with their progress across all courses - requires staff access"""

    # Get search query
    search_query = request.GET.get("q", "").strip()

    # Get all students with approved registrations
    all_students = Student.objects.filter(
        registrations__status="APPROVED",
    ).distinct()

    # Apply search filter if query provided
    if search_query:
        all_students = all_students.filter(
            Q(full_name__icontains=search_query) | Q(email__icontains=search_query)
        )

    students = sorted(all_students, key=lambda s: s.full_name)

    # Paginate students (20 per page)
    paginator = Paginator(students, settings.PER_PAGE)
    page = request.GET.get("page", 1)

    try:
        students_page = paginator.page(page)
    except PageNotAnInteger:
        students_page = paginator.page(1)
    except EmptyPage:
        students_page = paginator.page(paginator.num_pages)

    context = {
        "students": students_page,
        "total_students": len(students),
        "search_query": search_query,
    }
    return render(request, "app/student_list.html", context)

@login_required
@staff_member_required
def student_detail(request, google_id):
    """Detailed view of a student across all their course enrollments - requires staff access"""
    from django.db.models import Prefetch
    from ..models import Attendance

    # Get student with comprehensive prefetching
    student = get_object_or_404(
        Student.objects.prefetch_related(
            Prefetch(
                "registrations",
                queryset=Registration.objects.select_related("cohort")
                .prefetch_related(
                    Prefetch(
                        "enrollments",
                        queryset=Enrollment.objects.filter(
                            status__in=["IN_PROGRESS", "COMPLETED"]
                        )
                        .select_related("course", "registration", "certificate")
                        .prefetch_related(
                            Prefetch(
                                "submissions",
                                queryset=Submission.objects.select_related(
                                    "assignment"
                                ),
                            ),
                            "course__assignments",
                        )
                        .order_by("course__name"),
                    )
                )
                .order_by("-cohort__start_date"),
            ),
            Prefetch("attendance", queryset=Attendance.objects.all().order_by("date")),
        ),
        google_id=google_id,
    )

    # Group enrollments by cohort
    from collections import defaultdict

    enrollments_by_cohort = defaultdict(list)
    for enrollment in Enrollment.objects.filter(
        registration__student=student, status__in=["IN_PROGRESS", "COMPLETED"]
    ):
        enrollments_by_cohort[enrollment.cohort].append(enrollment)

    # Sort cohorts by start date (most recent first)
    sorted_cohorts = sorted(
        enrollments_by_cohort.items(),
        key=lambda x: x[0].start_date if x[0] else "",
        reverse=True,
    )

    context = {
        "student": student,
        "student_name": student.full_name,
        "student_email": student.email,
        "enrollments_by_cohort": sorted_cohorts,
        "registrations": student.registrations.all(),
        "total_enrollments": student.enrollment_count,
        "avg_completion": student.average_completion_rate,
        "avg_score": student.average_score,
        "avg_improvement": student.average_improvement,
        "has_improvement": student.has_improvement_data,
        "avg_on_time": student.average_on_time_rate,
        "attendance_rate": student.attendance_rate,
        "attendance_records": student.attendance.all().order_by("date"),
        "total_hours": student.total_attendance_hours,
        "total_weeks": student.total_attendance_weeks,
    }
    return render(request, "app/student_detail.html", context)
