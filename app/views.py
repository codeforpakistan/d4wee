from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
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
    """Main dashboard view - public landing page or user-specific dashboard"""
    context = {
        'registrations': [],
        'has_registrations': False,
        'student': None,
        'is_staff': False,
    }
    
    # If user is authenticated, show personalized content
    if request.user.is_authenticated:
        context['is_staff'] = request.user.is_staff
        
        # Staff members see admin dashboard with stats
        if request.user.is_staff:
            context['total_students'] = Student.objects.count()
            context['total_courses'] = Course.objects.filter(is_visible=True).count()
            context['total_cohorts'] = Cohort.objects.count()
            context['pending_registrations'] = Registration.objects.filter(status='PENDING').count()
            return render(request, 'app/dashboard.html', context)
        
        # Regular users see their student dashboard
        try:
            student = Student.objects.filter(user=request.user).first()
            
            if student:
                context['student'] = student
                
                # Get registrations (including pending ones)
                registrations = Registration.objects.filter(
                    student=student
                ).select_related('cohort').order_by('-requested_date')
                
                if registrations.exists():
                    context['has_registrations'] = True
                    
                    # Build registration data with enrollments
                    registrations_data = []
                    for registration in registrations:
                        # Get enrollments for approved/active registrations
                        enrollments = Enrollment.objects.filter(registration=registration) if registration.status in ['APPROVED', 'ACTIVE', 'COMPLETED'] else []
                        
                        enrollments_data = []
                        for enrollment in enrollments:
                            enrollments_data.append({
                                'course': enrollment.course,
                                'status': enrollment.status,
                                'completion_rate': enrollment.completion_rate,
                                'overall_average': enrollment.overall_average_score,
                                'category': enrollment.category,
                            })
                        
                        registrations_data.append({
                            'registration': registration,
                            'cohort': registration.cohort,
                            'enrollments': enrollments_data,
                            'attendance_rate': registration.session_attendance_rate if registration.status in ['APPROVED', 'ACTIVE', 'COMPLETED'] else 0,
                            'overall_completion': registration.overall_completion_rate if registration.status in ['APPROVED', 'ACTIVE', 'COMPLETED'] else 0,
                        })
                    
                    context['registrations'] = registrations_data
                
        except Exception as e:
            messages.error(request, f'Error loading dashboard: {str(e)}')
    
    return render(request, 'app/dashboard.html', context)


@staff_required
def courses(request):
    """Courses list view - requires authentication"""
    # Get all visible courses
    courses = Course.objects.filter(is_visible=True).order_by('name')
    
    courses_data = []
    for course in courses:
        # Count students enrolled in this course
        enrollments = Enrollment.objects.filter(course=course)
        student_count = enrollments.values('student').distinct().count()
        
        # Calculate average completion rate
        if enrollments.exists():
            total_completion = sum(e.completion_rate or 0 for e in enrollments)
            avg_completion = total_completion / enrollments.count()
        else:
            avg_completion = 0
        
        # Count ungraded assignments
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
        
        if student_count > 0:  # Only show courses with students
            courses_data.append({
                'course': course,
                'student_count': student_count,
                'avg_completion': avg_completion,
                'ungraded_count': ungraded_count,
            })
    
    # Calculate overall statistics
    total_students = Student.objects.count()
    all_enrollments = Enrollment.objects.all()
    if all_enrollments.exists():
        overall_completion = sum(e.completion_rate or 0 for e in all_enrollments) / all_enrollments.count()
    else:
        overall_completion = 0
    
    context = {
        'courses_data': courses_data,
        'total_courses': len(courses_data),
        'total_students': total_students,
        'overall_completion': round(overall_completion, 1),
    }
    return render(request, 'app/courses.html', context)


@staff_required
def students_list(request):
    """List all students with their progress across all courses - requires staff access"""
    from collections import defaultdict
    
    # Get all courses that have enrollments
    courses = Course.objects.filter(enrollments__isnull=False).distinct().order_by('name')
    
    # Get all unique students with their enrollments
    students_dict = defaultdict(lambda: {'name': '', 'email': '', 'enrollments': {}})
    
    # Get all enrollments with related data
    all_enrollments = Enrollment.objects.select_related('student', 'course').all()
    
    for enrollment in all_enrollments:
        student_id = enrollment.student.id
        students_dict[student_id]['name'] = enrollment.student.full_name
        students_dict[student_id]['email'] = enrollment.student.email
        students_dict[student_id]['student'] = enrollment.student
        students_dict[student_id]['enrollments'][enrollment.course.id] = enrollment
    
    # Convert to sorted list by student name
    students = sorted(students_dict.values(), key=lambda x: x['name'])
    
    context = {
        'students': students,
        'courses': courses,
    }
    return render(request, 'app/students_list.html', context)


@staff_required
def course_detail(request, course_id):
    """Detailed view of a single course - requires staff access"""
    course = get_object_or_404(Course, id=course_id)
    
    # Get all enrollments for this course with student info
    enrollments = Enrollment.objects.filter(
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
        'ungraded_assignments': ungraded_assignments,
        'total_students': total_students,
        'total_assignments': total_assignments,
    }
    return render(request, 'app/course_detail.html', context)


@staff_required
def student_detail(request, student_id):
    """Detailed view of a student across all their course enrollments - requires staff access"""
    # Get student
    student = get_object_or_404(Student, id=student_id)
    
    # Get all enrollments for this student
    enrollments = Enrollment.objects.filter(
        student=student
    ).select_related('course', 'cohort').order_by('course__name')
    
    # Get registrations for this student
    registrations = Registration.objects.filter(
        student=student
    ).select_related('cohort').order_by('-cohort__start_date')
    
    # Calculate overall stats from enrollments
    total_enrollments = enrollments.count()
    
    if total_enrollments > 0:
        avg_completion = sum(e.completion_rate or 0 for e in enrollments) / total_enrollments
        scores = [e.overall_average_score for e in enrollments if e.overall_average_score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        improvements = [e.improvement_rate for e in enrollments if e.improvement_rate is not None]
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0
        has_improvement = len(improvements) > 0
        on_times = [e.on_time_rate or 0 for e in enrollments]
        avg_on_time = sum(on_times) / len(on_times) if on_times else 0
    else:
        avg_completion = avg_score = avg_improvement = avg_on_time = 0
        has_improvement = False
    
    # Calculate attendance statistics
    attendance_records = Attendance.objects.filter(
        student=student
    ).order_by('date')
    
    total_hours = sum(r.hours_spent or 0 for r in attendance_records)
    total_weeks = attendance_records.count()
    
    context = {
        'student': student,
        'student_name': student.full_name,
        'student_email': student.email,
        'enrollments': enrollments,
        'registrations': registrations,
        'total_enrollments': total_enrollments,
        'avg_completion': avg_completion,
        'avg_score': avg_score,
        'avg_improvement': avg_improvement,
        'has_improvement': has_improvement,
        'avg_on_time': avg_on_time,
        'attendance_records': attendance_records,
        'total_hours': total_hours,
        'total_weeks': total_weeks,
    }
    return render(request, 'app/student_detail.html', context)


@login_required
def profile(request):
    """Student profile view - shows logged-in student's data"""
    # Get or create student profile for logged-in user
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.info(request, 'You are not enrolled in any courses yet.')
        return redirect('home')
    
    # Get all enrollments for this student
    enrollments = Enrollment.objects.filter(
        student=student
    ).select_related('course', 'cohort').order_by('course__name')
    
    # Get registrations for this student
    registrations = Registration.objects.filter(
        student=student
    ).select_related('cohort').order_by('-cohort__start_date')
    
    # Calculate overall stats from enrollments
    total_enrollments = enrollments.count()
    
    if total_enrollments > 0:
        avg_completion = sum(e.completion_rate or 0 for e in enrollments) / total_enrollments
        scores = [e.overall_average_score for e in enrollments if e.overall_average_score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        improvements = [e.improvement_rate for e in enrollments if e.improvement_rate is not None]
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0
        has_improvement = len(improvements) > 0
        on_times = [e.on_time_rate or 0 for e in enrollments]
        avg_on_time = sum(on_times) / len(on_times) if on_times else 0
    else:
        avg_completion = avg_score = avg_improvement = avg_on_time = 0
        has_improvement = False
    
    # Calculate attendance statistics
    attendance_records = Attendance.objects.filter(
        student=student
    ).order_by('date')
    
    total_hours = sum(r.hours_spent or 0 for r in attendance_records)
    total_weeks = attendance_records.count()
    
    context = {
        'student': student,
        'enrollments': enrollments,
        'registrations': registrations,
        'total_enrollments': total_enrollments,
        'avg_completion': avg_completion,
        'avg_score': avg_score,
        'avg_improvement': avg_improvement,
        'has_improvement': has_improvement,
        'avg_on_time': avg_on_time,
        'attendance_records': attendance_records,
        'total_hours': total_hours,
        'total_weeks': total_weeks,
        'is_profile': True,
    }
    return render(request, 'app/profile.html', context)


@staff_required
def cohorts(request):
    """Display cohort statistics - requires staff access"""
    cohorts_data = []
    
    for cohort in Cohort.objects.all().order_by('-start_date'):
        # Get registrations for this cohort
        registrations = Registration.objects.filter(cohort=cohort)
        total_registrations = registrations.count()
        
        # Count by status
        pending = registrations.filter(status='PENDING').count()
        approved = registrations.filter(status='APPROVED').count()
        active = registrations.filter(status='ACTIVE').count()
        completed = registrations.filter(status='COMPLETED').count()
        dropped = registrations.filter(status='DROPPED').count()
        
        # Get unique courses students are enrolled in for this cohort
        enrollments = Enrollment.objects.filter(cohort=cohort)
        unique_courses = enrollments.values('course').distinct().count()
        
        # Calculate average completion rate from active/completed registrations
        active_registrations = registrations.filter(status__in=['ACTIVE', 'COMPLETED'])
        if active_registrations.exists():
            total_completion = sum(r.overall_completion_rate or 0 for r in active_registrations)
            avg_completion = total_completion / active_registrations.count()
        else:
            avg_completion = 0
        
        # Get certificates for this cohort
        certificates = Certificate.objects.filter(registration__cohort=cohort).count()
        
        cohorts_data.append({
            'cohort': cohort,
            'total_registrations': total_registrations,
            'pending': pending,
            'approved': approved,
            'active': active,
            'completed': completed,
            'dropped': dropped,
            'unique_courses': unique_courses,
            'avg_completion': avg_completion,
            'certificates_issued': certificates,
        })
    
    context = {
        'cohorts_data': cohorts_data,
    }
    return render(request, 'app/cohorts.html', context)


@staff_required
def cohort_detail(request, cohort_id):
    """Detailed view of a single cohort - requires staff access"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Get registrations for this cohort
    registrations = Registration.objects.filter(cohort=cohort).select_related('student')
    total_registrations = registrations.count()
    
    # Count by status
    pending = registrations.filter(status='PENDING').count()
    approved = registrations.filter(status='APPROVED').count()
    active = registrations.filter(status='ACTIVE').count()
    completed = registrations.filter(status='COMPLETED').count()
    dropped = registrations.filter(status='DROPPED').count()
    
    # Get all enrollments for this cohort
    enrollments = Enrollment.objects.filter(cohort=cohort).select_related('course', 'student')
    
    # Get unique courses students are enrolled in
    courses_data = {}
    for enrollment in enrollments:
        course = enrollment.course
        if course.id not in courses_data:
            courses_data[course.id] = {
                'course': course,
                'student_count': 0,
                'avg_completion': 0,
                'completions': [],
            }
        courses_data[course.id]['student_count'] += 1
        if enrollment.completion_rate:
            courses_data[course.id]['completions'].append(enrollment.completion_rate)
    
    # Calculate averages
    courses = []
    for course_data in courses_data.values():
        if course_data['completions']:
            course_data['avg_completion'] = sum(course_data['completions']) / len(course_data['completions'])
        courses.append(course_data)
    
    # Calculate average completion rate from active/completed registrations
    active_registrations = registrations.filter(status__in=['ACTIVE', 'COMPLETED'])
    if active_registrations.exists():
        total_completion = sum(r.overall_completion_rate or 0 for r in active_registrations)
        avg_completion = total_completion / active_registrations.count()
    else:
        avg_completion = 0
    
    # Get certificates
    certificates = Certificate.objects.filter(registration__cohort=cohort).count()
    
    context = {
        'cohort': cohort,
        'courses': courses,
        'total_courses': len(courses),
        'total_registrations': total_registrations,
        'pending': pending,
        'approved': approved,
        'active': active,
        'completed': completed,
        'dropped': dropped,
        'avg_completion': avg_completion,
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
def attendance_mismatches(request):
    """Show attendance records - no longer has mismatches since using proper FKs"""
    # Redirect to main attendance page since we no longer track email mismatches
    messages.info(request, 'Attendance now uses proper student references. No mismatches to show.')
    return redirect('attendance')


