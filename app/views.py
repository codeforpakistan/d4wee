from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import (
    Student, Course, Cohort, Registration, Enrollment,
    Assignment, Submission, Attendance, Certificate
)


def dashboard(request):
    """Main dashboard view - shows user's cohort registrations and course enrollments"""
    context = {
        'registrations': [],
        'has_registrations': False,
        'student': None,
    }
    
    # If user is authenticated, show their registrations and enrollments
    if request.user.is_authenticated:
        try:
            # Get or create student profile for logged-in user
            student = Student.objects.filter(user=request.user).first()
            
            if student:
                context['student'] = student
                
                # Get active registrations (cohorts they're enrolled in)
                registrations = Registration.objects.filter(
                    student=student,
                    status__in=['APPROVED', 'ACTIVE', 'COMPLETED']
                ).select_related('cohort').prefetch_related('enrollments__course').order_by('-cohort__start_date')
                
                if registrations.exists():
                    context['has_registrations'] = True
                    
                    # Build registration data with enrollments
                    registrations_data = []
                    for registration in registrations:
                        # Get enrollments for this registration
                        enrollments = registration.enrollments.all()
                        
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
                            'attendance_rate': registration.session_attendance_rate,
                            'overall_completion': registration.overall_completion_rate,
                        })
                    
                    context['registrations'] = registrations_data
                
        except Exception as e:
            messages.error(request, f'Error loading dashboard: {str(e)}')
    
    return render(request, 'app/dashboard.html', context)


def courses(request):
    """Courses list view - public access"""
    from django.db.models import Count, Q, Avg
    
    # Only show courses with enrolled students
    courses = Course.objects.annotate(
        student_count=Count('students'),
        avg_completion=Avg('student_metrics__completion_rate')
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
    
    # Calculate overall statistics
    total_students = Student.objects.values('google_id').distinct().count()
    overall_completion = StudentMetrics.objects.aggregate(
        avg=Avg('completion_rate')
    )['avg'] or 0
    
    context = {
        'courses': courses,
        'total_courses': courses.count(),
        'total_students': total_students,
        'overall_completion': round(overall_completion, 1),
    }
    return render(request, 'app/courses.html', context)


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
    return render(request, 'app/students_list.html', context)


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
    return render(request, 'app/course_detail.html', context)


def student_detail(request, google_id):
    """Detailed view of a student across all their course enrollments - public access"""
    # Get all enrollments for this student
    enrollments = Student.objects.filter(google_id=google_id).select_related('course')
    
    if not enrollments.exists():
        messages.error(request, 'Student not found.')
        return redirect('home')
    
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
        avg_assignment = sum(e['metrics'].assignment_average for e in enrollment_data if e['metrics'].assignment_average is not None) / max(1, sum(1 for e in enrollment_data if e['metrics'].assignment_average is not None))
        avg_improvement = sum(e['metrics'].improvement_rate for e in enrollment_data if e['metrics'].improvement_rate is not None) / max(1, sum(1 for e in enrollment_data if e['metrics'].improvement_rate is not None))
        avg_on_time = sum(e['metrics'].on_time_rate for e in enrollment_data) / total_enrollments
        has_improvement = any(e['metrics'].improvement_rate is not None for e in enrollment_data)
    else:
        avg_completion = avg_score = avg_assignment = avg_improvement = avg_on_time = 0
        has_improvement = False
    
    # Calculate attendance statistics using google_id
    attendance_records = Attendance.objects.filter(
        google_id=google_id
    ).order_by('week_number')
    
    weeks_attended = attendance_records.values('week_number').distinct().count()
    total_weeks = Attendance.objects.values('week_number').distinct().count()
    attendance_rate = round((weeks_attended / total_weeks * 100), 1) if total_weeks > 0 else 0
    
    # Get weekly attendance details (one per week, even if multiple records exist)
    weekly_attendance = []
    weeks_seen = set()
    for record in attendance_records:
        if record.week_number not in weeks_seen:
            weekly_attendance.append({
                'week': record.week_number,
                'date': record.date,
                'timestamp': record.timestamp,
            })
            weeks_seen.add(record.week_number)
    
    context = {
        'google_id': google_id,
        'student_name': student_name,
        'student_email': student_email,
        'enrollments': enrollment_data,
        'total_enrollments': total_enrollments,
        'avg_completion': avg_completion,
        'avg_score': avg_score,
        'avg_assignment': avg_assignment,
        'avg_improvement': avg_improvement,
        'has_improvement': has_improvement,
        'avg_on_time': avg_on_time,
        'weeks_attended': weeks_attended,
        'total_weeks': total_weeks,
        'attendance_rate': attendance_rate,
        'weekly_attendance': weekly_attendance,
    }
    return render(request, 'app/student_detail.html', context)


@login_required
def profile(request):
    """Student profile view - shows logged-in student's data similar to student_detail"""
    from allauth.socialaccount.models import SocialAccount
    
    # Get user's Google ID from their social account
    try:
        social_account = SocialAccount.objects.get(user=request.user, provider='google')
        google_id = social_account.uid
    except SocialAccount.DoesNotExist:
        messages.error(request, 'No Google account linked. Please sign in with Google.')
        return redirect('home')
    
    # Get all enrollments for this student
    enrollments = Student.objects.filter(google_id=google_id).select_related('course')
    
    if not enrollments.exists():
        messages.info(request, 'You are not enrolled in any courses yet.')
        return redirect('home')
    
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
        avg_assignment = sum(e['metrics'].assignment_average for e in enrollment_data if e['metrics'].assignment_average is not None) / max(1, sum(1 for e in enrollment_data if e['metrics'].assignment_average is not None))
        avg_improvement = sum(e['metrics'].improvement_rate for e in enrollment_data if e['metrics'].improvement_rate is not None) / max(1, sum(1 for e in enrollment_data if e['metrics'].improvement_rate is not None))
        avg_on_time = sum(e['metrics'].on_time_rate for e in enrollment_data) / total_enrollments
        has_improvement = any(e['metrics'].improvement_rate is not None for e in enrollment_data)
    else:
        avg_completion = avg_score = avg_assignment = avg_improvement = avg_on_time = 0
        has_improvement = False
    
    context = {
        'google_id': google_id,
        'student_name': student_name,
        'student_email': student_email,
        'enrollments': enrollment_data,
        'total_enrollments': total_enrollments,
        'avg_completion': avg_completion,
        'avg_score': avg_score,
        'avg_assignment': avg_assignment,
        'avg_improvement': avg_improvement,
        'has_improvement': has_improvement,
        'avg_on_time': avg_on_time,
        'is_profile': True,  # Flag to indicate this is the profile view
    }
    return render(request, 'app/profile.html', context)


def cohorts(request):
    """Display cohort statistics"""
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


def cohort_detail(request, cohort_id):
    """Detailed view of a single cohort"""
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


def attendance(request):
    """Display student attendance by week"""
    from collections import defaultdict
    from django.db.models import Min, Max
    from .models import Cohort
    
    # Get filter parameters
    selected_cohort = request.GET.get('cohort', None)
    selected_week = request.GET.get('week', None)
    
    # Base queryset
    attendance_records = Attendance.objects.all()
    
    # Apply filters
    if selected_cohort:
        attendance_records = attendance_records.filter(cohort_id=selected_cohort)
    if selected_week:
        attendance_records = attendance_records.filter(week_number=selected_week)
    
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
    for record in attendance_records.select_related('cohort').order_by('week_number'):
        week = record.week_number
        weeks_data[week]['week_number'] = week
        weeks_data[week]['unique_students'].add(record.student_email)
        weeks_data[week]['present_students'].add(record.student_email)
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
    all_unique_students = set(Attendance.objects.values_list('student_email', flat=True))
    total_enrolled_students = len(all_unique_students)
    
    # For filtered view, count unique students in filtered records
    present_students = set(attendance_records.values_list('student_email', flat=True))
    total_present = len(present_students)
    
    overall_attendance_rate = round((total_present / total_enrolled_students * 100), 1) if total_enrolled_students > 0 else 0
    
    # Recalculate attendance rate for each week based on total enrolled students
    for data in weeks_list:
        if total_enrolled_students > 0:
            data['attendance_rate'] = round((data['present_count'] / total_enrolled_students) * 100, 1)
        else:
            data['attendance_rate'] = 0
    
    # Get unique weeks and cohorts for filters (from all records, not filtered)
    available_weeks = sorted(set(Attendance.objects.values_list('week_number', flat=True)))
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
    
    # Get counts for different issue types
    # Only count records that don't have an exact email match (real issues)
    missing_google_id = Attendance.objects.filter(google_id='')
    real_issues_count = 0
    for record in missing_google_id:
        # Skip if there's an exact email match (can be auto-fixed)
        if not Student.objects.filter(email__iexact=record.student_email).exists():
            real_issues_count += 1
    
    issue_categories = [
        {
            'title': 'Attendance Email Issues',
            'description': 'Attendance records that couldn\'t be matched to students due to email differences',
            'count': real_issues_count,
            'url': 'issues_attendance_emails',
            'icon': 'email',
            'severity': 'warning' if real_issues_count > 0 else 'success',
        },
        # Future issue types can be added here
        # {
        #     'title': 'Duplicate Students',
        #     'description': 'Students enrolled multiple times in the same course',
        #     'count': 0,
        #     'url': 'issues_duplicate_students',
        #     'icon': 'users',
        #     'severity': 'error',
        # },
    ]
    
    context = {
        'issue_categories': issue_categories,
        'total_issues': sum(cat['count'] for cat in issue_categories),
    }
    return render(request, 'app/issues.html', context)


@login_required
def attendance_mismatches(request):
    """Show attendance records with missing google_id (email mismatches)"""
    from collections import defaultdict
    
    # Get all attendance records with missing google_id
    missing_records = Attendance.objects.filter(google_id='').order_by('student_email', 'week_number')
    
    # Group by email to show all records for each student
    email_groups = defaultdict(list)
    for record in missing_records:
        email_groups[record.student_email].append(record)
    
    # For each email, try to find potential matches in Student table
    mismatch_data = []
    for email, records in email_groups.items():
        # Try to find similar students
        potential_matches = []
        
        # 1. Exact match (case-insensitive) - if found, skip this record (can be auto-fixed)
        exact_match = Student.objects.filter(email__iexact=email).first()
        if exact_match:
            # This is not a real issue - email is correct, just needs google_id update
            # Skip it from the issues list
            continue
        
        # 2. Partial match on email username (before @)
        if '@' in email:
            email_username = email.split('@')[0]
            similar_students = Student.objects.filter(email__icontains=email_username).exclude(email__iexact=email)[:5]
            for student in similar_students:
                potential_matches.append({
                    'student': student,
                    'match_type': 'partial',
                    'confidence': 'medium'
                })
        
        # 3. Match by name (case-insensitive)
        student_name = records[0].student_name
        name_matches = Student.objects.filter(full_name__icontains=student_name)[:3]
        for student in name_matches:
            # Avoid duplicates
            if not any(m['student'].id == student.id for m in potential_matches):
                potential_matches.append({
                    'student': student,
                    'match_type': 'name',
                    'confidence': 'low'
                })
        
        mismatch_data.append({
            'email': email,
            'name': records[0].student_name,
            'city': records[0].city,
            'record_count': len(records),
            'weeks': sorted([r.week_number for r in records]),
            'records': records,
            'potential_matches': potential_matches,
        })
    
    # Sort by number of records (students with most records first)
    mismatch_data.sort(key=lambda x: x['record_count'], reverse=True)
    
    context = {
        'mismatch_data': mismatch_data,
        'total_records': missing_records.count(),
        'total_students': len(mismatch_data),
    }
    return render(request, 'app/attendance_mismatches.html', context)


