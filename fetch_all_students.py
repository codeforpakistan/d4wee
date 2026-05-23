"""
Fetch ALL students from ALL Google Classroom courses
This will show us the PILOT cohort students
"""
import os
import sys
import django
import json
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from app.services import get_classroom_service
from app.models import Course


def fetch_all_students():
    """Fetch students from all courses"""
    
    print("="*60)
    print("Fetching ALL Students from Google Classroom")
    print("="*60)
    
    # Find teacher user
    from allauth.socialaccount.models import SocialAccount
    
    # Try to use teacher@codeforpakistan.org
    try:
        user = User.objects.get(email='teacher@codeforpakistan.org')
        print(f"User: {user.email}\n")
    except User.DoesNotExist:
        # Fallback to any user with Google OAuth
        social_accounts = SocialAccount.objects.filter(provider='google')
        if not social_accounts.exists():
            print("✗ No users with Google OAuth found.")
            return
        user = social_accounts.first().user
        print(f"User: {user.email} (auto-detected)\n")
    
    # Get Google Classroom service
    try:
        service = get_classroom_service(user)
        print("✓ Connected to Google Classroom API\n")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return
    
    # Get PILOT courses
    pilot_course_names = [
        'Orientation Class - Pilot Phase',
        'Basic Computer Literacy',
        'AI Essentials and Prompt Engineering',
        'Digital Safety & Online Security',
        'Modern Digital Workspace'
    ]
    
    courses = Course.objects.filter(name__in=pilot_course_names)
    print(f"Found {courses.count()} PILOT courses in database")
    print(f"PILOT courses: {', '.join([c.name for c in courses])}\n")
    
    all_students = {}
    course_student_count = {}
    
    for course in courses:
        print(f"Fetching students from: {course.display_name}...", end=" ")
        try:
            # Paginate through all students in this course
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
                
                # Check if there are more pages
                page_token = students_result.get('nextPageToken')
                if not page_token:
                    break
            
            course_student_count[course.display_name] = len(students)
            print(f"✓ {len(students)} students")
            
            # Collect unique students by userId
            for student in students:
                user_id = student['userId']
                if user_id not in all_students:
                    all_students[user_id] = student
                    # Add course tracking
                    all_students[user_id]['courses_enrolled'] = []
                
                all_students[user_id]['courses_enrolled'].append({
                    'course_id': course.google_id,
                    'course_name': course.name,
                    'course_section': course.section
                })
                
        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg:
                print(f"✗ No access (not a teacher?)")
            elif '403' in error_msg:
                print(f"✗ Permission denied")
            else:
                print(f"✗ Error: {e}")
            continue
    
    # Save to JSON
    data_dir = Path(__file__).resolve().parent / 'data'
    data_dir.mkdir(exist_ok=True)
    
    students_file = data_dir / 'all_students.json'
    students_list = list(all_students.values())
    
    with open(students_file, 'w', encoding='utf-8') as f:
        json.dump(students_list, f, indent=2, ensure_ascii=False, default=str)
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"Total unique students: {len(all_students)}")
    print(f"\nStudents per course:")
    for course_name, count in sorted(course_student_count.items()):
        if count > 0:
            print(f"  {course_name:50} {count:3} students")
    
    print(f"\n✓ Saved all students to: {students_file}")
    
    # Show sample student structure
    if students_list:
        print("\n" + "="*60)
        print("Sample Student Structure:")
        print("="*60)
        print(json.dumps(students_list[0], indent=2, default=str))
        
        # Show all fields
        print("\n" + "="*60)
        print("Available Student Fields:")
        print("="*60)
        sample = students_list[0]
        for key in sorted(sample.keys()):
            if key != 'courses_enrolled':
                value = sample[key]
                print(f"  {key:20} {type(value).__name__:10}")
        
        # Show profile structure
        if 'profile' in sample:
            print("\nProfile Fields:")
            profile = sample['profile']
            for key in sorted(profile.keys()):
                value = profile[key]
                print(f"  {key:20} {type(value).__name__:10}")


if __name__ == '__main__':
    fetch_all_students()
