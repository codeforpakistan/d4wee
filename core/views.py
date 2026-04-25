from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Course, Student, Assignment, Submission, StudentMetrics


def index(request):
    """Setup page for initial OAuth login - admin only"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/index.html')


def dashboard(request):
    """Main dashboard view - public access"""
    from django.db.models import Count, Q
    
    # Only show courses with enrolled students
    courses = Course.objects.annotate(
        student_count=Count('students')
    ).filter(
        student_count__gt=0
    ).prefetch_related('students', 'assignments', 'student_metrics').order_by('name')
    
    # Calculate ungraded assignments for each course
    for course in courses:
        # Count assignments with turned-in submissions that have no grades
        ungraded_count = 0
        assignments = Assignment.objects.filter(
            course=course,
            max_points__isnull=False,
            max_points__gt=0
        )
        
        for assignment in assignments:
            has_ungraded = Submission.objects.filter(
                assignment=assignment,
                state='TURNED_IN',
                assigned_grade__isnull=True
            ).exists()
            
            if has_ungraded:
                ungraded_count += 1
        
        course.ungraded_count = ungraded_count
    
    context = {
        'courses': courses,
    }
    return render(request, 'core/dashboard.html', context)


def students_list(request):
    """List all students with their progress across all courses - public access"""
    from collections import defaultdict
    
    # Get all courses
    courses = Course.objects.filter(students__isnull=False).distinct().order_by('name')
    
    # Get all unique students grouped by google_id
    student_data = defaultdict(lambda: {'name': '', 'enrollments': {}})
    
    # Get all student metrics with related data
    all_metrics = StudentMetrics.objects.select_related('student', 'course').all()
    
    for metric in all_metrics:
        google_id = metric.student.google_id
        student_data[google_id]['name'] = metric.student.full_name
        student_data[google_id]['google_id'] = google_id
        student_data[google_id]['enrollments'][metric.course.id] = metric
    
    # Convert to sorted list by student name
    students = sorted(student_data.values(), key=lambda x: x['name'])
    
    context = {
        'students': students,
        'courses': courses,
    }
    return render(request, 'core/students_list.html', context)


@login_required
def sync_classroom_data(request):
    """Trigger manual sync of Google Classroom data"""
    if request.method == 'POST':
        # Import here to avoid circular imports
        from .services import sync_all_classroom_data
        import traceback
        
        try:
            print(f"\n{'='*60}")
            print(f"Starting sync for user: {request.user.email}")
            print(f"{'='*60}\n")
            
            sync_log = sync_all_classroom_data(request.user)
            
            print(f"\n{'='*60}")
            print(f"Sync completed!")
            print(f"Courses: {sync_log.courses_synced}")
            print(f"Students: {sync_log.students_synced}")
            print(f"Assignments: {sync_log.assignments_synced}")
            print(f"Submissions: {sync_log.submissions_synced}")
            print(f"{'='*60}\n")
            
            messages.success(request, 
                f'Successfully synced {sync_log.courses_synced} courses, '
                f'{sync_log.students_synced} students, '
                f'{sync_log.assignments_synced} assignments, '
                f'{sync_log.submissions_synced} submissions!')
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"ERROR during sync:")
            print(f"{str(e)}")
            print(f"\nFull traceback:")
            traceback.print_exc()
            print(f"{'='*60}\n")
            messages.error(request, f'Error syncing data: {str(e)}')
    
    return redirect('dashboard')


def course_detail(request, course_id):
    """Detailed view of a single course - public access"""
    from django.db.models import Count, Q
    
    course = get_object_or_404(Course, id=course_id)
    
    # Get all students with their metrics, sorted by name
    students_with_metrics = StudentMetrics.objects.filter(
        course=course
    ).select_related('student').order_by('student__full_name')
    
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
            assignment.submission_count = ungraded_count
            ungraded_assignments.append(assignment)
    
    # Calculate course stats
    total_students = course.students.count()
    total_assignments = Assignment.objects.filter(course=course).count()
    
    context = {
        'course': course,
        'students_with_metrics': students_with_metrics,
        'ungraded_assignments': ungraded_assignments,
        'total_students': total_students,
        'total_assignments': total_assignments,
    }
    return render(request, 'core/course_detail.html', context)


def student_detail(request, google_id):
    """Detailed view of a student across all their course enrollments - public access"""
    # Get all enrollments for this student
    enrollments = Student.objects.filter(google_id=google_id).select_related('course')
    
    if not enrollments.exists():
        messages.error(request, 'Student not found.')
        return redirect('dashboard')
    
    # Get student info from first enrollment
    first_enrollment = enrollments.first()
    student_name = first_enrollment.full_name
    student_email = first_enrollment.email
    
    # Build enrollment data with metrics
    enrollment_data = []
    for enrollment in enrollments:
        try:
            metrics = StudentMetrics.objects.get(student=enrollment)
            enrollment_data.append({
                'course': enrollment.course,
                'metrics': metrics,
                'assignment_count': Assignment.objects.filter(course=enrollment.course).count(),
            })
        except StudentMetrics.DoesNotExist:
            # Skip if no metrics
            continue
    
    # Sort enrollment data by course name
    enrollment_data.sort(key=lambda x: x['course'].name)
    
    # Calculate overall stats
    total_enrollments = len(enrollment_data)
    
    # Calculate average metrics across all courses
    if enrollment_data:
        avg_completion = sum(e['metrics'].completion_rate for e in enrollment_data) / total_enrollments
        avg_score = sum(e['metrics'].average_score for e in enrollment_data if e['metrics'].average_score is not None) / max(1, sum(1 for e in enrollment_data if e['metrics'].average_score is not None))
        avg_on_time = sum(e['metrics'].on_time_rate for e in enrollment_data) / total_enrollments
    else:
        avg_completion = avg_score = avg_on_time = 0
    
    context = {
        'google_id': google_id,
        'student_name': student_name,
        'student_email': student_email,
        'enrollments': enrollment_data,
        'total_enrollments': total_enrollments,
        'avg_completion': avg_completion,
        'avg_score': avg_score,
        'avg_on_time': avg_on_time,
    }
    return render(request, 'core/student_detail.html', context)


@login_required
def debug_auth(request):
    """Debug endpoint to check OAuth status"""
    from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
    
    debug_info = {
        'user': str(request.user),
        'user_email': request.user.email,
        'is_authenticated': request.user.is_authenticated,
    }
    
    # Check SocialAccount
    try:
        social_account = SocialAccount.objects.get(user=request.user, provider='google')
        debug_info['social_account'] = {
            'provider': social_account.provider,
            'uid': social_account.uid,
            'extra_data': social_account.extra_data,
        }
    except SocialAccount.DoesNotExist:
        debug_info['social_account'] = 'Not found'
    
    # Check SocialToken
    try:
        social_token = SocialToken.objects.get(account__user=request.user, account__provider='google')
        debug_info['social_token'] = {
            'token_exists': True,
            'token_length': len(social_token.token) if social_token.token else 0,
            'has_refresh_token': bool(social_token.token_secret),
            'app_id': social_token.app_id if social_token.app else None,
        }
    except SocialToken.DoesNotExist:
        debug_info['social_token'] = 'Not found'
    
    # Check SocialApp
    try:
        social_app = SocialApp.objects.get(provider='google')
        debug_info['social_app'] = {
            'name': social_app.name,
            'client_id': social_app.client_id[:20] + '...',
            'has_secret': bool(social_app.secret),
        }
    except SocialApp.DoesNotExist:
        debug_info['social_app'] = 'Not found'
    
    return JsonResponse(debug_info, json_dumps_params={'indent': 2})
