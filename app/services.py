"""
Google Classroom API integration service
Syncs data from Google Classroom API for active cohort
"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from allauth.socialaccount.models import SocialToken
from django.utils import timezone
from datetime import datetime
from .models import Course, Student, Assignment, Submission, SyncLog, Attendance, Registration, Enrollment


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
    Sync classroom data from Google Classroom API for target cohort
    
    Args:
        user: Django user with Google OAuth
        target_cohort: Cohort to sync data for. Must be an active cohort.
    
    Returns SyncLog instance
    """
    import gc
    
    if not target_cohort:
        raise Exception("Target cohort is required for sync")
    
    print(f"🎯 Syncing data for active cohort: {target_cohort.name}")
    
    sync_log = SyncLog.objects.create(status='IN_PROGRESS', cohort=target_cohort)
    
    try:
        service = get_classroom_service(user)
        
        # Fetch all courses
        courses_result = service.courses().list(pageSize=100).execute()
        courses_data = courses_result.get('courses', [])
        
        for course_data in courses_data:
            try:
                # Sync the course
                course, created = sync_course(course_data)
                if course:
                    sync_log.courses_synced += 1
                    
                    # Sync students for this course and create enrollments
                    students_count = sync_students(service, course, target_cohort)
                    sync_log.students_synced += students_count
                    
                    # Sync assignments for this course
                    assignments_count = sync_assignments(service, course)
                    sync_log.assignments_synced += assignments_count
                    
                    # Sync submissions for this course
                    submissions_count = sync_submissions(service, course)
                    sync_log.submissions_synced += submissions_count
                    
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
    """Sync a single course from Google Classroom"""
    try:
        # Parse timestamps
        google_creation_time = None
        google_update_time = None
        
        if 'creationTime' in course_data:
            try:
                google_creation_time = datetime.fromisoformat(
                    course_data['creationTime'].replace('Z', '+00:00')
                )
            except:
                pass
        
        if 'updateTime' in course_data:
            try:
                google_update_time = datetime.fromisoformat(
                    course_data['updateTime'].replace('Z', '+00:00')
                )
            except:
                pass
        
        course, created = Course.objects.update_or_create(
            google_id=course_data['id'],
            defaults={
                'name': course_data.get('name', ''),
                'section': course_data.get('section', ''),
                'description_heading': course_data.get('descriptionHeading', ''),
                'description': course_data.get('description', ''),
                'room': course_data.get('room', ''),
                'owner_id': course_data.get('ownerId', ''),
                'enrollment_code': course_data.get('enrollmentCode', ''),
                'course_state': course_data.get('courseState', 'ACTIVE'),
                'alternate_link': course_data.get('alternateLink', ''),
                'teacher_group_email': course_data.get('teacherGroupEmail', ''),
                'course_group_email': course_data.get('courseGroupEmail', ''),
                'guardians_enabled': course_data.get('guardiansEnabled', False),
                'calendar_id': course_data.get('calendarId', ''),
                'google_creation_time': google_creation_time,
                'google_update_time': google_update_time,
            }
        )
        
        return course, created
    except Exception as e:
        print(f"Error syncing course {course_data.get('id')}: {e}")
        return None, False


def sync_students(service, course, target_cohort):
    """Sync students for a course and create enrollments for target cohort"""
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
                given_name = profile.get('name', {}).get('givenName', '')
                family_name = profile.get('name', {}).get('familyName', '')
                email = profile.get('emailAddress', '')
                
                # Use student ID as identifier if name is hidden
                if not full_name or full_name == 'Unknown user':
                    full_name = f"Student {user_id[-8:]}"
                
                # Create or update student
                student, created = Student.objects.update_or_create(
                    google_id=user_id,
                    defaults={
                        'email': email,
                        'full_name': full_name,
                        'given_name': given_name,
                        'family_name': family_name,
                    }
                )
                
                # Create registration if doesn't exist
                registration, reg_created = Registration.objects.get_or_create(
                    student=student,
                    cohort=target_cohort,
                    defaults={'status': 'ACTIVE'}
                )
                
                # Create enrollment for this course
                Enrollment.objects.get_or_create(
                    student=student,
                    course=course,
                    cohort=target_cohort,
                    registration=registration,
                    defaults={'status': 'ACTIVE'}
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
                # Parse timestamps
                google_creation_time = parse_timestamp(work_data.get('creationTime'))
                google_update_time = parse_timestamp(work_data.get('updateTime'))
                
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
                
                # Auto-categorize assignment type based on title
                title = work_data.get('title', '')
                title_lower = title.lower()
                if 'pre' in title_lower and 'test' in title_lower:
                    assignment_type = 'PRE_TEST'
                elif 'post' in title_lower and 'test' in title_lower:
                    assignment_type = 'POST_TEST'
                elif 'quiz' in title_lower:
                    assignment_type = 'QUIZ'
                else:
                    assignment_type = 'ASSIGNMENT'
                
                Assignment.objects.update_or_create(
                    google_id=work_data['id'],
                    defaults={
                        'course': course,
                        'title': title,
                        'description': work_data.get('description', ''),
                        'work_type': work_data.get('workType', 'ASSIGNMENT'),
                        'state': work_data.get('state', 'PUBLISHED'),
                        'max_points': work_data.get('maxPoints'),
                        'due_date': due_date,
                        'topic_id': work_data.get('topicId', ''),
                        'alternate_link': work_data.get('alternateLink', ''),
                        'assignment_type': assignment_type,
                        'google_creation_time': google_creation_time,
                        'google_update_time': google_update_time,
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
                        # Find student by google_id
                        student = Student.objects.get(google_id=sub_data['userId'])
                        
                        # Find enrollment for this student and course
                        # Get any enrollment for this student and course (there might be multiple cohorts)
                        enrollment = Enrollment.objects.filter(
                            student=student,
                            course=course
                        ).first()
                        
                        if not enrollment:
                            # Skip submission if no enrollment exists
                            continue
                        
                        # Parse timestamps
                        google_creation_time = parse_timestamp(sub_data.get('creationTime'))
                        google_update_time = parse_timestamp(sub_data.get('updateTime'))
                        
                        Submission.objects.update_or_create(
                            google_id=sub_data['id'],
                            defaults={
                                'assignment': assignment,
                                'enrollment': enrollment,
                                'state': sub_data.get('state', 'NEW'),
                                'late': sub_data.get('late', False),
                                'assigned_grade': sub_data.get('assignedGrade'),
                                'draft_grade': sub_data.get('draftGrade'),
                                'alternate_link': sub_data.get('alternateLink', ''),
                                'google_creation_time': google_creation_time,
                                'google_update_time': google_update_time,
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
            count = Attendance.objects.filter(cohort=target_cohort).count()
            Attendance.objects.filter(cohort=target_cohort).delete()
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
                hours_str = data.get('How many hours do you spend daily on your course(s).   ', '').strip()
                
                # Validate required fields
                if not timestamp_str or not email:
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
                
                # Parse hours (try to extract number from string like "1-2 hours" or "3")
                hours_spent = None
                if hours_str:
                    try:
                        # Extract first number from string
                        import re
                        match = re.search(r'(\d+)', hours_str)
                        if match:
                            hours_spent = float(match.group(1))
                    except:
                        pass
                
                # Find student by email
                student = Student.objects.filter(email__iexact=email).first()
                if not student:
                    print(f"⚠️  Row {row_num}: Student not found with email: {email}")
                    skipped_count += 1
                    continue
                
                # Create or update attendance record
                Attendance.objects.update_or_create(
                    student=student,
                    cohort=target_cohort,
                    date=date,
                    defaults={
                        'hours_spent': hours_spent,
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


def generate_certificate(certificate):
    """
    Generate a certificate SVG/PDF file for a given certificate instance
    
    Args:
        certificate: Certificate model instance
    
    Returns:
        Django File object that can be saved to certificate_file field
    """
    from django.template.loader import render_to_string
    from django.core.files.base import ContentFile
    from django.conf import settings
    import os
    
    # Prepare context data for HTML certificate
    cohort = certificate.registration.cohort
    period = f"{cohort.start_date.strftime('%B %Y')} - {cohort.end_date.strftime('%B %Y')}"
    
    context = {
        'name': certificate.registration.student.full_name,
        'course': certificate.course.name if certificate.course else certificate.registration.cohort.name,
        'period': period,
    }
    
    # Load and render HTML template
    template_path = 'certificate/certificate.html'
    html_content = render_to_string(template_path, context)
    
    # Generate filename using google_id and course_id for consistency
    student_google_id = certificate.registration.student.google_id
    course_google_id = certificate.course.google_id if certificate.course else 'cohort'
    filename = f"{student_google_id}_{course_google_id}.html"
    
    # Return as ContentFile that can be saved to FileField
    return ContentFile(html_content.encode('utf-8'), name=filename)


