"""
Management command to sync courses from Google Classroom into the local database.

WHAT IT DOES:
- Connects to Google Classroom API using the specified user's credentials
- Fetches all courses from the authenticated user's Google Classroom account
- Creates new Course records or updates existing ones based on google_id (unique identifier)
- Syncs all course metadata from Google Classroom API

DATA SYNCED PER COURSE:
- google_id (unique identifier from Google)
- name (course name)
- section (course section)
- description_heading, description (course descriptions)
- room (classroom location)
- owner_id (Google ID of course owner)
- enrollment_code (student enrollment code)
- course_state (ACTIVE, ARCHIVED, PROVISIONED, DECLINED, SUSPENDED)
- alternate_link (URL to course in Google Classroom)
- teacher_group_email, course_group_email
- guardians_enabled (whether guardians can receive summaries)
- calendar_id (associated Google Calendar)
- google_creation_time, google_update_time (timestamps from Google)
- is_visible (set to True by default for new courses)

BEHAVIOR:
- New courses: Creates Course record with all Google Classroom data
- Existing courses (with --update-existing): Updates ALL fields from Google Classroom
- Existing courses (without flag): Skipped, no changes made
- Uses google_id to match courses (guaranteed unique by Google)

USAGE:
  python manage.py sync_courses [--user EMAIL] [--update-existing] [--set-active]

OPTIONS:
  --user EMAIL         Email of Google user with API access (default: teacher@codeforpakistan.org)
  --update-existing    Update existing course records if they already exist in database
  --set-active         Force all synced courses to ACTIVE status (overrides Google's course_state)

EXAMPLES:
  # Sync new courses only (skip existing):
  python manage.py sync_courses
  
  # Sync and update all existing courses:
  python manage.py sync_courses --update-existing
  
  # Sync and force all to ACTIVE status:
  python manage.py sync_courses --update-existing --set-active
  
  # Use different Google account:
  python manage.py sync_courses --user admin@example.org --update-existing
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.services import get_classroom_service
from app.models import Course
from datetime import datetime


class Command(BaseCommand):
    help = 'Sync courses from Google Classroom'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='teacher@codeforpakistan.org',
            help='Email of the user to sync data for (default: teacher@codeforpakistan.org)',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing courses (name, description). Code remains unchanged.',
        )
        parser.add_argument(
            '--set-active',
            action='store_true',
            help='Set all synced courses to ACTIVE status',
        )

    def handle(self, *args, **options):
        user_email = options['user']
        update_existing = options.get('update_existing', False)
        set_active = options.get('set_active', False)
        
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('📚 Google Classroom Course Sync'))
        self.stdout.write('='*60)
        self.stdout.write(f'User: {user_email}')
        self.stdout.write(f'Update existing: {update_existing}')
        self.stdout.write(f'Set active: {set_active}')
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
        
        # Fetch courses from Google Classroom
        self.stdout.write('')
        self.stdout.write('Fetching courses from Google Classroom...')
        
        try:
            courses_result = service.courses().list(pageSize=100).execute()
            classroom_courses = courses_result.get('courses', [])
            
            if not classroom_courses:
                self.stdout.write(self.style.WARNING('⚠ No courses found in Google Classroom'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'✓ Found {len(classroom_courses)} courses in Google Classroom'))
            self.stdout.write('')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Failed to fetch courses: {e}'))
            return
        
        # Sync courses
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        self.stdout.write('Syncing courses...')
        self.stdout.write('')
        
        for classroom_course in classroom_courses:
            try:
                google_id = classroom_course.get('id')
                name = classroom_course.get('name', 'Untitled Course')
                description = classroom_course.get('descriptionHeading', '') or classroom_course.get('description', '')
                course_state = classroom_course.get('courseState', 'ACTIVE')
                
                # Parse timestamps
                creation_time = classroom_course.get('creationTime')
                update_time = classroom_course.get('updateTime')
                google_creation_time = None
                google_update_time = None
                
                if creation_time:
                    try:
                        google_creation_time = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                    except:
                        pass
                
                if update_time:
                    try:
                        google_update_time = datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Check if course already exists
                existing_course = Course.objects.filter(google_id=google_id).first()
                
                if existing_course:
                    if update_existing:
                        # Update existing course with ALL fields
                        existing_course.name = name
                        existing_course.section = classroom_course.get('section', '')
                        existing_course.description_heading = classroom_course.get('descriptionHeading', '')
                        existing_course.description = classroom_course.get('description', '')
                        existing_course.room = classroom_course.get('room', '')
                        existing_course.owner_id = classroom_course.get('ownerId', '')
                        existing_course.enrollment_code = classroom_course.get('enrollmentCode', '')
                        existing_course.alternate_link = classroom_course.get('alternateLink', '')
                        existing_course.teacher_group_email = classroom_course.get('teacherGroupEmail', '')
                        existing_course.course_group_email = classroom_course.get('courseGroupEmail', '')
                        existing_course.guardians_enabled = classroom_course.get('guardiansEnabled', False)
                        existing_course.calendar_id = classroom_course.get('calendarId', '')
                        existing_course.google_creation_time = google_creation_time
                        existing_course.google_update_time = google_update_time
                        
                        # Update status if set_active flag is used
                        if set_active:
                            existing_course.course_state = 'ACTIVE'
                        else:
                            existing_course.course_state = course_state
                        
                        existing_course.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Updated: {name}')
                        )
                        updated_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'  ⏭ Skipped (exists): {name}')
                        )
                        skipped_count += 1
                else:
                    # Create new course with ALL Google Classroom fields
                    # Determine status
                    if set_active:
                        status = 'ACTIVE'
                    else:
                        status = course_state
                    
                    course = Course.objects.create(
                        google_id=google_id,
                        name=name,
                        section=classroom_course.get('section', ''),
                        description_heading=classroom_course.get('descriptionHeading', ''),
                        description=classroom_course.get('description', ''),
                        room=classroom_course.get('room', ''),
                        owner_id=classroom_course.get('ownerId', ''),
                        enrollment_code=classroom_course.get('enrollmentCode', ''),
                        course_state=status,
                        alternate_link=classroom_course.get('alternateLink', ''),
                        teacher_group_email=classroom_course.get('teacherGroupEmail', ''),
                        course_group_email=classroom_course.get('courseGroupEmail', ''),
                        guardians_enabled=classroom_course.get('guardiansEnabled', False),
                        calendar_id=classroom_course.get('calendarId', ''),
                        google_creation_time=google_creation_time,
                        google_update_time=google_update_time,
                        is_visible=True,
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Created: {name}')
                    )
                    created_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error syncing "{name}": {e}')
                )
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
        
        # Show all courses
        if created_count > 0 or updated_count > 0:
            self.stdout.write('Current courses in database:')
            for course in Course.objects.filter(google_id__isnull=False).order_by('name'):
                status_color = {
                    'ACTIVE': self.style.SUCCESS,
                    'PROVISIONED': self.style.WARNING,
                    'ARCHIVED': lambda x: x,
                    'DECLINED': lambda x: x,
                    'SUSPENDED': lambda x: x,
                }
                display_name = course.display_name
                self.stdout.write(
                    f'  {display_name:50} | {status_color.get(course.course_state, lambda x: x)(course.course_state)}'
                )

