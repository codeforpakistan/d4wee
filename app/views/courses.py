from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from app.models import (
    Course, Enrollment, Assignment, Submission
)
from django.conf import settings

@login_required
@staff_member_required
def course_list(request):
    """Courses list view - requires authentication"""
    from django.db.models import Count
    
    # Get all visible courses with aggregated counts
    courses = Course.objects.filter(is_visible=True).annotate(
        total_students=Count('enrollments__registration__student', distinct=True),
        total_assignments=Count('assignments', distinct=True)
    ).order_by('name')
    
    return render(request, 'app/course_list.html', {
        'courses': courses,
    })

@login_required
@staff_member_required
def course_detail(request, google_id):
    """Detailed view of a single course - requires staff access"""
    from django.db.models import Prefetch, Q
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    course = get_object_or_404(Course, google_id=google_id)
    
    # Get search query
    search_query = request.GET.get('q', '').strip()
    
    # Prefetch assignments for this course
    course_assignments = Assignment.objects.filter(course=course)
    
    # Get all enrollments for this course with comprehensive prefetching
    enrollments = Enrollment.objects.filter(
        course=course
    ).select_related(
        'registration__student',
    ).prefetch_related(
        Prefetch(
            'submissions',
            queryset=Submission.objects.select_related('assignment').all()
        ),
        Prefetch(
            'course__assignments',
            queryset=course_assignments
        )
    )
    
    # Apply search filter if query exists
    if search_query:
        enrollments = enrollments.filter(
            Q(registration__student__full_name__icontains=search_query) |
            Q(registration__student__email__icontains=search_query)
        )
    
    enrollments = enrollments.order_by('registration__student__full_name')
    
    # Calculate metrics for each student
    students_with_metrics = []
    for enrollment in enrollments:
        students_with_metrics.append({
            'student': enrollment.registration.student,
            'completion_rate': enrollment.completion_rate,
            'average_score': enrollment.overall_average_score,
            'on_time_rate': enrollment.on_time_rate,
            'late_submissions': enrollment.late_assignments_count,
            'missing_submissions': enrollment.missing_assignments_count,
        })
    
    # Paginate students (20 per page)
    paginator = Paginator(students_with_metrics, settings.PER_PAGE)
    page = request.GET.get('page', 1)
    
    try:
        students_page = paginator.page(page)
    except PageNotAnInteger:
        students_page = paginator.page(1)
    except EmptyPage:
        students_page = paginator.page(paginator.num_pages)
    
    # Get assignments with max_points (gradeable)
    assignments = Assignment.objects.filter(
        course=course,
        max_points__isnull=False,
        max_points__gt=0
    ).order_by('-due_date')
    
    # Find ungraded assignments (have submissions but no grades)
    ungraded_assignments = []
    for assignment in assignments:
        ungraded_count = Submission.objects.filter(
            assignment=assignment,
            state='TURNED_IN',
            assigned_grade__isnull=True
        ).count()
        
        if ungraded_count > 0:
            ungraded_assignments.append({
                'assignment': assignment,
                'count': ungraded_count,
            })
    
    # Calculate course stats
    total_students = enrollments.count()
    total_assignments = Assignment.objects.filter(course=course).count()
    
    context = {
        'course': course,
        'enrollments': enrollments,
        'students_with_metrics': students_page,
        'ungraded_assignments': ungraded_assignments,
        'total_students': total_students,
        'total_assignments': total_assignments,
        'search_query': search_query,
    }
    return render(request, 'app/course_detail.html', context)
