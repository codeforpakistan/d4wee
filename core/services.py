"""
Google Classroom API integration service
"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from allauth.socialaccount.models import SocialToken
from django.utils import timezone
from datetime import datetime
from .models import Course, Student, Assignment, Submission, SyncLog, StudentMetrics, AttendanceRecord


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


def sync_all_classroom_data(user):
    """
    Sync all classroom data from Google Classroom API
    Returns SyncLog instance
    """
    import gc
    sync_log = SyncLog.objects.create(status='IN_PROGRESS')
    
    try:
        service = get_classroom_service(user)
        
        # Fetch all courses
        courses_result = service.courses().list(pageSize=100).execute()
        courses_data = courses_result.get('courses', [])
        
        for course_data in courses_data:
            try:
                course, created = sync_course(course_data)
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


def sync_course(course_data):
    """Sync a single course and assign to active cohort if not already assigned"""
    from .models import Cohort
    
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
        
        # Auto-assign to active cohort if course doesn't have one
        if not course.cohort:
            active_cohort = Cohort.objects.filter(is_active=True).first()
            if active_cohort:
                course.cohort = active_cohort
                course.save()
                print(f"✅ Assigned course '{course.name}' to cohort '{active_cohort.name}'")
        
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
    # Use iterator() to avoid caching all students in memory
    students = Student.objects.filter(course=course).iterator(chunk_size=50)
    total_assignments = Assignment.objects.filter(course=course).count()
    
    if total_assignments == 0:
        return
    
    for student in students:
        submissions = Submission.objects.filter(student=student)
        
        # Calculate metrics
        completed = submissions.filter(state='TURNED_IN').count()
        completion_rate = (completed / total_assignments) * 100 if total_assignments > 0 else 0
        
        # Calculate average score as percentage
        graded_submissions = submissions.filter(
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False,
            assignment__max_points__gt=0
        ).select_related('assignment')
        
        if graded_submissions.exists():
            # Convert each grade to percentage and average them
            percentage_scores = [
                (s.assigned_grade / s.assignment.max_points) * 100 
                for s in graded_submissions
            ]
            average_score = sum(percentage_scores) / len(percentage_scores)
        else:
            average_score = None
        
        on_time = submissions.filter(late=False, state='TURNED_IN').count()
        on_time_rate = (on_time / total_assignments) * 100 if total_assignments > 0 else 0
        
        late_count = submissions.filter(late=True).count()
        missing_count = total_assignments - completed
        
        # Categorize student
        category = None
        if completion_rate < 60 or (average_score is not None and average_score < 60):
            category = 'FOCUS'
        elif completion_rate >= 85 and (average_score is None or average_score >= 85):
            category = 'PRAISE'
        else:
            category = 'PUSH'
        
        # Save metrics
        StudentMetrics.objects.update_or_create(
            student=student,
            course=course,
            defaults={
                'completion_rate': completion_rate,
                'average_score': average_score,
                'on_time_rate': on_time_rate,
                'late_submissions': late_count,
                'missing_submissions': missing_count,
                'category': category,
            }
        )
        
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


def sync_attendance_from_sheets(user, spreadsheet_id='1hWGkuHAKFT-Z6I_I5A0hML9WxLd9sU5wEIOk1WP_4F4', clear_existing=False):
    """
    Sync attendance data from Google Sheets
    
    Args:
        user: Django user with Google OAuth
        spreadsheet_id: Google Sheets spreadsheet ID
        clear_existing: If True, delete all existing attendance records before syncing
    
    Returns:
        Dictionary with sync statistics
    """
    from .models import Cohort
    
    print(f"📊 Syncing attendance from Google Sheets: {spreadsheet_id}")
    
    try:
        service = get_sheets_service(user)
        
        # Clear existing data if requested
        if clear_existing:
            count = AttendanceRecord.objects.all().count()
            AttendanceRecord.objects.all().delete()
            print(f"🗑️  Deleted {count} existing attendance records")
        
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
        
        # Get active cohort for assignment
        cohort = Cohort.objects.filter(is_active=True).first()
        if not cohort:
            cohort = Cohort.objects.order_by('-start_date').first()
        
        if cohort:
            print(f"📍 Using cohort: {cohort.name}")
            program_start = cohort.start_date
        else:
            print("⚠️  No cohort found, using default start date")
            program_start = datetime(2026, 4, 13).date()
        
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
                
                # Create or update attendance record
                # First, check if any records exist with this combination
                existing = AttendanceRecord.objects.filter(
                    student_email=email,
                    date=date,
                    week_number=week
                )
                
                if existing.count() > 1:
                    # Delete all duplicates and create fresh
                    existing.delete()
                
                # Now safely use update_or_create
                AttendanceRecord.objects.update_or_create(
                    student_email=email,
                    date=date,
                    week_number=week,
                    defaults={
                        'student_name': name,
                        'student_unique_id': unique_id,
                        'city': city,
                        'cohort': cohort,
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
