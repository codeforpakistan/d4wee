"""
Google Classroom API integration service
"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from allauth.socialaccount.models import SocialToken
from django.utils import timezone
from datetime import datetime
from .models import Course, Student, Assignment, Submission, SyncLog, StudentMetrics


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
    count = 0
    try:
        assignments = Assignment.objects.filter(course=course)
        
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
    students = Student.objects.filter(course=course)
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
