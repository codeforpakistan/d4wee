from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import render

from ..models import (
    Cohort,
    Student,
    StudentReport,
)


@login_required
def index(request):
    """Coordinator dashboard"""
    # Get search query
    search_query = request.GET.get("q", "").strip()
    cohort_query = request.GET.get('cohort', '').strip()

    # Fetch coordinator approved students
    students = (
        Student.objects.filter(
            Q(registrations__approved_by=request.user)
        ).distinct()
    )

    # Apply search filter if query provided
    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query) | Q(email__icontains=search_query)
        )

    if cohort_query:
        cohort_query = int(cohort_query)
        students = students.filter(Q(registrations__cohort=cohort_query))

    grades = StudentReport.objects.filter(email__in=students.values_list('email', flat=True))

    # Paginate students (20 per page)
    paginator = Paginator(grades, settings.PER_PAGE)
    page = request.GET.get("page", 1)

    try:
        students_page = paginator.page(page)
    except PageNotAnInteger:
        students_page = paginator.page(1)
    except EmptyPage:
        students_page = paginator.page(paginator.num_pages)

    context = {
        "grades": students_page,
        "search_query": search_query,
        "cohort_query": cohort_query,
    }

    return render(request, "app/console.html", context)
