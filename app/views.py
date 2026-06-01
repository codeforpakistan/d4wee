from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from functools import wraps
from .models import (
    Student, Course, Cohort, Registration, Enrollment,
    Assignment, Submission, Attendance, Certificate
)


# Custom decorator for staff-only views
def staff_required(view_func):
    """Decorator that requires user to be staff"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You must be staff to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


def dashboard(request):
    """Main dashboard view - public home or authenticated dashboard"""
    # Show public home page for unauthenticated users
    if not request.user.is_authenticated:
        # Get open cohorts for public display
        open_cohorts = Cohort.objects.filter(
            is_open_for_registration=True
        ).order_by('-start_date')
        
        return render(request, 'app/public_home.html', {
            'open_cohorts': open_cohorts,
        })
    
    # Staff members go to cohorts page as their home
    if request.user.is_staff or request.user.is_superuser:
        return redirect('cohorts')
    
    # Regular users see unified dashboard
    from django.db.models import Prefetch
    
    # Get or create student profile for logged-in user
    try:
        student = Student.objects.prefetch_related(
            Prefetch(
                'enrollments',
                queryset=Enrollment.objects.select_related(
                    'course', 'cohort', 'registration'
                ).prefetch_related(
                    'course__assignments',
                    'submissions__assignment',
                    Prefetch(
                        'registration__certificates',
                        queryset=Certificate.objects.select_related('course')
                    )
                ).order_by('course__name')
            ),
            Prefetch(
                'registrations',
                queryset=Registration.objects.select_related('cohort').prefetch_related(
                    Prefetch(
                        'certificates',
                        queryset=Certificate.objects.select_related('course')
                    )
                ).order_by('-cohort__start_date')
            )
        ).get(user=request.user)
    except Student.DoesNotExist:
        # Try to find existing student by email (from Google Classroom sync or admin creation)
        try:
            student = Student.objects.prefetch_related(
                Prefetch(
                    'enrollments',
                    queryset=Enrollment.objects.select_related(
                        'course', 'cohort', 'registration'
                    ).prefetch_related(
                        'course__assignments',
                        'submissions__assignment',
                        Prefetch(
                            'registration__certificates',
                            queryset=Certificate.objects.select_related('course')
                        )
                    ).order_by('course__name')
                ),
                Prefetch(
                    'registrations',
                    queryset=Registration.objects.select_related('cohort').prefetch_related(
                        Prefetch(
                            'certificates',
                            queryset=Certificate.objects.select_related('course')
                        )
                    ).order_by('-cohort__start_date')
                )
            ).get(email=request.user.email)
            # Link this existing student to the user account
            student.user = request.user
            student.save()
        except Student.DoesNotExist:
            # No student profile - show available cohorts for registration
            # Student profile will be auto-created when they register for a cohort
            open_cohorts = Cohort.objects.filter(
                is_open_for_registration=True
            ).order_by('-start_date')
            
            # Build cohort data with registration status
            available_cohorts_data = []
            for cohort in open_cohorts:
                available_cohorts_data.append({
                    'cohort': cohort,
                    'can_register': cohort.can_accept_registrations,
                    'current_count': cohort.total_enrolled_students,
                })
            
            return render(request, 'app/registration_home.html', {
                'user': request.user,
                'available_cohorts_data': available_cohorts_data,
            })
    
    # Get approved and pending registrations
    approved_registrations = Registration.objects.filter(
        student=student,
        status='APPROVED'
    ).select_related('cohort').order_by('-created_at')
    
    pending_registrations = Registration.objects.filter(
        student=student,
        status='PENDING'
    ).select_related('cohort').order_by('-created_at')
    
    # Get enrolled course IDs
    enrolled_course_ids = Enrollment.objects.filter(
        student=student
    ).values_list('course_id', flat=True)
    
    # Get available courses (flat list, no cohort grouping)
    available_courses = []
    primary_cohort = None
    if approved_registrations.exists():
        # Use the first approved registration's cohort for enrollment
        primary_cohort = approved_registrations.first().cohort
        
        # Show ALL visible courses, not just ones with existing enrollments
        available_courses = Course.objects.filter(
            is_visible=True,
            course_state='ACTIVE'
        ).exclude(
            id__in=enrolled_course_ids  # Exclude already enrolled courses
        ).prefetch_related('assignments').order_by('name')
    
    # Get cohorts available for registration
    open_cohorts = Cohort.objects.filter(
        is_open_for_registration=True
    ).order_by('-start_date')
    
    # Get student's existing registrations
    existing_registration_cohort_ids = Registration.objects.filter(
        student=student
    ).values_list('cohort_id', flat=True)
    
    # Build available cohorts data
    available_cohorts_data = []
    for cohort in open_cohorts:
        is_registered = cohort.id in existing_registration_cohort_ids
        registration = None
        if is_registered:
            registration = Registration.objects.filter(
                student=student,
                cohort=cohort
            ).first()
        
        available_cohorts_data.append({
            'cohort': cohort,
            'is_registered': is_registered,
            'registration': registration,
            'can_register': cohort.can_accept_registrations and not is_registered,
            'current_count': cohort.total_enrolled_students,
        })
    
    # Check if student can mark attendance this week
    from datetime import date
    today = date.today()
    
    # Get active cohorts where student can mark attendance
    can_mark_attendance = Registration.objects.filter(
        student=student,
        status='APPROVED'
    ).exists()
    
    # Check if already marked for today and get hours
    today_attendance = Attendance.objects.filter(
        student=student,
        date=today
    ).first()
    
    marked_today = today_attendance is not None
    hours_today = today_attendance.hours_spent if today_attendance else 0
    
    context = {
        'student': student,
        'student_name': student.full_name,
        'student_email': student.email,
        'enrollments': student.enrollments.filter(course__is_visible=True, cohort__status='ACTIVE'),
        'total_enrollments': student.enrollment_count,
        'avg_completion': student.average_completion_rate,
        'avg_assignment': student.average_score,
        'avg_improvement': student.average_improvement,
        'has_improvement': student.has_improvement_data,
        'avg_on_time': student.average_on_time_rate,
        'available_courses': available_courses,
        'primary_cohort': primary_cohort,
        'has_pending_registration': pending_registrations.exists(),
        'available_cohorts_data': available_cohorts_data,
        'can_mark_attendance': can_mark_attendance,
        'marked_today': marked_today,
        'hours_today': hours_today,
        'attendance_rate': student.attendance_rate,
    }
    return render(request, 'app/dashboard.html', context)


@staff_required
def courses(request):
    """Courses list view - requires authentication"""
    from django.db.models import Count
    
    # Get all visible courses with aggregated counts
    courses = Course.objects.filter(is_visible=True).annotate(
        total_students=Count('enrollments__student', distinct=True),
        total_assignments=Count('assignments', distinct=True)
    ).order_by('name')
    
    context = {
        'courses': courses,
    }
    return render(request, 'app/courses.html', context)


@staff_required
def students_list(request):
    """List all students with their progress across all courses - requires staff access"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Count, Q
    
    # Get search query
    search_query = request.GET.get('q', '').strip()
    
    # Get students with annotated enrollment count (visible courses, active cohorts only)
    students = Student.objects.filter(
        enrollments__isnull=False,
        enrollments__course__is_visible=True,
        enrollments__cohort__status='ACTIVE'
    ).annotate(
        total_enrollments=Count('enrollments', distinct=True, filter=Q(
            enrollments__course__is_visible=True,
            enrollments__cohort__status='ACTIVE'
        ))
    ).distinct()
    
    # Apply search filter if query provided
    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    students = students.order_by('full_name')
    
    # Paginate students (20 per page)
    paginator = Paginator(students, 20)
    page = request.GET.get('page', 1)
    
    try:
        students_page = paginator.page(page)
    except PageNotAnInteger:
        students_page = paginator.page(1)
    except EmptyPage:
        students_page = paginator.page(paginator.num_pages)
    
    context = {
        'students': students_page,
        'total_students': students.count(),
        'search_query': search_query,
    }
    return render(request, 'app/students_list.html', context)


@staff_required
def course_detail(request, course_id):
    """Detailed view of a single course - requires staff access"""
    from django.db.models import Prefetch, Q
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    course = get_object_or_404(Course, id=course_id)
    
    # Get search query
    search_query = request.GET.get('q', '').strip()
    
    # Prefetch assignments for this course
    course_assignments = Assignment.objects.filter(course=course)
    
    # Get all enrollments for this course with comprehensive prefetching
    enrollments = Enrollment.objects.filter(
        course=course
    ).select_related(
        'student'
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
            Q(student__full_name__icontains=search_query) |
            Q(student__email__icontains=search_query)
        )
    
    enrollments = enrollments.order_by('student__full_name')
    
    # Calculate metrics for each student
    students_with_metrics = []
    for enrollment in enrollments:
        students_with_metrics.append({
            'student': enrollment.student,
            'completion_rate': enrollment.completion_rate,
            'average_score': enrollment.overall_average_score,
            'on_time_rate': enrollment.on_time_rate,
            'late_submissions': enrollment.late_assignments_count,
            'missing_submissions': enrollment.missing_assignments_count,
        })
    
    # Paginate students (20 per page)
    paginator = Paginator(students_with_metrics, 20)
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


@staff_required
def student_detail(request, google_id):
    """Detailed view of a student across all their course enrollments - requires staff access"""
    from django.db.models import Prefetch
    from .models import Attendance
    
    # Get student with comprehensive prefetching
    student = get_object_or_404(
        Student.objects.prefetch_related(
            Prefetch(
                'enrollments',
                queryset=Enrollment.objects.select_related(
                    'course', 'cohort', 'registration'
                ).prefetch_related(
                    Prefetch(
                        'submissions',
                        queryset=Submission.objects.select_related('assignment')
                    ),
                    Prefetch(
                        'course__assignments',
                        queryset=Assignment.objects.all()
                    ),
                    Prefetch(
                        'registration__certificates',
                        queryset=Certificate.objects.select_related('course')
                    )
                ).order_by('course__name')
            ),
            Prefetch(
                'registrations',
                queryset=Registration.objects.select_related('cohort').prefetch_related(
                    Prefetch(
                        'enrollments',
                        queryset=Enrollment.objects.select_related('course').prefetch_related(
                            Prefetch(
                                'submissions',
                                queryset=Submission.objects.select_related('assignment')
                            ),
                            'course__assignments'
                        )
                    ),
                    Prefetch(
                        'certificates',
                        queryset=Certificate.objects.select_related('course')
                    )
                ).order_by('-cohort__start_date')
            ),
            Prefetch(
                'attendance',
                queryset=Attendance.objects.all().order_by('date')
            )
        ),
        google_id=google_id
    )
    
    context = {
        'student': student,
        'student_name': student.full_name,
        'student_email': student.email,
        'enrollments': student.enrollments.filter(course__is_visible=True, cohort__status='ACTIVE'),
        'registrations': student.registrations.all(),
        'total_enrollments': student.enrollment_count,
        'avg_completion': student.average_completion_rate,
        'avg_score': student.average_score,
        'avg_improvement': student.average_improvement,
        'has_improvement': student.has_improvement_data,
        'avg_on_time': student.average_on_time_rate,
        'attendance_rate': student.attendance_rate,
        'attendance_records': student.attendance.filter(cohort__status='ACTIVE').order_by('date'),
        'total_hours': student.total_attendance_hours,
        'total_weeks': student.total_attendance_weeks,
    }
    return render(request, 'app/student_detail.html', context)


@login_required
@login_required
def profile(request):
    """Student profile view - shows logged-in student's data and available courses"""
    from django.db.models import Prefetch
    
    # Get or create student profile for logged-in user
    try:
        student = Student.objects.prefetch_related(
            Prefetch(
                'enrollments',
                queryset=Enrollment.objects.select_related(
                    'course', 'cohort'
                ).prefetch_related(
                    'course__assignments',
                    'submissions__assignment'
                ).order_by('course__name')
            ),
            Prefetch(
                'registrations',
                queryset=Registration.objects.select_related('cohort').order_by('-cohort__start_date')
            )
        ).get(user=request.user)
    except Student.DoesNotExist:
        # No student profile - redirect to home (which shows registration options)
        messages.info(request, 'Please register for a cohort to access your profile.')
        return redirect('home')
    
    # Get approved/active registrations for available courses
    registrations = Registration.objects.filter(
        student=student,
        status='APPROVED'
    ).select_related('cohort').order_by('-created_at')
    
    # Get enrolled course IDs
    enrolled_course_ids = Enrollment.objects.filter(
        student=student
    ).values_list('course_id', flat=True)
    
    # Build available courses data
    cohorts_data = []
    for registration in registrations:
        cohort = registration.cohort
        
        # Get unique courses for this cohort
        course_ids = Enrollment.objects.filter(
            cohort=cohort
        ).values_list('course_id', flat=True).distinct()
        
        courses = Course.objects.filter(
            id__in=course_ids,
            is_visible=True
        ).prefetch_related('assignments')
        
        courses_data = []
        for course in courses:
            courses_data.append({
                'course': course,
                'cohort': cohort,
                'is_enrolled': course.id in enrolled_course_ids,
            })
        
        if courses_data:  # Only add cohort if it has courses
            cohorts_data.append({
                'registration': registration,
                'cohort': cohort,
                'courses': courses_data,
            })
    
    context = {
        'student': student,
        'student_name': student.full_name,
        'student_email': student.email,
        'enrollments': student.enrollments.all(),
        'total_enrollments': student.enrollment_count,
        'avg_completion': student.average_completion_rate,
        'avg_assignment': student.average_score,
        'avg_improvement': student.average_improvement,
        'has_improvement': student.has_improvement_data,
        'avg_on_time': student.average_on_time_rate,
        'cohorts_data': cohorts_data,
        'is_profile': True,
    }
    return render(request, 'app/profile.html', context)


@staff_required
def cohorts(request):
    """Display cohort statistics - requires staff access"""
    from django.db.models import Count, Q
    
    # Get all cohorts with aggregated counts (count unique students, not registrations)
    cohorts = Cohort.objects.annotate(
        active_registrations=Count('registrations__student', filter=Q(registrations__status='APPROVED'), distinct=True),
        total_registrations=Count('registrations__student', distinct=True),
        total_certificates=Count('registrations__certificates', distinct=True),
        courses_count=Count('registrations__enrollments__course', distinct=True)
    ).order_by('start_date')
    
    context = {
        'cohorts': cohorts,
    }
    return render(request, 'app/cohorts.html', context)


@staff_required
def cohort_detail(request, cohort_id):
    """Detailed view of a single cohort - requires staff access"""
    from django.db.models import Prefetch
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Get registrations for this cohort with optimized counts
    registrations = Registration.objects.filter(cohort=cohort).select_related('student')
    total_registrations = registrations.count()
    
    # Count by status
    pending = registrations.filter(status='PENDING').count()
    approved = registrations.filter(status='APPROVED').count()
    rejected = registrations.filter(status='REJECTED').count()
    
    # Get all enrollments for this cohort with prefetching
    enrollments = Enrollment.objects.filter(cohort=cohort).select_related(
        'course', 'student'
    ).prefetch_related(
        'course__assignments',
        'submissions'
    )
    
    # Count total enrolled students
    total_enrollments = approved
    
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
    
    # Calculate overall average completion rate
    if completion_rates:
        completion_rate = sum(completion_rates) / len(completion_rates)
    else:
        completion_rate = 0
    
    # Get certificates
    certificates = Certificate.objects.filter(registration__cohort=cohort).count()
    
    context = {
        'cohort': cohort,
        'courses': courses,
        'total_courses': len(courses),
        'total_registrations': total_registrations,
        'total_enrollments': total_enrollments,  # Template expects this
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'completion_rate': completion_rate,  # Template expects this (not avg_completion)
        'certificates_issued': certificates,
    }
    return render(request, 'app/cohort_detail.html', context)


@staff_required
def attendance(request):
    """Display student attendance by week - requires staff access"""
    from collections import defaultdict
    from .models import Cohort
    
    # Get filter parameters
    selected_cohort = request.GET.get('cohort', None)
    selected_week = request.GET.get('week', None)
    if selected_week:
        selected_week = int(selected_week)
    
    # Base queryset
    attendance_records = Attendance.objects.all()
    
    # Apply cohort filter
    if selected_cohort:
        attendance_records = attendance_records.filter(cohort_id=selected_cohort)
    
    # Group attendance by week
    weeks_data = defaultdict(lambda: {
        'week_number': 0,
        'present_count': 0,
        'total_count': 0,
        'start_date': None,
        'end_date': None,
        'unique_students': set(),
        'present_students': set(),
        'dates': [],
    })
    
    # Process all attendance records - each record represents a present student
    for record in attendance_records.select_related('cohort', 'student').order_by('date'):
        week = record.week_number  # Calculated property from date
        
        # Apply week filter in Python (since week_number is a property)
        if selected_week and week != selected_week:
            continue
        
        weeks_data[week]['week_number'] = week
        weeks_data[week]['unique_students'].add(record.student.email)
        weeks_data[week]['present_students'].add(record.student.email)
        weeks_data[week]['dates'].append(record.date)
    
    # Calculate attendance rate and date ranges for each week
    for week, data in weeks_data.items():
        # Count unique students who were present
        data['total_count'] = len(data['unique_students'])
        data['present_count'] = len(data['present_students'])
        
        # Calculate week date range from actual attendance record dates
        if data['dates']:
            data['start_date'] = min(data['dates'])
            data['end_date'] = max(data['dates'])
        
        # Remove sets and dates list from data (not JSON serializable)
        del data['unique_students']
        del data['present_students']
        del data['dates']
    
    # Convert to sorted list
    weeks_list = sorted(weeks_data.values(), key=lambda x: x['week_number'])
    
    # Calculate overall statistics - count unique students across ALL records (not just filtered)
    all_unique_students = set(Attendance.objects.select_related('student').values_list('student__email', flat=True))
    total_enrolled_students = len(all_unique_students)
    
    # For filtered view, count unique students in filtered records
    present_students = set(attendance_records.values_list('student__email', flat=True))
    total_present = len(present_students)
    
    overall_attendance_rate = round((total_present / total_enrolled_students * 100), 1) if total_enrolled_students > 0 else 0
    
    # Recalculate attendance rate for each week based on total enrolled students
    for data in weeks_list:
        if total_enrolled_students > 0:
            data['attendance_rate'] = round((data['present_count'] / total_enrolled_students) * 100, 1)
        else:
            data['attendance_rate'] = 0
    
    # Get unique weeks and cohorts for filters (from all records, not filtered)
    # Calculate available weeks from dates since week_number is a property
    all_records = Attendance.objects.all()
    available_weeks = sorted(set(record.week_number for record in all_records))
    cohorts = Cohort.objects.all()
    
    context = {
        'weeks_data': weeks_list,
        'total_enrolled_students': total_enrolled_students,  # Total students across all weeks
        'total_present': total_present,
        'overall_attendance_rate': overall_attendance_rate,
        'available_weeks': available_weeks,
        'cohorts': cohorts,
        'selected_cohort': int(selected_cohort) if selected_cohort else None,
        'selected_week': int(selected_week) if selected_week else None,
    }
    return render(request, 'app/attendance.html', context)


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
        'issue_categories': issue_categories,
        'total_issues': sum(cat['count'] for cat in issue_categories),
    }
    return render(request, 'app/issues.html', context)


@login_required
def register_for_cohort(request, cohort_id):
    """Handle cohort registration request - for non-staff users"""
    # Staff users should use admin interface
    if request.user.is_staff or request.user.is_superuser:
        messages.error(request, 'Staff members should use the admin interface.')
        return redirect('cohorts')
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Get or create student profile when registering for cohort
    try:
        # First try to get by user
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        # Try to find existing student by email (from Google Classroom sync)
        try:
            student = Student.objects.get(email=request.user.email)
            # Link this existing student to the user account
            student.user = request.user
            student.save()
        except Student.DoesNotExist:
            # Create new student profile
            student = Student.objects.create(
                user=request.user,
                email=request.user.email,
                full_name=request.user.get_full_name() or request.user.username,
                google_id=f"local_{request.user.id}"
            )
    
    # Check if cohort is open for registration
    if not cohort.is_open_for_registration:
        messages.error(request, f'{cohort.name} is not currently open for registration.')
        return redirect('home')
    
    # Check if cohort can accept registrations
    if not cohort.can_accept_registrations:
        messages.error(request, f'{cohort.name} has reached its maximum capacity.')
        return redirect('home')
    
    # Check if already registered
    existing = Registration.objects.filter(student=student, cohort=cohort).first()
    if existing:
        messages.warning(request, f'You already have a {existing.status.lower()} registration for {cohort.name}.')
        return redirect('home')
    
    # Create registration request
    Registration.objects.create(
        student=student,
        cohort=cohort,
        status='PENDING',
        notes=f"Self-registration via web interface by {request.user.username}"
    )
    
    messages.success(request, 
        f'Your registration request for {cohort.name} has been submitted! '
        f'An administrator will review it shortly.')
    
    return redirect('home')


@login_required
def enroll_in_course(request, course_id):
    """Enroll student in a course within their cohort"""
    if request.method != 'POST':
        return redirect('home')
    
    # Get cohort_id from POST data
    cohort_id = request.POST.get('cohort_id')
    if not cohort_id:
        messages.error(request, 'Cohort information missing.')
        return redirect('home')
    
    # Get student
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    # Get course and cohort
    course = get_object_or_404(Course, id=course_id)
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Verify student has approved registration for this cohort
    registration = Registration.objects.filter(
        student=student,
        cohort=cohort,
        status='APPROVED'
    ).first()
    
    if not registration:
        messages.error(request, f'You are not registered for the {cohort.name} cohort.')
        return redirect('home')
    
    # Check if already enrolled
    existing = Enrollment.objects.filter(
        student=student,
        course=course
    ).first()
    
    if existing:
        messages.warning(request, f'You are already enrolled in {course.name}.')
        return redirect('home')
    
    # Check enrollment limit (max 5 courses)
    current_enrollment_count = Enrollment.objects.filter(student=student).count()
    if current_enrollment_count >= 5:
        messages.error(request, 'You cannot enroll in more than 5 courses at a time.')
        return redirect('home')
    
    # Create enrollment
    Enrollment.objects.create(
        student=student,
        course=course,
        cohort=cohort,
        registration=registration,
        status='IN_PROGRESS'
    )
    
    messages.success(request, f'Successfully enrolled in {course.name}!')
    return redirect('home')


@login_required
def unenroll_from_course(request, enrollment_id):
    """Allow student to unenroll from a course"""
    if request.method != 'POST':
        return redirect('home')
    
    # Get student
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    # Get enrollment and verify it belongs to this student
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=student)
    
    course_name = enrollment.course.name
    
    # Delete the enrollment
    enrollment.delete()
    
    messages.success(request, f'Successfully unenrolled from {course_name}.')
    return redirect('home')


@login_required
def mark_attendance(request):
    """Allow students to mark their attendance for the current week"""
    from datetime import date
    
    # Get student
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    # Get student's active registration (should only be one)
    active_registration = Registration.objects.filter(
        student=student,
        status='APPROVED'
    ).select_related('cohort').first()
    
    if not active_registration:
        messages.error(request, 'You need an active cohort registration to mark attendance.')
        return redirect('home')
    
    cohort = active_registration.cohort
    today = date.today()
    week_number = today.isocalendar()[1]
    
    # Check if already marked for today
    existing_attendance = Attendance.objects.filter(
        student=student,
        cohort=cohort,
        date=today
    ).first()
    
    if request.method == 'POST':
        hours_spent = request.POST.get('hours_spent')
        
        if existing_attendance:
            # Update existing record
            existing_attendance.hours_spent = float(hours_spent) if hours_spent else 0
            existing_attendance.save()
            messages.success(request, f'Updated attendance for {cohort.name} - Week {week_number}!')
        else:
            # Create new attendance record
            Attendance.objects.create(
                student=student,
                cohort=cohort,
                date=today,
                hours_spent=float(hours_spent) if hours_spent else 0
            )
            messages.success(request, f'Attendance marked for {cohort.name} - Week {week_number}!')
        
        return redirect('home')
    
    # GET request - show form
    context = {
        'student': student,
        'cohort': cohort,
        'today': today,
        'week_number': week_number,
        'existing_attendance': existing_attendance,
    }
    return render(request, 'app/mark_attendance.html', context)


@login_required
def my_certificates(request):
    """Display certificates for the logged-in student"""
    # Get student
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('home')
    
    # Get all enrollments with certificate info
    from django.db.models import Prefetch
    
    enrollments = Enrollment.objects.filter(
        student=student
    ).select_related(
        'course', 'cohort', 'registration'
    ).prefetch_related(
        Prefetch(
            'registration__certificates',
            queryset=Certificate.objects.select_related('course').order_by('-issued_date')
        )
    ).order_by('-cohort__start_date', 'course__name')
    
    # Build data structure with certificates and eligibility info
    certificates_data = []
    for enrollment in enrollments:
        # Get certificate for this specific course
        course_cert = enrollment.registration.certificates.filter(
            certificate_type='COURSE',
            course=enrollment.course
        ).first()
        
        certificates_data.append({
            'enrollment': enrollment,
            'course': enrollment.course,
            'cohort': enrollment.cohort,
            'is_eligible': enrollment.certificate_eligible,
            'eligibility_notes': enrollment.certificate_eligibility_notes,
            'certificate': course_cert,
            'completion_rate': enrollment.completion_rate,
            'average_score': enrollment.overall_average_score,
        })
    
    context = {
        'student': student,
        'certificates_data': certificates_data,
    }
    return render(request, 'app/my_certificates.html', context)


@staff_required
def issue_certificate(request, enrollment_id):
    """Issue a certificate for an enrollment"""
    from datetime import date
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('home')
    
    # Get the enrollment
    enrollment = get_object_or_404(
        Enrollment.objects.select_related('student', 'course', 'registration'),
        id=enrollment_id
    )
    
    # Check eligibility
    if not enrollment.certificate_eligible:
        messages.error(request, f'Student is not eligible for certificate for {enrollment.course.name}. {enrollment.certificate_eligibility_notes}')
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
    # Check if certificate already exists
    existing_cert = Certificate.objects.filter(
        registration=enrollment.registration,
        certificate_type='COURSE',
        course=enrollment.course
    ).first()
    
    if existing_cert:
        messages.warning(request, f'Certificate already issued for {enrollment.student.full_name} - {enrollment.course.name}')
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
    # Create certificate
    try:
        from .services import generate_certificate
        
        cert = Certificate.objects.create(
            registration=enrollment.registration,
            certificate_type='COURSE',
            course=enrollment.course,
            issued_date=date.today(),
            completion_percentage=enrollment.completion_rate or 0,
            average_grade=enrollment.overall_average_score,
            notes=f"Issued by {request.user.username}"
        )
        
        # Generate and save certificate file
        certificate_file = generate_certificate(cert)
        cert.certificate_file.save(certificate_file.name, certificate_file, save=True)
        
        messages.success(request, f'Certificate issued for {enrollment.student.full_name} - {enrollment.course.name}')
    except Exception as e:
        messages.error(request, f'Error issuing certificate: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@staff_required
def delete_certificate(request, certificate_id):
    """Delete a certificate record (staff only)"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('home')
    
    # Get the certificate
    certificate = get_object_or_404(Certificate, id=certificate_id)
    
    student_name = certificate.registration.student.full_name
    course_name = certificate.course.name if certificate.course else 'Cohort'
    
    try:
        # Delete the file if it exists
        if certificate.certificate_file:
            certificate.certificate_file.delete(save=False)
        
        # Delete the certificate record
        certificate.delete()
        
        messages.success(request, f'Certificate deleted for {student_name} - {course_name}')
    except Exception as e:
        messages.error(request, f'Error deleting certificate: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def test_certificate(request):
    """Test view to preview certificate template"""
    from datetime import datetime
    
    context = {
        'name': 'Jane Doe',
        'course': 'Digital Marketing Fundamentals',
        'period': 'January 2026 - May 2026',
    }
    
    return render(request, 'certificate/certificate.html', context)


def view_certificate(request, student_google_id, course_google_id):
    """View a student's certificate for a specific course or cohort"""
    from django.shortcuts import get_object_or_404
    
    # Get the student
    student = get_object_or_404(Student, google_id=student_google_id)
    
    # Determine if this is a course or cohort certificate
    if course_google_id == 'cohort':
        # Find cohort certificate - get the most recent registration for this student
        registration = student.registrations.filter(certificates__isnull=False).order_by('-created_at').first()
        if not registration:
            messages.error(request, 'Certificate not found')
            return redirect('home')
        
        certificate = registration.certificates.filter(certificate_type='COHORT').first()
        if not certificate:
            messages.error(request, 'Certificate not found')
            return redirect('home')
        
        course_name = certificate.registration.cohort.name
    else:
        # Find course certificate
        course = get_object_or_404(Course, google_id=course_google_id)
        
        # Find the certificate for this student and course
        certificate = Certificate.objects.filter(
            registration__student=student,
            course=course,
            certificate_type='COURSE'
        ).first()
        
        if not certificate:
            messages.error(request, 'Certificate not found')
            return redirect('home')
        
        course_name = course.name
    
    # Get cohort dates
    cohort = certificate.registration.cohort
    period = f"{cohort.start_date.strftime('%B %Y')} - {cohort.end_date.strftime('%B %Y')}"
    
    context = {
        'name': student.full_name,
        'course': course_name,
        'period': period,
    }
    
    return render(request, 'certificate/certificate.html', context)


# =============================================================================
# STAFF VIEWS FOR REGISTRATIONS
# =============================================================================

@staff_required
def registrations_list(request):
    """
    Staff view to see and manage all registrations
    """
    # Get filter from query params
    status_filter = request.GET.get('status', 'PENDING')
    page_number = request.GET.get('page', 1)
    
    # Only show registrations for active cohorts
    registrations = Registration.objects.select_related(
        'student', 'cohort', 'approved_by'
    ).filter(cohort__status='ACTIVE')
    
    if status_filter and status_filter != 'ALL':
        registrations = registrations.filter(status=status_filter)
    
    registrations = registrations.order_by('-requested_date')
    
    # Paginate results (25 per page)
    paginator = Paginator(registrations, 25)
    page_obj = paginator.get_page(page_number)
    
    # Count by status for tabs (only for active cohorts)
    pending_count = Registration.objects.filter(status='PENDING', cohort__status='ACTIVE').count()
    approved_count = Registration.objects.filter(status='APPROVED', cohort__status='ACTIVE').count()
    rejected_count = Registration.objects.filter(status='REJECTED', cohort__status='ACTIVE').count()
    
    context = {
        'registrations': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    
    return render(request, 'app/registrations_list.html', context)


@staff_required
@require_POST
def approve_registration(request, registration_id):
    """
    Approve a registration (POST only)
    """
    registration = get_object_or_404(Registration, id=registration_id)
    
    if registration.status != 'PENDING':
        messages.warning(request, f'Registration is already {registration.status.lower()}.')
    else:
        registration.approve(request.user)
        messages.success(request, f'Approved registration for {registration.student.full_name}.')
    
    # Redirect back to registrations list
    return redirect('registrations_list')


@staff_required
@require_POST
def reject_registration(request, registration_id):
    """
    Reject a registration (POST only)
    """
    registration = get_object_or_404(Registration, id=registration_id)
    
    if registration.status != 'PENDING':
        messages.warning(request, f'Registration is already {registration.status.lower()}.')
    else:
        reason = request.POST.get('reason', '')
        registration.reject(request.user, reason=reason)
        messages.success(request, f'Rejected registration for {registration.student.full_name}.')
    
    # Redirect back to registrations list
    return redirect('registrations_list')

