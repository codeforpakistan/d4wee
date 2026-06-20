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

    def handle(self, *args, **options):
        user_email = options['user']
        
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('👥 Google Classroom Student Sync'))
        self.stdout.write('='*60)
        self.stdout.write(f'User: {user_email}')
        self.stdout.write(f'Mode: {"All courses"}')
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

            if email:
                try:
                    # Check if student exists
                    student = Student.objects.filter(email=email).first()
                    
                    if student:
                        # Update existing student
                        student.google_id = google_id
                        # student.email = email
                        student.full_name = full_name
                        student.given_name = given_name
                        student.family_name = family_name
                        student.photo_url = photo_url
                        student.save()
                        
                        updated_count += 1
                    else:
                        # Create new student
                        user = User.objects.filter(email=email).first()
                        student = Student.objects.create(
                            user=user,
                            google_id=google_id,
                            email=email,
                            full_name=full_name,
                            given_name=given_name,
                            family_name=family_name,
                            photo_url=photo_url,
                        )
                        created_count += 1
                    
                    self._create_enrollments(student, courses_enrolled)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error with {email}: {e}'))
                    error_count += 1
                    continue
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ No email for student with Google ID {google_id}, skipping'))
                skipped_count += 1
        
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
        students_with_accounts = Student.objects.filter(user__isnull=False).count()
        
        self.stdout.write('Current database statistics:')
        self.stdout.write(f'  Total students: {total_students}')
        self.stdout.write(f'  Students with accounts: {students_with_accounts}')
        self.stdout.write('')

    def _create_enrollments(self, student, courses):
        """
        Create Enrollment records for student in courses
        """
        # Fetch active cohort
        cohort = Cohort.objects.filter(status='ACTIVE').first()
        if not cohort:
            self.stdout.write(self.style.WARNING('  ⚠ No active cohort found, skipping enrollments'))
            return

        # Fetch registration for the student in the cohort
        registration, created = Registration.objects.get_or_create(
            student=student,
            cohort=cohort,
            defaults={'status': 'PENDING'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created registration for {student.full_name} in cohort {cohort.name}'))
        
        # Create enrollments for each course
        enrollments_created = 0
        for course in courses:
            enrollment, created = Enrollment.objects.get_or_create(
                course=course,
                registration=registration,
            )
            if created:
                enrollments_created += 1
        
        if enrollments_created > 0:
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Created {enrollments_created} enrollments for {student.full_name}')
            )