from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Course, Student, Assignment, Submission, Attendance


def dashboard(request):
    """Main dashboard view - shows user's enrolled courses grouped by cohort"""
    from django.db.models import Avg
    from collections import defaultdict
    from allauth.socialaccount.models import SocialAccount
    
    context = {
        'user_courses': [],
        'cohorts_with_courses': [],
        'has_courses': False,
        'google_id': None,
    }
    
    # If user is authenticated, show their courses
    if request.user.is_authenticated:
        try:
            # Get user's Google ID from their social account
            social_account = SocialAccount.objects.get(user=request.user, provider='google')
            google_id = social_account.uid
            context['google_id'] = google_id
            
            # Get all student records for this google_id
            student_records = Student.objects.filter(
                google_id=google_id
            ).select_related('course', 'course__cohort').prefetch_related(
                'course__assignments',
                'course__student_metrics'
            )
            
            if student_records.exists():
                context['has_courses'] = True
                
                # Group courses by cohort
                cohorts_dict = defaultdict(lambda: {
                    'cohort': None,
                    'courses': []
                })
                
                for student_record in student_records:
                    course = student_record.course
                    cohort = course.cohort
                    
                    # Get student's metrics for this course
                    try:
                        metrics = StudentMetrics.objects.get(
                            student=student_record,
                            course=course
                        )
                        completion = metrics.completion_rate
                        avg_grade = metrics.assignment_average
                    except StudentMetrics.DoesNotExist:
                        completion = 0
                        avg_grade = None
                    
                    # Count assignments
                    total_assignments = course.assignments.count()
                    
                    # Count turned in submissions
                    turned_in = Submission.objects.filter(
                        student=student_record,
                        assignment__course=course,
                        state__in=['TURNED_IN', 'RETURNED']
                    ).count()
                    
                    course_data = {
                        'course': course,
                        'completion': completion,
                        'avg_grade': avg_grade,
                        'total_assignments': total_assignments,
                        'turned_in': turned_in,
                    }
                    
                    cohort_key = cohort.id if cohort else 'no_cohort'
                    cohorts_dict[cohort_key]['cohort'] = cohort
                    cohorts_dict[cohort_key]['courses'].append(course_data)
                
                # Convert to list and sort by cohort start_date (newest first)
                cohorts_list = []
                for key, data in cohorts_dict.items():
                    if data['cohort']:
                        cohorts_list.append(data)
                
                # Sort by cohort start_date descending (newest first)
                cohorts_list.sort(
                    key=lambda x: x['cohort'].start_date if x['cohort'] else '',
                    reverse=True
                )
                
                context['cohorts_with_courses'] = cohorts_list
                
        except SocialAccount.DoesNotExist:
            # User logged in with username/password, not Google OAuth
            pass
    
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
    """Display cohort completion statistics"""
    from .models import Cohort, CohortEnrollment, Certificate
    from django.db.models import Avg, Count, Q
    
    cohorts_data = []
    
    for cohort in Cohort.objects.all().order_by('start_date'):
        # Count unique students across all courses in this cohort
        courses = cohort.courses.all()
        unique_students = Student.objects.filter(
            course__cohort=cohort
        ).values('google_id').distinct().count()
        
        # Calculate completion based on StudentMetrics
        # Students with completion_rate >= 80% are considered "completed"
        completed_metrics = StudentMetrics.objects.filter(
            course__cohort=cohort,
            completion_rate__gte=80
        ).values('student__google_id').distinct().count()
        
        # Calculate average completion rate across all students in cohort
        avg_completion = StudentMetrics.objects.filter(
            course__cohort=cohort
        ).aggregate(avg=Avg('completion_rate'))['avg'] or 0
        
        # Get enrollment statistics from CohortEnrollment (if manually tracked)
        enrollments = CohortEnrollment.objects.filter(cohort=cohort)
        in_progress = enrollments.filter(status='IN_PROGRESS').count()
        dropped = enrollments.filter(status='DROPPED').count()
        enrolled_status = enrollments.filter(status='ENROLLED').count()
        
        certificates = Certificate.objects.filter(cohort=cohort)
        
        cohorts_data.append({
            'cohort': cohort,
            'total_enrollments': unique_students,
            'completed': completed_metrics,
            'in_progress': in_progress,
            'enrolled': enrolled_status,
            'dropped': dropped,
            'completion_rate': avg_completion,
            'certificates_issued': certificates.count(),
            'courses': courses,
        })
    
    context = {
        'cohorts_data': cohorts_data,
    }
    return render(request, 'app/cohorts.html', context)


def cohort_detail(request, cohort_id):
    """Detailed view of a single cohort with its courses"""
    from django.db.models import Count, Avg
    from .models import Cohort, CohortEnrollment, Certificate
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Get courses for this cohort
    courses = Course.objects.filter(cohort=cohort).annotate(
        student_count=Count('students'),
        avg_completion=Avg('student_metrics__completion_rate')
    ).prefetch_related('students', 'assignments', 'student_metrics').order_by('name')
    
    # Calculate ungraded assignments for each course
    for course in courses:
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
    
    # Count unique students across all courses in this cohort
    total_enrollments = Student.objects.filter(
        course__cohort=cohort
    ).values('google_id').distinct().count()
    
    # Calculate completion based on StudentMetrics (students with >= 80% completion)
    completed_students = StudentMetrics.objects.filter(
        course__cohort=cohort,
        completion_rate__gte=80
    ).values('student__google_id').distinct().count()
    
    # Calculate average completion rate across all students in cohort
    completion_rate = StudentMetrics.objects.filter(
        course__cohort=cohort
    ).aggregate(avg=Avg('completion_rate'))['avg'] or 0
    
    # Get enrollment statistics from CohortEnrollment (if manually tracked)
    enrollments = CohortEnrollment.objects.filter(cohort=cohort)
    in_progress = enrollments.filter(status='IN_PROGRESS').count()
    enrolled = enrollments.filter(status='ENROLLED').count()
    dropped = enrollments.filter(status='DROPPED').count()
    
    certificates = Certificate.objects.filter(cohort=cohort)
    
    # Calculate overall completion for this cohort's courses
    overall_completion = courses.aggregate(avg=Avg('student_metrics__completion_rate'))['avg'] or 0
    
    context = {
        'cohort': cohort,
        'courses': courses,
        'total_courses': courses.count(),
        'total_enrollments': total_enrollments,
        'completed': completed_students,
        'in_progress': in_progress,
        'enrolled': enrolled,
        'dropped': dropped,
        'completion_rate': completion_rate,
        'certificates_issued': certificates.count(),
        'overall_completion': overall_completion,
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

