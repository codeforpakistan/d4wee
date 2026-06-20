"""
Management command to sync students from Google Classroom into the local database.

WHAT IT DOES:
- Connects to Google Classroom API using the specified user's credentials
- Fetches student enrollment data from Google Classroom courses
- Creates or updates Student records in the database with Google profile data
- Tracks unique students across multiple courses (deduplicates by Google ID)
- Optionally creates Enrollment and Registration records for students

TWO SYNC MODES:
1. PILOT mode (--pilot): 
   - Syncs only from these specific courses:
     * Orientation Class - Pilot Phase
     * Basic Computer Literacy
     * AI Essentials and Prompt Engineering
     * Digital Safety & Online Security
     * Modern Digital Workspace
   - Marks students as is_pilot_student=True
   - Creates Registration in "Pilot" cohort with status='COMPLETED'
   - Creates Enrollment records with status='COMPLETED' (if --create-enrollments used)

2. All courses mode (default):
   - Syncs from all ACTIVE courses in the database
   - Does NOT mark students as pilot students
   - Does NOT auto-create enrollments (students go through normal registration)

DATA SYNCED PER STUDENT:
- google_id (unique identifier from Google)
- email (from Google profile)
- full_name, given_name, family_name
- photo_url (profile picture)
- is_pilot_student flag (True if synced with --pilot)

USAGE:
  python manage.py sync_students [--pilot] [--user EMAIL] [--update-existing] [--create-enrollments]

OPTIONS:
  --pilot              Sync only PILOT cohort students (from specific courses)
  --user EMAIL         Email of Google user with API access (default: teacher@codeforpakistan.org)
  --update-existing    Update existing student records if they already exist
  --create-enrollments Create Enrollment records (only works for PILOT students)

EXAMPLES:
  # Sync all PILOT students and create their enrollments:
  python manage.py sync_students --pilot --update-existing --create-enrollments
  
  # Sync from all active courses without updating existing:
  python manage.py sync_students
  
  # Update all active course students:
  python manage.py sync_students --update-existing
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from app.services import get_classroom_service
from app.models import Student, Course, Cohort, Registration, Enrollment


class Command(BaseCommand):
    help = 'Sync students from Google Classroom'

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
            help='Sync PILOT cohort students only',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing student records',
        )
        parser.add_argument(
            '--create-enrollments',
            action='store_true',
            help='Create Enrollment records for students in courses',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        user_email = options['user']
        pilot_only = options.get('pilot', False)
        update_existing = options.get('update_existing', False)
        create_enrollments = options.get('create_enrollments', False)
        dry_run = options.get('dry_run', False)
        
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('👥 Google Classroom Student Sync'))
        self.stdout.write('='*60)
        self.stdout.write(f'User: {user_email}')
        self.stdout.write(f'Mode: {"PILOT cohort only" if pilot_only else "All courses"}')
        self.stdout.write(f'Update existing: {update_existing}')
        self.stdout.write(f'Create enrollments: {create_enrollments}')
        self.stdout.write(f'Dry run: {dry_run}')
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
        if pilot_only:
            pilot_course_names = [
                'Orientation Class - Pilot Phase',
                'Basic Computer Literacy',
                'AI Essentials and Prompt Engineering',
                'Digital Safety & Online Security',
                'Modern Digital Workspace'
            ]
            courses = Course.objects.filter(name__in=pilot_course_names)
            self.stdout.write(f'✓ Found {courses.count()} PILOT courses')
        else:
            courses = Course.objects.filter(course_state='ACTIVE')
            self.stdout.write(f'✓ Found {courses.count()} ACTIVE courses')
        
        if not courses.exists():
            self.stdout.write(self.style.WARNING('⚠ No courses found to sync'))
            return
        
        self.stdout.write('')
        self.stdout.write('Syncing students...')
        self.stdout.write('')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        # Track students and their course enrollments
        all_student_data = {}  # google_id -> {student_data, courses: []}
        
        # Fetch students from each course
        for course in courses:
            self.stdout.write(f'  Fetching from {course.display_name}...', ending=' ')
            
            try:
                # Paginate through all students
                students = []
                page_token = None
                
                while True:
                    students_result = service.courses().students().list(
                        courseId=course.google_id,
                        pageSize=100,
                        pageToken=page_token
                    ).execute()
                    
                    page_students = students_result.get('students', [])
                    students.extend(page_students)
                    
                    page_token = students_result.get('nextPageToken')
                    if not page_token:
                        break
                
                self.stdout.write(self.style.SUCCESS(f'✓ {len(students)} students'))
                
                # Process each student
                for student_data in students:
                    user_id = student_data['userId']
                    profile = student_data.get('profile', {})
                    
                    # Track unique students
                    if user_id not in all_student_data:
                        all_student_data[user_id] = {
                            'profile': profile,
                            'courses': []
                        }
                    
                    all_student_data[user_id]['courses'].append(course)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error: {e}'))
                error_count += 1
                continue
        
        self.stdout.write('')
        self.stdout.write(f'Found {len(all_student_data)} unique students')
        self.stdout.write('')
        self.stdout.write('Creating/updating student records...')
        self.stdout.write('')

        # print(all_student_data)

        # import json
        # with open("data.json", "w") as json_file:
        #     json.dump(all_student_data, json_file, indent=4)
        
        if not dry_run:
            # Create/update student records
            for google_id, data in all_student_data.items():
                profile = data['profile']
                courses_enrolled = data['courses']
                
                # Extract profile data
                name = profile.get('name', {})
                email = profile.get('emailAddress')
                full_name = name.get('fullName')
                given_name = name.get('givenName', '')
                family_name = name.get('familyName', '')
                photo_url = profile.get('photoUrl', '')
                
                try:
                    # Check if student exists
                    existing_student = Student.objects.filter(email=email).first()
                    
                    if existing_student:
                        if update_existing:
                            # Update existing student
                            existing_student.google_id = google_id
                            existing_student.email = email
                            existing_student.full_name = full_name
                            existing_student.given_name = given_name
                            existing_student.family_name = family_name
                            existing_student.photo_url = photo_url
                            if pilot_only and not existing_student.is_pilot_student:
                                existing_student.is_pilot_student = True
                            existing_student.save()
                            
                            updated_count += 1
                        else:
                            skipped_count += 1
                            student = existing_student
                    else:
                        # Create new student
                        student = Student.objects.create(
                            google_id=google_id,
                            email=email,
                            full_name=full_name,
                            given_name=given_name,
                            family_name=family_name,
                            photo_url=photo_url,
                            is_pilot_student=pilot_only
                        )
                        created_count += 1
                    
                    # Create enrollments if requested
                    if create_enrollments and existing_student:
                        student = existing_student
                    
                    if create_enrollments:
                        self._create_enrollments(student, courses_enrolled, pilot_only)
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error with {email}: {e}')
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
            
            # Show statistics
            total_students = Student.objects.count()
            pilot_students = Student.objects.filter(is_pilot_student=True).count()
            students_with_accounts = Student.objects.filter(user__isnull=False).count()
            
            self.stdout.write('Current database statistics:')
            self.stdout.write(f'  Total students: {total_students}')
            self.stdout.write(f'  PILOT students: {pilot_students}')
            self.stdout.write(f'  Students with Django accounts: {students_with_accounts}')
            self.stdout.write('')

    def _create_enrollments(self, student, courses, is_pilot):
        """
        Create Enrollment records for student in courses
        
        For PILOT students:
        - Creates/gets Registration in "Pilot" cohort with status='COMPLETED'
        - Creates Enrollment for each course with status='COMPLETED'
        
        For future students:
        - Logic TBD (will likely be manual registration)
        """
        if not is_pilot:
            # For non-PILOT students, don't auto-create enrollments
            # They go through normal registration workflow
            return
        
        # Get the PILOT cohort
        try:
            pilot_cohort = Cohort.objects.get(name='Pilot')
        except Cohort.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('  ✗ PILOT cohort not found. Run: python manage.py loaddata app/fixtures/cohorts.json')
            )
            return
        
        # Create or get Registration for student in PILOT cohort
        registration, reg_created = Registration.objects.get_or_create(
            student=student,
            cohort=pilot_cohort,
            defaults={
                'status': 'COMPLETED',  # PILOT cohort is complete
                'approved_date': timezone.now(),
                'completion_date': timezone.now(),
            }
        )
        
        # If registration already existed but wasn't completed, update it
        if not reg_created and registration.status != 'COMPLETED':
            registration.status = 'COMPLETED'
            registration.approved_date = timezone.now()
            registration.completion_date = timezone.now()
            registration.save()
        
        # Create enrollments for each course
        enrollments_created = 0
        for course in courses:
            enrollment, created = Enrollment.objects.get_or_create(
                student=student,
                course=course,
                cohort=pilot_cohort,
                registration=registration,
                defaults={
                    'status': 'COMPLETED',  # PILOT cohort is complete
                    'completion_date': timezone.now(),
                }
            )
            if created:
                enrollments_created += 1
        
        if enrollments_created > 0:
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Created {enrollments_created} enrollments for {student.full_name}')
            )
