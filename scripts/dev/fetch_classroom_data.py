"""
Fetch sample data from Google Classroom API and save to JSON files
This helps us understand the exact structure we need to model

Usage: python fetch_classroom_data.py
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


def fetch_and_save_courses(user_email=None):
    """Fetch courses from Google Classroom and save to JSON"""
    
    print("="*60)
    print("Fetching Google Classroom Data")
    print("="*60)
    
    # Get user - find any user with Google OAuth connected
    if user_email:
        try:
            user = User.objects.get(email=user_email)
            print(f"User: {user.email}")
            print(f"✓ Found user: {user.email}")
        except User.DoesNotExist:
            print(f"✗ User not found: {user_email}")
            return
    else:
        # Find any user with a Google social account
        from allauth.socialaccount.models import SocialAccount
        social_accounts = SocialAccount.objects.filter(provider='google')
        if not social_accounts.exists():
            print("✗ No users with Google OAuth found. Please login via Google first.")
            return
        
        user = social_accounts.first().user
        print(f"User: {user.email} (auto-detected)")
        print(f"✓ Using user: {user.email}\n")
    
    # Get Google Classroom service
    try:
        service = get_classroom_service(user)
        print("✓ Connected to Google Classroom API\n")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return
    
    # Create data directory
    data_dir = Path(__file__).resolve().parent / 'data'
    data_dir.mkdir(exist_ok=True)
    
    # Fetch courses
    print("Fetching courses...")
    try:
        courses_result = service.courses().list(pageSize=10).execute()
        courses = courses_result.get('courses', [])
        
        print(f"✓ Found {len(courses)} courses\n")
        
        # Save full courses data
        courses_file = data_dir / 'google_classroom_courses.json'
        with open(courses_file, 'w', encoding='utf-8') as f:
            json.dump(courses, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✓ Saved courses to: {courses_file}")
        
        # Print sample course structure
        if courses:
            print("\n" + "="*60)
            print("Sample Course Structure (first course):")
            print("="*60)
            print(json.dumps(courses[0], indent=2, default=str))
            
            # Print all available fields
            print("\n" + "="*60)
            print("Available fields in Course object:")
            print("="*60)
            for key in sorted(courses[0].keys()):
                value = courses[0][key]
                value_type = type(value).__name__
                value_preview = str(value)[:50] if value else 'null'
                print(f"  {key:25} ({value_type:10}): {value_preview}")
        
        # Fetch students, assignments, and submissions from first course (if available)
        if courses:
            # Try to find a course with students
            course_with_students = None
            
            for course in courses[:5]:  # Check first 5 courses
                course_id = course['id']
                course_name = course.get('name', 'Unknown')
                
                try:
                    students_result = service.courses().students().list(
                        courseId=course_id,
                        pageSize=5
                    ).execute()
                    students = students_result.get('students', [])
                    
                    if students:
                        course_with_students = course
                        print(f"\n{'='*60}")
                        print(f"Found course with students: {course_name}")
                        print(f"Course ID: {course_id}")
                        print("="*60)
                        break
                except Exception as e:
                    continue
            
            if not course_with_students:
                print(f"\n{'='*60}")
                print("No courses with students found. Using first course for structure.")
                print("="*60)
                course_with_students = courses[0]
            
            course_id = course_with_students['id']
            course_name = course_with_students.get('name', 'Unknown')
            
            # Fetch students
            try:
                print("\nFetching students...")
                students_result = service.courses().students().list(
                    courseId=course_id,
                    pageSize=100
                ).execute()
                students = students_result.get('students', [])
                
                students_file = data_dir / 'google_classroom_students.json'
                with open(students_file, 'w', encoding='utf-8') as f:
                    json.dump(students, f, indent=2, ensure_ascii=False, default=str)
                
                print(f"✓ Found {len(students)} students")
                print(f"✓ Saved to: {students_file}")
                
                if students:
                    print("\n" + "="*60)
                    print("Sample Student Structure (first student):")
                    print("="*60)
                    print(json.dumps(students[0], indent=2, default=str))
                    
                    print("\n" + "="*60)
                    print("Available fields in Student object:")
                    print("="*60)
                    for key in sorted(students[0].keys()):
                        value = students[0][key]
                        value_type = type(value).__name__
                        print(f"  {key:25} ({value_type:10})")
                        
            except Exception as e:
                print(f"✗ Error fetching students: {e}")
            
            # Fetch assignments (coursework)
            try:
                print("\nFetching assignments (coursework)...")
                coursework_result = service.courses().courseWork().list(
                    courseId=course_id,
                    pageSize=10
                ).execute()
                coursework = coursework_result.get('courseWork', [])
                
                coursework_file = data_dir / 'google_classroom_coursework.json'
                with open(coursework_file, 'w', encoding='utf-8') as f:
                    json.dump(coursework, f, indent=2, ensure_ascii=False, default=str)
                
                print(f"✓ Found {len(coursework)} assignments")
                print(f"✓ Saved to: {coursework_file}")
                
                if coursework:
                    print("\nSample Assignment fields:")
                    for key in sorted(coursework[0].keys()):
                        print(f"  {key}")
                        
            except Exception as e:
                print(f"✗ Error fetching coursework: {e}")
            
            # Fetch submissions (if we have coursework)
            if 'coursework' in locals() and coursework:
                try:
                    coursework_id = coursework[0]['id']
                    print("\nFetching submissions...")
                    submissions_result = service.courses().courseWork().studentSubmissions().list(
                        courseId=course_id,
                        courseWorkId=coursework_id,
                        pageSize=10
                    ).execute()
                    submissions = submissions_result.get('studentSubmissions', [])
                    
                    submissions_file = data_dir / 'google_classroom_submissions.json'
                    with open(submissions_file, 'w', encoding='utf-8') as f:
                        json.dump(submissions, f, indent=2, ensure_ascii=False, default=str)
                    
                    print(f"✓ Found {len(submissions)} submissions")
                    print(f"✓ Saved to: {submissions_file}")
                    
                    if submissions:
                        print("\nSample Submission fields:")
                        for key in sorted(submissions[0].keys()):
                            print(f"  {key}")
                            
                except Exception as e:
                    print(f"✗ Error fetching submissions: {e}")
        
        print("\n" + "="*60)
        print("Data fetch complete! Check the 'data/' directory for JSON files.")
        print("="*60)
        
    except Exception as e:
        print(f"✗ Error fetching courses: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import sys
    email = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_and_save_courses(email)
