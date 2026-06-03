"""
Management command to sync student submissions from Google Classroom into the local database.

WHAT IT DOES:
- Connects to Google Classroom API using the specified user's credentials
- Fetches all student submissions for assignments from Google Classroom
- Creates new Submission records or updates existing ones based on google_id
- Links submissions to Student and Enrollment records (requires these to exist first)
- Syncs submission metadata including grades, state, timestamps, and late status

TWO SYNC MODES:
1. PILOT mode (--pilot):
   - Syncs submissions only from these specific courses:
     * Orientation Class - Pilot Phase
     * Basic Computer Literacy
     * AI Essentials and Prompt Engineering
     * Digital Safety & Online Security
     * Modern Digital Workspace

2. All courses mode (default):
   - Syncs submissions from all assignments in ACTIVE courses

DATA SYNCED PER SUBMISSION:
- google_id (unique identifier from Google)
- enrollment (linked to Enrollment model - student+course combination)
- assignment (linked to Assignment model)
- state (NEW, CREATED, TURNED_IN, RETURNED, RECLAIMED_BY_STUDENT)
- late (boolean - whether submission was late)
- assigned_grade (final grade assigned by teacher)
- draft_grade (draft grade not yet returned to student)
- alternate_link (URL to submission in Google Classroom)
- google_creation_time, google_update_time (timestamps from Google)

IMPORTANT PREREQUISITES:
Before running this command, you MUST have already synced:
1. Courses (python manage.py sync_courses)
2. Students (python manage.py sync_students)
3. Assignments (python manage.py sync_assignments)
4. Enrollments must exist for student+course combinations

MATCHING LOGIC:
- Finds Student by google_id (from submission's userId field)
- Finds Enrollment by matching student + assignment's course
- If Student not found: Submission skipped (increments student_not_found_count)
- If Enrollment not found: Submission skipped (increments enrollment_not_found_count)
- Uses google_id to match existing submissions (guaranteed unique by Google)

BEHAVIOR:
- New submissions: Creates Submission record linked to enrollment and assignment
- Existing submissions (with --update-existing): Updates grade, state, and timestamps
- Existing submissions (without flag): Skipped, no changes made
- Missing students/enrollments: Skipped with warning count in summary

SPECIAL OPTIONS:
- --clear: Deletes all existing submissions before syncing (DESTRUCTIVE - use with caution)
  * If used with --pilot: Only deletes submissions from PILOT course assignments
  * If used alone: Deletes ALL submissions

PERFORMANCE:
- Caches all students in memory for fast lookup by google_id
- Processes assignments sequentially with progress indicator
- Paginates through Google API results (100 per page)

USAGE:
  python manage.py sync_submissions [--pilot] [--user EMAIL] [--update-existing] [--clear]

OPTIONS:
  --pilot              Sync only submissions from PILOT cohort assignments
  --user EMAIL         Email of Google user with API access (default: teacher@codeforpakistan.org)
  --update-existing    Update existing submission records if they already exist
  --clear              Clear all submissions before syncing (DESTRUCTIVE)

EXAMPLES:
  # Sync new submissions only (skip existing):
  python manage.py sync_submissions
  
  # Sync and update all existing submissions with latest grades:
  python manage.py sync_submissions --update-existing
  
  # Sync only PILOT submissions:
  python manage.py sync_submissions --pilot --update-existing
  
  # Fresh sync - delete all and re-import (DESTRUCTIVE):
  python manage.py sync_submissions --clear --update-existing

TYPICAL WORKFLOW:
  1. python manage.py sync_courses --update-existing
  2. python manage.py sync_students --update-existing
  3. python manage.py sync_assignments --update-existing
  4. python manage.py sync_submissions --update-existing
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from app.services import get_classroom_service
from app.models import Submission, Assignment, Student, Enrollment
from datetime import datetime


class Command(BaseCommand):
    help = 'Sync student submissions from Google Classroom'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='teacher@codeforpakistan.org',
            help='Email of the user to sync data for (default: teacher@codeforpakistan.org)',
        )
        parser.add_argument(
            '--pilot',
            action='store_true',
            help='Sync PILOT cohort assignments only',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing submission records',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing submissions before syncing (fresh sync)',
        )

    def handle(self, *args, **options):
        user_email = options['user']
        pilot_only = options.get('pilot', False)
        update_existing = options.get('update_existing', False)
        clear_existing = options.get('clear', False)
        
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('📝 Google Classroom Submission Sync'))
        self.stdout.write('='*60)
        self.stdout.write(f'User: {user_email}')
        self.stdout.write(f'Mode: {"PILOT cohort only" if pilot_only else "All assignments"}')
        self.stdout.write(f'Update existing: {update_existing}')
        self.stdout.write(f'Clear before sync: {clear_existing}')
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
        
        # Clear existing data if requested
        if clear_existing:
            if pilot_only:
                pilot_assignments = Assignment.objects.filter(
                    course__name__in=[
                        'Orientation Class - Pilot Phase',
                        'Basic Computer Literacy',
                        'AI Essentials and Prompt Engineering',
                        'Digital Safety & Online Security',
                        'Modern Digital Workspace'
                    ]
                )
                deleted_count = Submission.objects.filter(assignment__in=pilot_assignments).delete()[0]
            else:
                deleted_count = Submission.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'🗑️  Cleared {deleted_count} existing submissions'))
            self.stdout.write('')
        
        # Determine which assignments to sync
        if pilot_only:
            assignments = Assignment.objects.filter(
                course__name__in=[
                    'Orientation Class - Pilot Phase',
                    'Basic Computer Literacy',
                    'AI Essentials and Prompt Engineering',
                    'Digital Safety & Online Security',
                    'Modern Digital Workspace'
                ]
            )
            self.stdout.write(f'✓ Found {assignments.count()} PILOT assignments')
        else:
            assignments = Assignment.objects.filter(course__course_state='ACTIVE')
            self.stdout.write(f'✓ Found {assignments.count()} assignments')
        
        if not assignments.exists():
            self.stdout.write(self.style.WARNING('⚠ No assignments found to sync'))
            return
        
        self.stdout.write('')
        self.stdout.write('Syncing submissions...')
        self.stdout.write('')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        student_not_found_count = 0
        enrollment_not_found_count = 0
        
        # Cache students by google_id for performance
        student_cache = {s.google_id: s for s in Student.objects.all()}
        
        # Fetch submissions for each assignment
        for idx, assignment in enumerate(assignments, 1):
            self.stdout.write(f'  [{idx}/{assignments.count()}] {assignment.title[:50]}...', ending=' ')
            
            try:
                # Paginate through all submissions
                submissions_list = []
                page_token = None
                
                while True:
                    result = service.courses().courseWork().studentSubmissions().list(
                        courseId=assignment.course.google_id,
                        courseWorkId=assignment.google_id,
                        pageSize=100,
                        pageToken=page_token
                    ).execute()
                    
                    page_submissions = result.get('studentSubmissions', [])
                    submissions_list.extend(page_submissions)
                    
                    page_token = result.get('nextPageToken')
                    if not page_token:
                        break
                
                self.stdout.write(self.style.SUCCESS(f'✓ {len(submissions_list)} submissions'))
                
                # Process each submission
                for sub_data in submissions_list:
                    try:
                        google_id = sub_data['id']
                        user_id = sub_data['userId']
                        state = sub_data.get('state', 'NEW')
                        late = sub_data.get('late', False)
                        assigned_grade = sub_data.get('assignedGrade')
                        draft_grade = sub_data.get('draftGrade')
                        alternate_link = sub_data.get('alternateLink', '')
                        
                        # Parse timestamps
                        google_creation_time = None
                        if 'creationTime' in sub_data:
                            google_creation_time = datetime.fromisoformat(
                                sub_data['creationTime'].replace('Z', '+00:00')
                            )
                        
                        google_update_time = None
                        if 'updateTime' in sub_data:
                            google_update_time = datetime.fromisoformat(
                                sub_data['updateTime'].replace('Z', '+00:00')
                            )
                        
                        # Find student by google_id (userId from submission)
                        student = student_cache.get(user_id)
                        if not student:
                            student_not_found_count += 1
                            continue
                        
                        # Find enrollment for this student and assignment's course
                        enrollment = Enrollment.objects.filter(
                            student=student,
                            course=assignment.course
                        ).first()
                        
                        if not enrollment:
                            enrollment_not_found_count += 1
                            continue
                        
                        # Check if submission exists
                        existing = Submission.objects.filter(google_id=google_id).first()
                        
                        if existing:
                            if update_existing:
                                # Update existing submission
                                existing.state = state
                                existing.late = late
                                existing.assigned_grade = assigned_grade
                                existing.draft_grade = draft_grade
                                existing.alternate_link = alternate_link
                                existing.google_creation_time = google_creation_time
                                existing.google_update_time = google_update_time
                                existing.save()
                                
                                updated_count += 1
                            else:
                                skipped_count += 1
                        else:
                            # Create new submission
                            Submission.objects.create(
                                google_id=google_id,
                                enrollment=enrollment,
                                assignment=assignment,
                                state=state,
                                late=late,
                                assigned_grade=assigned_grade,
                                draft_grade=draft_grade,
                                alternate_link=alternate_link,
                                google_creation_time=google_creation_time,
                                google_update_time=google_update_time
                            )
                            created_count += 1
                            
                    except Exception as e:
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
        if student_not_found_count > 0:
            self.stdout.write(self.style.WARNING(f'Student not found: {student_not_found_count}'))
        if enrollment_not_found_count > 0:
            self.stdout.write(self.style.WARNING(f'Enrollment not found: {enrollment_not_found_count}'))
        self.stdout.write('')
        
        # Show statistics
        total_submissions = Submission.objects.count()
        
        self.stdout.write('Current database statistics:')
        self.stdout.write(f'  Total submissions: {total_submissions}')
        self.stdout.write('')
