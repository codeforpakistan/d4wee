from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from app.models import Cohort, Enrollment


@login_required
@staff_member_required
def cohort_list(request):
    """Display cohort statistics - requires staff access"""
    from django.db.models import Count, Q
    
    # Get all cohorts with aggregated counts (count unique students, not registrations)
    cohorts = Cohort.objects.annotate(
        active_registrations=Count('registrations__student', filter=Q(registrations__status='APPROVED'), distinct=True),
        total_registrations=Count('registrations__student', distinct=True),
        total_certificates=Count('registrations__enrollments__certificate', distinct=True),
        courses_count=Count('registrations__enrollments__course', filter=Q(registrations__enrollments__course__is_visible=True), distinct=True)
    ).order_by('start_date')
    
    return render(request, 'app/cohort_list.html', {
        'cohorts': cohorts,
    })

@login_required
@staff_member_required
def cohort_detail(request, cohort_id):
    """Detailed view of a single cohort - requires staff access"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    enrollments = Enrollment.objects.filter(registration__cohort=cohort)

    # Get unique courses students are enrolled in
    courses_data = {}
    completion_rates = []
    
    for enrollment in enrollments:
        course = enrollment.course
        if course.id not in courses_data:
            # Create a simple object to hold course and its stats
            course_info = type('CourseInfo', (), {})()
            course_info.id = course.id
            course_info.name = course.name
            course_info.display_name = course.display_name
            course_info.section = getattr(course, 'section', None)
            course_info.students = type('Students', (), {'count': 0})()
            course_info.assignments = type('Assignments', (), {'count': course.assignments.count()})()
            course_info.avg_completion = 0
            course_info.completions = []
            course_info.ungraded_count = 0  # TODO: Calculate ungraded submissions
            courses_data[course.id] = course_info
        
        courses_data[course.id].students.count += 1
        
        # Calculate completion rate for this enrollment
        completion = enrollment.completion_rate
        if completion is not None:
            courses_data[course.id].completions.append(completion)
            # Add to overall completion rates
            completion_rates.append(completion)
    
    # Calculate averages for courses
    courses = []
    for course_info in courses_data.values():
        if course_info.completions:
            course_info.avg_completion = sum(course_info.completions) / len(course_info.completions)
        courses.append(course_info)
    
    context = {
        'cohort': cohort,
        'courses': courses,
    }
    return render(request, 'app/cohort_detail.html', context)
