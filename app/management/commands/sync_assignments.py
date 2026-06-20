"""
Management command to sync assignments (coursework) from Google Classroom into the local database.

WHAT IT DOES:
- Connects to Google Classroom API using the specified user's credentials
- Fetches all coursework (assignments, quizzes, tests) from Google Classroom courses
- Creates new Assignment records or updates existing ones based on google_id
- Automatically categorizes assignments as PRE_TEST, POST_TEST, QUIZ, or ASSIGNMENT based on title
- Syncs all assignment metadata including due dates, points, and Google timestamps

DATA SYNCED PER ASSIGNMENT:
- google_id (unique identifier from Google)
- course (linked to Course model)
- title (assignment title)
- description (assignment instructions)
- work_type (ASSIGNMENT, SHORT_ANSWER_QUESTION, MULTIPLE_CHOICE_QUESTION)
- state (PUBLISHED, DRAFT, DELETED)
- max_points (maximum grade points)
- due_date (combined from dueDate and dueTime from Google)
- topic_id (Google Classroom topic/module ID)
- alternate_link (URL to assignment in Google Classroom)
- google_creation_time, google_update_time (timestamps from Google)
- assignment_type (AUTO-CATEGORIZED: PRE_TEST, POST_TEST, QUIZ, or ASSIGNMENT)

AUTO-CATEGORIZATION LOGIC:
- Searches title for patterns using regex:
  * "pre-test", "pre test", "pre-assessment" → PRE_TEST
  * "post-test", "post test", "post-assessment" → POST_TEST
  * "quiz" → QUIZ
  * Default → ASSIGNMENT

BEHAVIOR:
- New assignments: Creates Assignment record with auto-categorized type
- Existing assignments (with --update-existing): Updates ALL fields including re-categorization
- Existing assignments (without flag): Skipped, no changes made
- Uses google_id to match assignments (guaranteed unique by Google)

USAGE:
  python manage.py sync_assignments

EXAMPLES:
  # Sync new assignments only (skip existing):
  python manage.py sync_assignments
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from app.services import get_classroom_service
from app.models import Assignment, Course
from datetime import datetime
import re


class Command(BaseCommand):
    help = 'Sync assignments (coursework) from Google Classroom'
    
    def categorize_assignment_type(self, title):
        """
        Automatically categorize assignment type based on title
        Returns: 'PRE_TEST', 'POST_TEST', 'QUIZ', or 'ASSIGNMENT'
        """
        title_lower = title.lower()
        
        # Check for pre-test/pre-assessment
        if re.search(r'\b(pre[-\s]?(test|assessment|survey))\b', title_lower):
            return 'PRE_TEST'
        
        # Check for post-test/post-assessment
        if re.search(r'\b(post[-\s]?(test|assessment|survey))\b', title_lower):
            return 'POST_TEST'
        
        # Check for quiz
        if re.search(r'\bquiz\b', title_lower):
            return 'QUIZ'
        
        # Default to assignment
        return 'ASSIGNMENT'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='teacher@codeforpakistan.org',
            help='Email of the user to sync data for (default: teacher@codeforpakistan.org)',
        )

    def handle(self, *args, **options):
        user_email = options['user']
        
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('📚 Google Classroom Assignment Sync'))
        self.stdout.write('='*60)
        self.stdout.write(f'User: {user_email}')
        self.stdout.write('')
        
        # Get user
        try:
            user = User.objects.get(email=user_email)
            self.stdout.write(self.style.SUCCESS(f'✓ Found user: {user.email}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ User not found: {user_email}'))
            return
        
        # Get Google Classroom service
        try:
            service = get_classroom_service(user)
            self.stdout.write(self.style.SUCCESS('✓ Connected to Google Classroom API'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Failed to connect to Google Classroom: {e}'))
            return
        
        # Determine which courses to sync
        courses = Course.objects.filter(course_state='ACTIVE')
        self.stdout.write(f'✓ Found {courses.count()} ACTIVE courses')
        
        if not courses.exists():
            self.stdout.write(self.style.WARNING('⚠ No courses found to sync'))
            return
        
        self.stdout.write('')
        self.stdout.write('Syncing assignments...')
        self.stdout.write('')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        # Fetch assignments from each course
        for course in courses:
            self.stdout.write(f'  {course.display_name}...', ending=' ')
            
            try:
                # Paginate through all coursework
                coursework_list = []
                page_token = None
                
                while True:
                    result = service.courses().courseWork().list(
                        courseId=course.google_id,
                        pageSize=100,
                        pageToken=page_token
                    ).execute()
                    
                    page_coursework = result.get('courseWork', [])
                    coursework_list.extend(page_coursework)
                    
                    page_token = result.get('nextPageToken')
                    if not page_token:
                        break
                
                self.stdout.write(self.style.SUCCESS(f'✓ {len(coursework_list)} assignments'))
                
                # Process each coursework
                for cw_data in coursework_list:
                    try:
                        google_id = cw_data['id']
                        title = cw_data.get('title', 'Untitled')
                        description = cw_data.get('description', '')
                        work_type = cw_data.get('workType', 'ASSIGNMENT')
                        state = cw_data.get('state', 'PUBLISHED')
                        max_points = cw_data.get('maxPoints')
                        topic_id = cw_data.get('topicId', '')
                        alternate_link = cw_data.get('alternateLink', '')
                        
                        # Parse creation/update times
                        google_creation_time = None
                        if 'creationTime' in cw_data:
                            google_creation_time = datetime.fromisoformat(
                                cw_data['creationTime'].replace('Z', '+00:00')
                            )
                        
                        google_update_time = None
                        if 'updateTime' in cw_data:
                            google_update_time = datetime.fromisoformat(
                                cw_data['updateTime'].replace('Z', '+00:00')
                            )
                        
                        # Parse due date (combine dueDate + dueTime)
                        due_date = None
                        if 'dueDate' in cw_data:
                            date_dict = cw_data['dueDate']
                            time_dict = cw_data.get('dueTime', {})
                            
                            # Create datetime
                            year = date_dict.get('year')
                            month = date_dict.get('month')
                            day = date_dict.get('day')
                            hours = time_dict.get('hours', 23)
                            minutes = time_dict.get('minutes', 59)
                            
                            if year and month and day:
                                due_date = timezone.make_aware(
                                    datetime(year, month, day, hours, minutes)
                                )
                        
                        # Check if assignment exists
                        existing = Assignment.objects.filter(google_id=google_id).first()
                        
                        # Auto-categorize assignment type based on title
                        assignment_type = self.categorize_assignment_type(title)
                        
                        if existing:
                            # Update existing assignment
                            existing.title = title
                            existing.description = description
                            existing.work_type = work_type
                            existing.state = state
                            existing.max_points = max_points
                            existing.due_date = due_date
                            existing.topic_id = topic_id
                            existing.alternate_link = alternate_link
                            existing.google_creation_time = google_creation_time
                            existing.google_update_time = google_update_time
                            existing.assignment_type = assignment_type  # Update type based on title
                            existing.save()
                            
                            updated_count += 1
                        else:
                            # Create new assignment
                            Assignment.objects.create(
                                google_id=google_id,
                                course=course,
                                title=title,
                                description=description,
                                work_type=work_type,
                                state=state,
                                max_points=max_points,
                                due_date=due_date,
                                topic_id=topic_id,
                                alternate_link=alternate_link,
                                google_creation_time=google_creation_time,
                                google_update_time=google_update_time,
                                assignment_type=assignment_type  # Auto-categorized from title
                            )
                            created_count += 1
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'    ✗ Error with assignment "{cw_data.get("title", "unknown")}": {e}')
                        )
                        error_count += 1
                        continue
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error: {e}'))
                error_count += 1
                continue
        
        # Summary
        self.stdout.write('')
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('Sync Complete'))
        self.stdout.write('='*60)
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Updated: {updated_count}')
        self.stdout.write(f'Skipped: {skipped_count}')
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write('')
        
        # Show statistics
        total_assignments = Assignment.objects.count()       
        self.stdout.write('Current database statistics:')
        self.stdout.write(f'  Total assignments: {total_assignments}')
        self.stdout.write('')
