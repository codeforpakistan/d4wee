"""
Google Classroom API integration service
TODO: Rewrite sync logic to use new model structure (Registration, Enrollment)
"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from allauth.socialaccount.models import SocialToken
from django.utils import timezone
from datetime import datetime
from .models import Course, Student, Assignment, Submission, SyncLog, AttendanceRecord
# TODO: Update sync to use Enrollment model instead of StudentMetrics


def get_classroom_service(user):
    """Get authenticated Google Classroom API service for user"""
    from allauth.socialaccount.models import SocialAccount
    
    try:
        # First, get the social account
        social_account = SocialAccount.objects.get(
            user=user,
            provider='google'
        )
        
        # Get the social token
        social_token = SocialToken.objects.get(
            account=social_account
        )
        
        # Get the app credentials from the database
        from allauth.socialaccount.models import SocialApp
        social_app = SocialApp.objects.get(provider='google')
        
        credentials = Credentials(
            token=social_token.token,
            refresh_token=social_token.token_secret,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=social_app.client_id,
            client_secret=social_app.secret
        )
        
        service = build('classroom', 'v1', credentials=credentials)
        return service
    except SocialAccount.DoesNotExist:
        raise Exception("User is not connected to Google Classroom. Please sign in.")
    except SocialToken.DoesNotExist:
        raise Exception("OAuth token not found. Please sign out and sign in again.")
    except SocialApp.DoesNotExist:
        raise Exception("Google OAuth app not configured. Please run: python manage.py seed")


def sync_all_classroom_data(user, target_cohort=None):
    """
    Sync classroom data from Google Classroom API
    Only syncs courses belonging to target_cohort (or courses with no cohort assigned yet)
    
    Args:
        user: Django user with Google OAuth
        target_cohort: Cohort to sync data for. Must be an active cohort.
    
    Returns SyncLog instance
    """
    import gc
    from .models import Cohort
    from django.utils import timezone
    
    if not target_cohort:
        raise Exception("Target cohort is required for sync")
    
    print(f"🎯 Syncing data for active cohort: {target_cohort.name}")
    
    sync_log = SyncLog.objects.create(status='IN_PROGRESS')
    
    try:
        service = get_classroom_service(user)
        
        # Fetch all courses
        courses_result = service.courses().list(pageSize=100).execute()
        courses_data = courses_result.get('courses', [])
        
        for course_data in courses_data:
            try:
                # First, check if this course exists and has a cohort
                existing_course = Course.objects.filter(google_id=course_data['id']).first()
                
                # Skip if course belongs to a different (inactive) cohort
                if existing_course and existing_course.cohort and existing_course.cohort != target_cohort:
                    print(f"⏭️  Skipping '{existing_course.name}' (belongs to {existing_course.cohort.name})")
                    continue
                
                # Sync the course (will assign to target_cohort if no cohort)
                course, created = sync_course(course_data, target_cohort)
                if course:
                    sync_log.courses_synced += 1
                    
                    # Sync students for this course
                    students_count = sync_students(service, course)
                    sync_log.students_synced += students_count
                    
                    # Sync assignments for this course
                    assignments_count = sync_assignments(service, course)
                    sync_log.assignments_synced += assignments_count
                    
                    # Sync submissions for this course
                    submissions_count = sync_submissions(service, course)
                    sync_log.submissions_synced += submissions_count
                    
                    # Calculate metrics for all students in this course
                    calculate_student_metrics(course)
                    
                    # Clear memory after each course
                    gc.collect()
            except Exception as e:
                print(f"Error syncing course {course_data.get('id', 'unknown')}: {e}")
                continue
        
        sync_log.status = 'COMPLETED'
        sync_log.completed_at = timezone.now()
        
    except Exception as e:
        sync_log.status = 'FAILED'
        sync_log.errors = str(e)
        raise
    finally:
        sync_log.save()
    
    return sync_log


def sync_course(course_data, target_cohort=None):
    """Sync a single course and assign to target cohort if not already assigned"""
    try:
        course, created = Course.objects.update_or_create(
            google_id=course_data['id'],
            defaults={
                'name': course_data.get('name', ''),
                'section': course_data.get('section', ''),
                'description_heading': course_data.get('descriptionHeading', ''),
                'enrollment_code': course_data.get('enrollmentCode', ''),
                'course_state': course_data.get('courseState', 'ACTIVE'),
            }
        )
        
        # Auto-assign to target cohort if course doesn't have one
        if not course.cohort and target_cohort:
            course.cohort = target_cohort
            course.save()
            print(f"✅ Assigned course '{course.name}' to cohort '{target_cohort.name}'")
        
        return course, created
    except Exception as e:
        print(f"Error syncing course {course_data.get('id')}: {e}")
        return None, False


def sync_students(service, course):
    """Sync students for a course with pagination"""
    count = 0
    try:
        page_token = None
        while True:
            students_result = service.courses().students().list(
                courseId=course.google_id,
                pageSize=1000,
                pageToken=page_token
            ).execute()
            
            for student_data in students_result.get('students', []):
                profile = student_data.get('profile', {})
                user_id = student_data['userId']
                
                # Get profile data
                full_name = profile.get('name', {}).get('fullName', '')
                email = profile.get('emailAddress', '')
                
                # Use student ID as identifier if name is hidden
                if not full_name or full_name == 'Unknown user':
                    full_name = f"Student {user_id[-8:]}"
                
                Student.objects.update_or_create(
                    google_id=user_id,
                    course=course,
                    defaults={
                        'email': email,
                        'full_name': full_name,
                    }
                )
                count += 1
            
            # Check if there are more pages
            page_token = students_result.get('nextPageToken')
            if not page_token:
                break
                
    except Exception as e:
        print(f"Error syncing students for course {course.google_id}: {e}")
    
    return count


def sync_assignments(service, course):
    """Sync assignments for a course with pagination"""
    count = 0
    try:
        page_token = None
        while True:
            coursework_result = service.courses().courseWork().list(
                courseId=course.google_id,
                pageSize=1000,
                pageToken=page_token
            ).execute()
            
            for work_data in coursework_result.get('courseWork', []):
                # Parse due date if exists
                due_date = None
                if 'dueDate' in work_data and 'dueTime' in work_data:
                    due_date_dict = work_data['dueDate']
                    due_time_dict = work_data['dueTime']
                    try:
                        due_date = datetime(
                            year=due_date_dict.get('year'),
                            month=due_date_dict.get('month'),
                            day=due_date_dict.get('day'),
                            hour=due_time_dict.get('hours', 0),
                            minute=due_time_dict.get('minutes', 0)
                        )
                        due_date = timezone.make_aware(due_date)
                    except:
                        pass
                
                Assignment.objects.update_or_create(
                    google_id=work_data['id'],
                    defaults={
                        'course': course,
                        'title': work_data.get('title', ''),
                        'description': work_data.get('description', ''),
                        'work_type': work_data.get('workType', 'ASSIGNMENT'),
                        'max_points': work_data.get('maxPoints'),
                        'due_date': due_date,
                        'topic': work_data.get('topicId', ''),
                        'state': work_data.get('state', 'PUBLISHED'),
                    }
                )
                count += 1
            
            # Check if there are more pages
            page_token = coursework_result.get('nextPageToken')
            if not page_token:
                break
                
    except Exception as e:
        print(f"Error syncing assignments for course {course.google_id}: {e}")
    
    return count


def sync_submissions(service, course):
    """Sync submissions for all assignments in a course with pagination"""
    import gc
    count = 0
    try:
        # Use iterator() to avoid caching all assignments in memory
        assignments = Assignment.objects.filter(course=course).iterator(chunk_size=10)
        
        for assignment in assignments:
            page_token = None
            while True:
                submissions_result = service.courses().courseWork().studentSubmissions().list(
                    courseId=course.google_id,
                    courseWorkId=assignment.google_id,
                    pageSize=1000,
                    pageToken=page_token
                ).execute()
                
                for sub_data in submissions_result.get('studentSubmissions', []):
                    try:
                        student = Student.objects.get(
                            google_id=sub_data['userId'],
                            course=course
                        )
                        
                        # Parse timestamps
                        creation_time = parse_timestamp(sub_data.get('creationTime'))
                        update_time = parse_timestamp(sub_data.get('updateTime'))
                        
                        Submission.objects.update_or_create(
                            google_id=sub_data['id'],
                            defaults={
                                'assignment': assignment,
                                'student': student,
                                'state': sub_data.get('state', 'NEW'),
                                'late': sub_data.get('late', False),
                                'assigned_grade': sub_data.get('assignedGrade'),
                                'draft_grade': sub_data.get('draftGrade'),
                                'creation_time': creation_time,
                                'update_time': update_time,
                            }
                        )
                        count += 1
                    except Student.DoesNotExist:
                        continue
                
                # Check if there are more pages
                page_token = submissions_result.get('nextPageToken')
                if not page_token:
                    break
            
            # Clear memory after each assignment
            gc.collect()
                    
    except Exception as e:
        print(f"Error syncing submissions for course {course.google_id}: {e}")
    
    return count


def parse_timestamp(timestamp_str):
    """Parse Google API timestamp string to datetime"""
    if not timestamp_str:
        return None
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except:
        return None


def calculate_student_metrics(course):
    """Calculate metrics for all students in a course"""
    import gc
    
    def categorize_assignment(title):
        """Categorize assignment as 'PRE', 'POST', or 'ASSIGNMENT' based on title"""
        import re
        title_lower = title.lower()
        # Check if 'pre' or 'post' appears as a word (surrounded by space, hyphen, or start/end)
        # Word boundary \b matches position between word and non-word character
        if re.search(r'\bpre\b', title_lower):
            return 'PRE'
        elif re.search(r'\bpost\b', title_lower):
            return 'POST'
        else:
            return 'ASSIGNMENT'
    
    # Use iterator() to avoid caching all students in memory
    students = Student.objects.filter(course=course).iterator(chunk_size=50)
    total_assignments = Assignment.objects.filter(course=course).count()
    
    if total_assignments == 0:
        return
    
    for student in students:
        submissions = Submission.objects.filter(student=student)
        
        # Calculate metrics
        completed = submissions.filter(state__in=['TURNED_IN', 'RETURNED']).count()
        completion_rate = (completed / total_assignments) * 100 if total_assignments > 0 else 0
        
        # Get all graded submissions
        graded_submissions = submissions.filter(
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False,
            assignment__max_points__gt=0
        ).select_related('assignment')
        
        # Separate submissions by type
        pre_test_scores = []
        post_test_scores = []
        assignment_scores = []
        all_scores = []
        
        for s in graded_submissions:
            # Type guard: We filter for non-null values above, but help type checker
            if s.assigned_grade is not None and s.assignment.max_points is not None and s.assignment.max_points > 0:
                percentage = (s.assigned_grade / s.assignment.max_points) * 100
                all_scores.append(percentage)
                
                assignment_type = categorize_assignment(s.assignment.title)
                if assignment_type == 'PRE':
                    pre_test_scores.append(percentage)
                elif assignment_type == 'POST':
                    post_test_scores.append(percentage)
                else:
                    assignment_scores.append(percentage)
        
        # Calculate averages
        average_score = sum(all_scores) / len(all_scores) if all_scores else None
        assignment_average = sum(assignment_scores) / len(assignment_scores) if assignment_scores else None
        pre_test_score = sum(pre_test_scores) / len(pre_test_scores) if pre_test_scores else None
        post_test_score = sum(post_test_scores) / len(post_test_scores) if post_test_scores else None
        
        # Check if tests were attempted (not just scored)
        pre_test_attempted = len(pre_test_scores) > 0
        post_test_attempted = len(post_test_scores) > 0
        
        # Calculate improvement rate
        improvement_rate = None
        if pre_test_score is not None and post_test_score is not None:
            # Calculate percentage improvement: ((post - pre) / pre) * 100
            # Or absolute improvement: post - pre
            # Using absolute improvement for clarity
            improvement_rate = post_test_score - pre_test_score
        
        # Calculate attendance rates from AttendanceRecord
        # Get student's attendance records for this course's cohort
        # Match by google_id for reliable matching
        session_attendance_rate = 0.0
        weekly_call_attendance_rate = 0.0
        
        if course.cohort:
            # Count how many weeks the student attended
            attendance_weeks = AttendanceRecord.objects.filter(
                google_id=student.google_id,
                cohort=course.cohort
            ).values('week_number').distinct().count()
            
            # Calculate total weeks from cohort start and end dates
            if course.cohort.start_date and course.cohort.end_date:
                days_duration = (course.cohort.end_date - course.cohort.start_date).days
                total_weeks = max(1, round(days_duration / 7))  # At least 1 week, rounded to nearest week
            else:
                # Fallback: use max week number from attendance data or default to 12
                from django.db.models import Max
                cohort_max_week = AttendanceRecord.objects.filter(
                    cohort=course.cohort
                ).aggregate(Max('week_number'))['week_number__max']
                total_weeks = cohort_max_week if cohort_max_week else 12
            
            session_attendance_rate = (attendance_weeks / total_weeks) * 100 if total_weeks > 0 else 0
            
            # For now, use the same attendance rate for weekly calls
            # You can customize this logic if you track call attendance separately
            weekly_call_attendance_rate = session_attendance_rate
        
        on_time = submissions.filter(late=False, state__in=['TURNED_IN', 'RETURNED']).count()
        on_time_rate = (on_time / total_assignments) * 100 if total_assignments > 0 else 0
        
        late_count = submissions.filter(late=True).count()
        missing_count = total_assignments - completed
        
        # Categorize student based on assignment average (not pre/post tests)
        category = None
        score_for_category = assignment_average if assignment_average is not None else average_score
        if completion_rate < 60 or (score_for_category is not None and score_for_category < 60):
            category = 'FOCUS'
        elif completion_rate >= 85 and (score_for_category is None or score_for_category >= 85):
            category = 'PRAISE'
        else:
            category = 'PUSH'
        
        # TODO: Rewrite metrics calculation to use Enrollment model
        # Old code used StudentMetrics table, new architecture calculates on-the-fly
        # StudentMetrics.objects.update_or_create(
        #     student=student,
        #     course=course,
        #     defaults={...}
        # )
        
        # Clear memory after each student
        gc.collect()


def get_sheets_service(user):
    """Get authenticated Google Sheets API service for user"""
    from allauth.socialaccount.models import SocialAccount
    
    try:
        # First, get the social account
        social_account = SocialAccount.objects.get(
            user=user,
            provider='google'
        )
        
        # Get the social token
        social_token = SocialToken.objects.get(
            account=social_account
        )
        
        # Get the app credentials from the database
        from allauth.socialaccount.models import SocialApp
        social_app = SocialApp.objects.get(provider='google')
        
        credentials = Credentials(
            token=social_token.token,
            refresh_token=social_token.token_secret,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=social_app.client_id,
            client_secret=social_app.secret,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except SocialAccount.DoesNotExist:
        raise Exception("User is not connected to Google. Please sign in.")
    except SocialToken.DoesNotExist:
        raise Exception("OAuth token not found. Please sign out and sign in again.")
    except SocialApp.DoesNotExist:
        raise Exception("Google OAuth app not configured. Please run: python manage.py seed")


def sync_attendance_from_sheets(user, spreadsheet_id='1hWGkuHAKFT-Z6I_I5A0hML9WxLd9sU5wEIOk1WP_4F4', target_cohort=None, clear_existing=False):
    """
    Sync attendance data from Google Sheets
    
    Args:
        user: Django user with Google OAuth
        spreadsheet_id: Google Sheets spreadsheet ID
        target_cohort: Cohort to sync attendance for. Must be an active cohort.
        clear_existing: If True, delete existing attendance records for target cohort before syncing
    
    Returns:
        Dictionary with sync statistics
    """
    from .models import Cohort
    from django.utils import timezone
    
    print(f"📊 Syncing attendance from Google Sheets: {spreadsheet_id}")
    
    if not target_cohort:
        print("⚠️  No target cohort provided for attendance sync")
        return {'created': 0, 'skipped': 0, 'errors': 0}
    
    print(f"🎯 Syncing attendance for active cohort: {target_cohort.name}")
    
    try:
        service = get_sheets_service(user)
        
        # Clear existing data for target cohort only if requested
        if clear_existing:
            count = AttendanceRecord.objects.filter(cohort=target_cohort).count()
            AttendanceRecord.objects.filter(cohort=target_cohort).delete()
            print(f"🗑️  Deleted {count} existing attendance records for {target_cohort.name}")
        
        # Read the sheet data - assuming data is in the first sheet
        # We'll read all data from column A to the end
        range_name = 'Form Responses 1!A:K'  # Adjust sheet name if needed
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            print("⚠️  No data found in spreadsheet")
            return {'created': 0, 'skipped': 0, 'errors': 0}
        
        # First row is header
        headers = values[0]
        print(f"📋 Headers: {headers}")
        
        program_start = target_cohort.start_date
        
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        # Process data rows
        for row_num, row in enumerate(values[1:], start=2):
            try:
                # Pad row if it has fewer columns than headers
                while len(row) < len(headers):
                    row.append('')
                
                # Map row to dictionary using headers
                data = dict(zip(headers, row))
                
                # Extract fields (adjust column names based on actual sheet)
                timestamp_str = data.get('Timestamp', '').strip()
                email = data.get('Email Address', '').strip()
                name = data.get('Name', '').strip()
                city = data.get('City ', '').strip()  # Note the space
                unique_id = data.get('Unique ID ', '').strip()  # Note the space
                courses = data.get('Courses you are currently enrolled in ', '').strip()
                learnings = data.get('  What have you learned over the past week?  ', '').strip()
                assignments = data.get('How many assignments have you completed this week?  ', '').strip()
                challenges = data.get('Are you facing any challenges or roadblocks in completing the course?  ', '').strip()
                
                # Validate required fields
                if not timestamp_str or not email or not name:
                    skipped_count += 1
                    continue
                
                # Parse timestamp
                try:
                    # Format: "4/13/2026 17:31:38"
                    timestamp = datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
                    timestamp = timezone.make_aware(timestamp)
                    date = timestamp.date()
                except ValueError:
                    print(f"⚠️  Row {row_num}: Invalid timestamp format: {timestamp_str}")
                    error_count += 1
                    continue
                
                # Calculate week number
                days_diff = (date - program_start).days
                week = max(1, (days_diff // 7) + 1)
                
                # Try to match student by email to get google_id
                google_id = ''
                try:
                    # Look for any student with this email
                    student = Student.objects.filter(email__iexact=email).first()
                    if student:
                        google_id = student.google_id
                except Exception:
                    pass
                
                # Create or update attendance record
                # Use update_or_create without expensive duplicate check
                # If duplicates exist, this will update the first one found
                AttendanceRecord.objects.update_or_create(
                    student_email=email,
                    date=date,
                    week_number=week,
                    defaults={
                        'student_name': name,
                        'student_unique_id': unique_id,
                        'google_id': google_id,
                        'city': city,
                        'cohort': target_cohort,
                        'courses_enrolled': courses,
                        'learnings': learnings,
                        'assignments_completed': assignments,
                        'challenges': challenges,
                        'timestamp': timestamp,
                    }
                )
                created_count += 1
                
            except Exception as e:
                print(f"❌ Row {row_num}: Error - {str(e)}")
                error_count += 1
                continue
        
        print("\n📊 Sync Summary:")
        print(f"✅ Created/Updated: {created_count} records")
        if skipped_count > 0:
            print(f"⚠️  Skipped: {skipped_count} records")
        if error_count > 0:
            print(f"❌ Errors: {error_count} records")
        
        return {
            'created': created_count,
            'skipped': skipped_count,
            'errors': error_count
        }
        
    except Exception as e:
        print(f"❌ Error syncing attendance: {str(e)}")
        raise
