"""
Management command to sync historical data from Google Classroom
This is a ONE-TIME migration command to populate the database with existing data

Usage: 
    python manage.py sync_old_data [--user EMAIL] [--fetch-only] [--import-only]

This command runs after initial setup (migrate → seed) to bring in historical data.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.services import get_classroom_service, get_sheets_service
from app.models import Course, Cohort, Student, Assignment, Submission, Attendance
from pathlib import Path
import json
import os


class Command(BaseCommand):
    help = 'ONE-TIME command to sync historical Google Classroom data to populate new database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='teacher@codeforpakistan.org',
            help='Email of the user to sync data for (default: teacher@codeforpakistan.org)',
        )
        parser.add_argument(
            '--fetch-only',
            action='store_true',
            help='Only fetch data from Google Classroom to JSON files, do not import',
        )
        parser.add_argument(
            '--import-only',
            action='store_true',
            help='Only import from existing JSON files, do not fetch new data',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all app data before syncing (preserves OAuth tokens and admin user)',
        )

    def handle(self, *args, **options):
        user_email = options['user']
        fetch_only = options.get('fetch_only', False)
        import_only = options.get('import_only', False)
        clear_data = options.get('clear', False)
        
        if fetch_only and import_only:
            self.stdout.write(self.style.ERROR('❌ Cannot use both --fetch-only and --import-only'))
            return
        
        self.stdout.write('\n' + '╔' + '='*78 + '╗')
        self.stdout.write('║' + ' '*20 + 'D4WEE HISTORICAL DATA MIGRATION' + ' '*27 + '║')
        self.stdout.write('╚' + '='*78 + '╝\n')
        
        self.stdout.write(self.style.WARNING('⚠️  This is a ONE-TIME migration command for initial database setup'))
        self.stdout.write('   Use only when setting up a fresh database with historical data\n')
        
        # Get user
        try:
            user = User.objects.get(email=user_email)
            self.stdout.write(self.style.SUCCESS(f'✅ Found user: {user.email}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User not found: {user_email}'))
            self.stdout.write('   Please authenticate via /accounts/login/ first')
            return
        
        # Clear app data if requested
        if clear_data:
            self.stdout.write('\n' + '='*80)
            self.stdout.write('🗑️  CLEARING APP DATA')
            self.stdout.write('='*80)
            self.clear_app_data()
        
        # Create data directory
        data_dir = Path(__file__).resolve().parent.parent.parent.parent / 'data'
        data_dir.mkdir(exist_ok=True)
        
        # STEP 1: FETCH DATA
        if not import_only:
            self.stdout.write('\n' + '='*80)
            self.stdout.write('📥 STEP 1: FETCHING DATA FROM GOOGLE CLASSROOM')
            self.stdout.write('='*80 + '\n')
            
            try:
                service = get_classroom_service(user)
                self.stdout.write(self.style.SUCCESS('✅ Connected to Google Classroom API\n'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Failed to connect to Google Classroom: {e}'))
                return
            
            # Fetch courses
            self.fetch_courses(service, data_dir)
            
            # Fetch students
            self.fetch_students(service, data_dir)
            
            # Fetch assignments
            self.fetch_assignments(service, data_dir)
            
            # Fetch submissions (sample)
            self.fetch_submissions(service, data_dir)
            
            # Fetch attendance from Google Sheets
            try:
                sheets_service = get_sheets_service(user)
                self.fetch_attendance(sheets_service, data_dir)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️  Could not fetch attendance: {e}'))
        
        if fetch_only:
            self.stdout.write('\n' + '='*80)
            self.stdout.write(self.style.SUCCESS('✅ FETCH COMPLETE'))
            self.stdout.write(f'   Data saved to: {data_dir}/')
            self.stdout.write('='*80 + '\n')
            return
        
        # STEP 2: IMPORT DATA
        self.stdout.write('\n' + '='*80)
        self.stdout.write('📤 STEP 2: IMPORTING DATA TO DATABASE')
        self.stdout.write('='*80 + '\n')
        
        # Import courses
        self.import_courses(data_dir)
        
        # Import students
        self.import_students(data_dir)
        
        # Import enrollments (create enrollments from student-course data)
        self.import_enrollments(data_dir)
        
        # Import assignments
        self.import_assignments(data_dir)
        
        # Import submissions
        self.import_submissions(data_dir)
        
        # Import attendance
        self.import_attendance(data_dir)
        
        # STEP 3: VERIFICATION
        self.stdout.write('\n' + '='*80)
        self.stdout.write('🔍 STEP 3: VERIFICATION')
        self.stdout.write('='*80 + '\n')
        
        self.verify_import(data_dir)
        
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('✅ MIGRATION COMPLETE'))
        self.stdout.write('='*80 + '\n')

    def clear_app_data(self):
        """Clear all app data while preserving OAuth tokens and admin user"""
        from app.models import Enrollment, Registration, Submission, Attendance, Assignment
        
        # Delete in order of dependencies
        deleted_submissions = Submission.objects.all().delete()[0]
        deleted_attendance = Attendance.objects.all().delete()[0]
        deleted_enrollments = Enrollment.objects.all().delete()[0]
        deleted_registrations = Registration.objects.all().delete()[0]
        deleted_assignments = Assignment.objects.all().delete()[0]
        deleted_students = Student.objects.all().delete()[0]
        deleted_courses = Course.objects.all().delete()[0]
        
        self.stdout.write(f'   Deleted: {deleted_submissions} submissions')
        self.stdout.write(f'   Deleted: {deleted_attendance} attendance records')
        self.stdout.write(f'   Deleted: {deleted_enrollments} enrollments')
        self.stdout.write(f'   Deleted: {deleted_registrations} registrations')
        self.stdout.write(f'   Deleted: {deleted_assignments} assignments')
        self.stdout.write(f'   Deleted: {deleted_students} students')
        self.stdout.write(f'   Deleted: {deleted_courses} courses')
        self.stdout.write(self.style.SUCCESS('   ✅ App data cleared (OAuth tokens preserved)'))

    def fetch_courses(self, service, data_dir):
        """Fetch all courses from Google Classroom"""
        self.stdout.write('▶ Fetching courses...', ending=' ')
        
        try:
            # Fetch all pages of courses
            courses = []
            page_token = None
            
            while True:
                result = service.courses().list(
                    pageSize=100,
                    pageToken=page_token
                ).execute()
                
                page_courses = result.get('courses', [])
                courses.extend(page_courses)
                
                page_token = result.get('nextPageToken')
                if not page_token:
                    break
            
            # Save to JSON
            courses_file = data_dir / 'google_classroom_courses.json'
            with open(courses_file, 'w', encoding='utf-8') as f:
                json.dump(courses, f, indent=2, ensure_ascii=False, default=str)
            
            self.stdout.write(self.style.SUCCESS(f'✅ {len(courses)} courses'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def fetch_students(self, service, data_dir):
        """Fetch all students from all courses"""
        self.stdout.write('▶ Fetching students...', ending=' ')
        
        try:
            # Read courses from JSON file we just created
            courses_file = data_dir / 'google_classroom_courses.json'
            if not courses_file.exists():
                self.stdout.write(self.style.WARNING('⚠️  No courses file found, skipping'))
                return
            
            with open(courses_file, 'r', encoding='utf-8') as f:
                all_courses = json.load(f)
            
            # Filter for PILOT courses
            pilot_course_names = [
                'Orientation Class - Pilot Phase',
                'Basic Computer Literacy',
                'AI Essentials and Prompt Engineering',
                'Digital Safety & Online Security',
                'Modern Digital Workspace'
            ]
            
            pilot_courses = [c for c in all_courses if c.get('name') in pilot_course_names]
            
            all_students = {}
            total_count = 0
            
            for course in pilot_courses:
                course_id = course['id']
                course_name = course.get('name', 'Unknown')
                
                try:
                    students = []
                    page_token = None
                    
                    while True:
                        result = service.courses().students().list(
                            courseId=course_id,
                            pageSize=100,
                            pageToken=page_token
                        ).execute()
                        
                        page_students = result.get('students', [])
                        students.extend(page_students)
                        
                        page_token = result.get('nextPageToken')
                        if not page_token:
                            break
                    
                    total_count += len(students)
                    
                    # Collect unique students
                    for student in students:
                        user_id = student['userId']
                        if user_id not in all_students:
                            all_students[user_id] = student
                            all_students[user_id]['courses_enrolled'] = []
                        
                        all_students[user_id]['courses_enrolled'].append({
                            'course_id': course_id,
                            'course_name': course_name,
                        })
                
                except Exception:
                    continue
            
            # Save to JSON
            students_file = data_dir / 'all_students.json'
            students_list = list(all_students.values())
            
            with open(students_file, 'w', encoding='utf-8') as f:
                json.dump(students_list, f, indent=2, ensure_ascii=False, default=str)
            
            self.stdout.write(self.style.SUCCESS(f'✅ {len(all_students)} unique students ({total_count} enrollments)'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def fetch_assignments(self, service, data_dir):
        """Fetch all assignments from PILOT courses"""
        self.stdout.write('▶ Fetching assignments...', ending=' ')
        
        try:
            # Read courses from JSON file
            courses_file = data_dir / 'google_classroom_courses.json'
            if not courses_file.exists():
                self.stdout.write(self.style.WARNING('⚠️  No courses file found, skipping'))
                return
            
            with open(courses_file, 'r', encoding='utf-8') as f:
                all_courses = json.load(f)
            
            # Filter for PILOT courses
            pilot_course_names = [
                'Orientation Class - Pilot Phase',
                'Basic Computer Literacy',
                'AI Essentials and Prompt Engineering',
                'Digital Safety & Online Security',
                'Modern Digital Workspace'
            ]
            
            pilot_courses = [c for c in all_courses if c.get('name') in pilot_course_names]
            
            all_coursework = []
            
            for course in pilot_courses:
                course_id = course['id']
                course_name = course.get('name', 'Unknown')
                
                try:
                    coursework = []
                    page_token = None
                    
                    while True:
                        result = service.courses().courseWork().list(
                            courseId=course_id,
                            pageSize=100,
                            pageToken=page_token
                        ).execute()
                        
                        page_coursework = result.get('courseWork', [])
                        coursework.extend(page_coursework)
                        
                        page_token = result.get('nextPageToken')
                        if not page_token:
                            break
                    
                    # Add course reference
                    for cw in coursework:
                        cw['course_name'] = course_name
                        cw['course_id'] = course_id
                        all_coursework.append(cw)
                
                except Exception:
                    continue
            
            # Save to JSON
            assignments_file = data_dir / 'pilot_assignments.json'
            with open(assignments_file, 'w', encoding='utf-8') as f:
                json.dump(all_coursework, f, indent=2, ensure_ascii=False, default=str)
            
            self.stdout.write(self.style.SUCCESS(f'✅ {len(all_coursework)} assignments'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def fetch_submissions(self, service, data_dir):
        """Fetch ALL submissions from ALL pilot assignments"""
        self.stdout.write('▶ Fetching submissions...', ending=' ')
        
        try:
            # Load assignments to get IDs
            assignments_file = data_dir / 'pilot_assignments.json'
            if not assignments_file.exists():
                self.stdout.write(self.style.WARNING('⚠️  No assignments file found, skipping'))
                return
            
            with open(assignments_file, 'r', encoding='utf-8') as f:
                assignments = json.load(f)
            
            # Fetch submissions for ALL assignments (not just samples)
            all_submissions = []
            
            for assignment in assignments:  # ALL assignments, not [:3]
                try:
                    course_id = assignment['courseId']
                    assignment_id = assignment['id']
                    
                    submissions = []
                    page_token = None
                    
                    while True:
                        result = service.courses().courseWork().studentSubmissions().list(
                            courseId=course_id,
                            courseWorkId=assignment_id,
                            pageSize=100,
                            pageToken=page_token
                        ).execute()
                        
                        page_submissions = result.get('studentSubmissions', [])
                        submissions.extend(page_submissions)
                        
                        page_token = result.get('nextPageToken')
                        if not page_token:
                            break
                    
                    # Save ALL submissions with assignment info
                    for sub in submissions:
                        sub['assignment_title'] = assignment.get('title', 'Unknown')
                        sub['course_name'] = assignment.get('course_name', 'Unknown')
                        all_submissions.append(sub)
                        
                except Exception:
                    continue
            
            # Save to JSON
            submissions_file = data_dir / 'pilot_submissions.json'
            with open(submissions_file, 'w', encoding='utf-8') as f:
                json.dump(all_submissions, f, indent=2, ensure_ascii=False, default=str)
            
            self.stdout.write(self.style.SUCCESS(f'✅ {len(all_submissions)} submissions'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def fetch_attendance(self, service, data_dir):
        """Fetch attendance data from Google Sheets"""
        self.stdout.write('▶ Fetching attendance from Google Sheets...', ending=' ')
        
        try:
            # PILOT attendance spreadsheet ID
            spreadsheet_id = '1hWGkuHAKFT-Z6I_I5A0hML9WxLd9sU5wEIOk1WP_4F4'
            range_name = 'Form Responses 1!A:K'
            
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                self.stdout.write(self.style.WARNING('⚠️  No data found'))
                return
            
            # Convert to list of dictionaries
            headers = values[0]
            attendance_data = []
            
            for row in values[1:]:
                # Pad row if needed
                while len(row) < len(headers):
                    row.append('')
                
                record = dict(zip(headers, row))
                attendance_data.append(record)
            
            # Save to JSON
            attendance_file = data_dir / 'pilot_attendance.json'
            with open(attendance_file, 'w', encoding='utf-8') as f:
                json.dump(attendance_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(self.style.SUCCESS(f'✅ {len(attendance_data)} attendance records'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def import_courses(self, data_dir):
        """Import courses from JSON to database"""
        self.stdout.write('▶ Importing courses...', ending=' ')
        
        try:
            courses_file = data_dir / 'google_classroom_courses.json'
            if not courses_file.exists():
                self.stdout.write(self.style.WARNING('⚠️  No courses file found'))
                return
            
            with open(courses_file, 'r', encoding='utf-8') as f:
                courses_data = json.load(f)
            
            created = 0
            updated = 0
            
            for course_data in courses_data:
                google_id = course_data.get('id')
                name = course_data.get('name', 'Untitled')
                
                # Parse timestamps
                from datetime import datetime
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
                
                # Create or update course
                course, is_created = Course.objects.update_or_create(
                    google_id=google_id,
                    defaults={
                        'name': name,
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
                
                if is_created:
                    created += 1
                else:
                    updated += 1
            
            self.stdout.write(self.style.SUCCESS(f'✅ {created} created, {updated} updated'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def import_students(self, data_dir):
        """Import students from JSON to database"""
        self.stdout.write('▶ Importing students...', ending=' ')
        
        try:
            students_file = data_dir / 'all_students.json'
            if not students_file.exists():
                self.stdout.write(self.style.WARNING('⚠️  No students file found'))
                return
            
            with open(students_file, 'r', encoding='utf-8') as f:
                students_data = json.load(f)
            
            created = 0
            updated = 0
            
            for student_data in students_data:
                google_id = student_data.get('userId')
                profile = student_data.get('profile', {})
                
                # Extract profile data
                name = profile.get('name', {})
                email = profile.get('emailAddress', f'student_{google_id}@unknown.com')
                full_name = name.get('fullName', 'Unknown Student')
                given_name = name.get('givenName', '')
                family_name = name.get('familyName', '')
                photo_url = profile.get('photoUrl', '')
                
                # Create or update student
                student, is_created = Student.objects.update_or_create(
                    google_id=google_id,
                    defaults={
                        'email': email,
                        'full_name': full_name,
                        'given_name': given_name,
                        'family_name': family_name,
                        'photo_url': photo_url,
                    }
                )
                
                if is_created:
                    created += 1
                else:
                    updated += 1
            
            self.stdout.write(self.style.SUCCESS(f'✅ {created} created, {updated} updated'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def import_enrollments(self, data_dir):
        """Create registrations and enrollments from student-course relationships"""
        self.stdout.write('▶ Importing enrollments...', ending=' ')
        
        try:
            from app.models import Enrollment, Registration
            
            students_file = data_dir / 'all_students.json'
            if not students_file.exists():
                self.stdout.write(self.style.WARNING('⚠️  No students file found'))
                return
            
            with open(students_file, 'r', encoding='utf-8') as f:
                students_data = json.load(f)
            
            # Get Pilot cohort
            try:
                pilot_cohort = Cohort.objects.get(name='Pilot')
            except Cohort.DoesNotExist:
                self.stdout.write(self.style.ERROR('❌ Pilot cohort not found'))
                return
            
            created = 0
            skipped = 0
            
            # Cache for lookups
            student_cache = {s.google_id: s for s in Student.objects.all()}
            course_cache = {c.google_id: c for c in Course.objects.all()}
            registrations_cache = {}  # student_id -> registration
            
            for student_data in students_data:
                user_id = student_data.get('userId')
                courses_enrolled = student_data.get('courses_enrolled', [])
                
                if not user_id or not courses_enrolled:
                    skipped += 1
                    continue
                
                # Find student
                student = student_cache.get(user_id)
                if not student:
                    skipped += 1
                    continue
                
                # Get or create registration for this student in Pilot cohort
                if student.id not in registrations_cache:
                    registration, _ = Registration.objects.get_or_create(
                        student=student,
                        cohort=pilot_cohort,
                        defaults={
                            'status': 'ACTIVE',
                            'requested_date': pilot_cohort.start_date,
                        }
                    )
                    registrations_cache[student.id] = registration
                else:
                    registration = registrations_cache[student.id]
                
                # Create enrollment for EACH course this student is enrolled in
                for course_enrollment in courses_enrolled:
                    course_id = course_enrollment.get('course_id')
                    if not course_id:
                        continue
                    
                    course = course_cache.get(course_id)
                    if not course:
                        continue
                    
                    # Create enrollment
                    _, is_created = Enrollment.objects.get_or_create(
                        student=student,
                        course=course,
                        cohort=pilot_cohort,
                        defaults={
                            'registration': registration,
                            'status': 'IN_PROGRESS',
                        }
                    )
                    
                    if is_created:
                        created += 1
            
            msg = f'✅ {created} created'
            if skipped > 0:
                msg += f', {skipped} skipped'
            self.stdout.write(self.style.SUCCESS(msg))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def import_assignments(self, data_dir):
        """Import assignments from JSON to database"""
        self.stdout.write('▶ Importing assignments...', ending=' ')
        
        try:
            assignments_file = data_dir / 'pilot_assignments.json'
            if not assignments_file.exists():
                self.stdout.write(self.style.WARNING('⚠️  No assignments file found'))
                return
            
            with open(assignments_file, 'r', encoding='utf-8') as f:
                assignments_data = json.load(f)
            
            created = 0
            updated = 0
            skipped = 0
            
            from datetime import datetime
            from django.utils import timezone as tz
            
            for assignment_data in assignments_data:
                google_id = assignment_data.get('id')
                course_id = assignment_data.get('courseId')
                
                # Find the course
                try:
                    course = Course.objects.get(google_id=course_id)
                except Course.DoesNotExist:
                    skipped += 1
                    continue
                
                # Parse timestamps
                google_creation_time = None
                google_update_time = None
                
                if 'creationTime' in assignment_data:
                    try:
                        google_creation_time = datetime.fromisoformat(
                            assignment_data['creationTime'].replace('Z', '+00:00')
                        )
                    except:
                        pass
                
                if 'updateTime' in assignment_data:
                    try:
                        google_update_time = datetime.fromisoformat(
                            assignment_data['updateTime'].replace('Z', '+00:00')
                        )
                    except:
                        pass
                
                # Parse due date
                due_date = None
                if 'dueDate' in assignment_data:
                    date_dict = assignment_data['dueDate']
                    time_dict = assignment_data.get('dueTime', {})
                    
                    year = date_dict.get('year')
                    month = date_dict.get('month')
                    day = date_dict.get('day')
                    hours = time_dict.get('hours', 23)
                    minutes = time_dict.get('minutes', 59)
                    
                    if year and month and day:
                        try:
                            due_date = tz.make_aware(
                                datetime(year, month, day, hours, minutes)
                            )
                        except:
                            pass
                
                # Create or update assignment
                assignment, is_created = Assignment.objects.update_or_create(
                    google_id=google_id,
                    defaults={
                        'course': course,
                        'title': assignment_data.get('title', 'Untitled'),
                        'description': assignment_data.get('description', ''),
                        'work_type': assignment_data.get('workType', 'ASSIGNMENT'),
                        'state': assignment_data.get('state', 'PUBLISHED'),
                        'max_points': assignment_data.get('maxPoints'),
                        'due_date': due_date,
                        'topic_id': assignment_data.get('topicId', ''),
                        'alternate_link': assignment_data.get('alternateLink', ''),
                        'google_creation_time': google_creation_time,
                        'google_update_time': google_update_time,
                    }
                )
                
                if is_created:
                    created += 1
                else:
                    updated += 1
            
            msg = f'✅ {created} created, {updated} updated'
            if skipped > 0:
                msg += f', {skipped} skipped'
            self.stdout.write(self.style.SUCCESS(msg))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def import_submissions(self, data_dir):
        """Import submissions from JSON to database"""
        self.stdout.write('▶ Importing submissions...', ending=' ')
        
        try:
            from app.models import Enrollment
            
            submissions_file = data_dir / 'pilot_submissions.json'
            if not submissions_file.exists():
                self.stdout.write(self.style.WARNING('⚠️  No submissions file found'))
                return
            
            with open(submissions_file, 'r', encoding='utf-8') as f:
                submissions_data = json.load(f)
            
            created = 0
            updated = 0
            skipped = 0
            skip_reasons = {'no_student': 0, 'no_assignment': 0, 'no_enrollment': 0}
            
            from datetime import datetime
            
            # Cache students and assignments for performance
            student_cache = {s.google_id: s for s in Student.objects.all()}
            assignment_cache = {a.google_id: a for a in Assignment.objects.all()}
            
            for sub_data in submissions_data:
                try:
                    google_id = sub_data.get('id')
                    user_id = sub_data.get('userId')
                    course_work_id = sub_data.get('courseWorkId')
                    
                    if not google_id or not user_id or not course_work_id:
                        skipped += 1
                        continue
                    
                    # Find student
                    student = student_cache.get(user_id)
                    if not student:
                        skip_reasons['no_student'] += 1
                        skipped += 1
                        continue
                    
                    # Find assignment
                    assignment = assignment_cache.get(course_work_id)
                    if not assignment:
                        skip_reasons['no_assignment'] += 1
                        skipped += 1
                        continue
                    
                    # Find enrollment
                    enrollment = Enrollment.objects.filter(
                        student=student,
                        course=assignment.course
                    ).first()
                    
                    if not enrollment:
                        skip_reasons['no_enrollment'] += 1
                        skipped += 1
                        continue
                    
                    # Parse timestamps
                    google_creation_time = None
                    if 'creationTime' in sub_data:
                        try:
                            google_creation_time = datetime.fromisoformat(
                                sub_data['creationTime'].replace('Z', '+00:00')
                            )
                        except:
                            pass
                    
                    google_update_time = None
                    if 'updateTime' in sub_data:
                        try:
                            google_update_time = datetime.fromisoformat(
                                sub_data['updateTime'].replace('Z', '+00:00')
                            )
                        except:
                            pass
                    
                    # Create or update submission
                    submission, is_created = Submission.objects.update_or_create(
                        google_id=google_id,
                        defaults={
                            'enrollment': enrollment,
                            'assignment': assignment,
                            'state': sub_data.get('state', 'NEW'),
                            'late': sub_data.get('late', False),
                            'assigned_grade': sub_data.get('assignedGrade'),
                            'draft_grade': sub_data.get('draftGrade'),
                            'alternate_link': sub_data.get('alternateLink', ''),
                            'google_creation_time': google_creation_time,
                            'google_update_time': google_update_time,
                        }
                    )
                    
                    if is_created:
                        created += 1
                    else:
                        updated += 1
                        
                except Exception:
                    skipped += 1
                    continue
            
            msg = f'✅ {created} created, {updated} updated'
            if skipped > 0:
                msg += f', {skipped} skipped'
                if skip_reasons['no_enrollment'] > 0:
                    msg += f' ({skip_reasons["no_enrollment"]} no enrollment)'
            self.stdout.write(self.style.SUCCESS(msg))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def import_attendance(self, data_dir):
        """Import attendance from JSON to database"""
        self.stdout.write('▶ Importing attendance...', ending=' ')
        
        try:
            attendance_file = data_dir / 'pilot_attendance.json'
            if not attendance_file.exists():
                self.stdout.write(self.style.WARNING('⚠️  No attendance file found'))
                return
            
            with open(attendance_file, 'r', encoding='utf-8') as f:
                attendance_data = json.load(f)
            
            created = 0
            skipped = 0
            skip_reasons = {'no_email': 0, 'no_timestamp': 0, 'bad_date': 0, 'no_student': 0, 'no_cohort': 0}
            unmatched_emails = []  # Track emails that don't match any student
            
            from datetime import datetime
            
            # Get Pilot cohort once
            try:
                cohort = Cohort.objects.get(name='Pilot')
            except Cohort.DoesNotExist:
                self.stdout.write(self.style.ERROR('❌ Pilot cohort not found'))
                return
            
            for record in attendance_data:
                # Extract data from Google Form response
                timestamp_str = record.get('Timestamp', '').strip()
                email = record.get('Email Address', '').strip()
                hours_daily_str = record.get('How many hours do you spend daily on your course(s).   ', '').strip()
                
                if not email:
                    skip_reasons['no_email'] += 1
                    skipped += 1
                    continue
                
                if not timestamp_str:
                    skip_reasons['no_timestamp'] += 1
                    skipped += 1
                    continue
                
                # Parse timestamp to get date
                try:
                    dt = datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
                    date = dt.date()
                except:
                    skip_reasons['bad_date'] += 1
                    skipped += 1
                    continue
                
                # Find student by email (case-insensitive)
                try:
                    student = Student.objects.get(email__iexact=email)
                except Student.DoesNotExist:
                    skip_reasons['no_student'] += 1
                    skipped += 1
                    if email not in unmatched_emails:
                        unmatched_emails.append(email)
                    continue
                
                # Parse hours (if provided)
                hours_spent = None
                if hours_daily_str:
                    try:
                        hours_spent = float(hours_daily_str)
                    except (ValueError, TypeError):
                        pass
                
                # Create or update attendance record
                _, is_created = Attendance.objects.update_or_create(
                    student=student,
                    cohort=cohort,
                    date=date,
                    defaults={
                        'hours_spent': hours_spent,
                    }
                )
                
                if is_created:
                    created += 1
            
            msg = f'✅ {created} created'
            if skipped > 0:
                msg += f', {skipped} skipped'
                if skip_reasons['no_student'] > 0:
                    msg += f' ({skip_reasons["no_student"]} no student match)'
            self.stdout.write(self.style.SUCCESS(msg))
            
            # Log unmatched emails to file for cleanup
            if unmatched_emails:
                unmatched_file = data_dir / 'attendance_unmatched_emails.txt'
                with open(unmatched_file, 'w', encoding='utf-8') as f:
                    f.write(f'# Unmatched emails in attendance data ({len(unmatched_emails)} unique)\n')
                    f.write(f'# These emails submitted attendance but are not in the student database\n\n')
                    for email in sorted(unmatched_emails):
                        f.write(f'{email}\n')
                self.stdout.write(self.style.WARNING(f'   ⚠️  Saved {len(unmatched_emails)} unmatched emails to: attendance_unmatched_emails.txt'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

    def verify_import(self, data_dir):
        """Verify that data was imported correctly"""
        
        course_count = Course.objects.count()
        student_count = Student.objects.count()
        assignment_count = Assignment.objects.count()
        submission_count = Submission.objects.count()
        attendance_count = Attendance.objects.count()
        
        self.stdout.write(f'✅ Courses in database: {course_count}')
        self.stdout.write(f'✅ Students in database: {student_count}')
        self.stdout.write(f'✅ Assignments in database: {assignment_count}')
        self.stdout.write(f'✅ Submissions in database: {submission_count}')
        self.stdout.write(f'✅ Attendance records in database: {attendance_count}')
        
        # Show active cohort stats
        try:
            from django.utils import timezone
            today = timezone.now().date()
            
            for cohort in Cohort.objects.filter(is_closed=False):
                if cohort.start_date <= today <= cohort.end_date:
                    cohort_courses = Course.objects.filter(cohort=cohort).count()
                    cohort_students = Student.objects.filter(
                        course__cohort=cohort
                    ).values('google_id').distinct().count()
                    
                    self.stdout.write(f'\n✅ Active Cohort: {cohort.name}')
                    self.stdout.write(f'   Courses: {cohort_courses}')
                    self.stdout.write(f'   Students: {cohort_students}')
                    break
        except Exception:
            pass
