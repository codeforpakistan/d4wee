from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from ..models import (
    Attendance,
    Cohort,
    Course,
    Enrollment,
    Registration,
    Student,
)


@login_required
def index(request):
    """Coordinator dashboard"""
    # Fecth coordinator approved students
    students = (
        Student.objects.filter(
            Q(registrations__approved_by=request.user) | Q(registrations__approved_by=1)
        ).distinct()
    )

    # Get search query
    search_query = request.GET.get("q", "").strip()
    cohort_query = request.GET.get('cohort', '').strip()

    # Apply search filter if query provided
    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query) | Q(email__icontains=search_query)
        )

    if cohort_query:
        cohort_query = int(cohort_query)
        students = students.filter(Q(registrations__cohort=cohort_query))

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
        "cohorts": Cohort.objects.all().order_by("id"),
        "search_query": search_query,
        "cohort_query": cohort_query,
    }

    return render(request, "app/console.html", context)
