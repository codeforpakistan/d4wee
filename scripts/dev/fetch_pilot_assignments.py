"""
Fetch ALL coursework (assignments) from PILOT courses
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from app.services import get_classroom_service
from app.models import Course
import json

# Get teacher user
teacher = User.objects.get(email='teacher@codeforpakistan.org')
service = get_classroom_service(teacher)

# Get PILOT courses
pilot_course_names = [
    'Orientation Class - Pilot Phase',
    'Basic Computer Literacy',
    'AI Essentials and Prompt Engineering',
    'Digital Safety & Online Security',
    'Modern Digital Workspace'
]

pilot_courses = Course.objects.filter(name__in=pilot_course_names)
print(f'Found {pilot_courses.count()} PILOT courses')
print()

all_coursework = []

for course in pilot_courses:
    print(f'Fetching from {course.display_name}...', end=' ')
    
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
        
        print(f'✓ {len(coursework_list)} assignments')
        
        # Add course reference to each coursework
        for cw in coursework_list:
            cw['course_name'] = course.name
            cw['course_section'] = course.section
            all_coursework.append(cw)
            
    except Exception as e:
        print(f'✗ Error: {e}')

print()
print(f'Total assignments across all PILOT courses: {len(all_coursework)}')

# Save to file
output_file = 'data/pilot_assignments.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_coursework, f, indent=2, ensure_ascii=False)

print(f'Saved to {output_file}')
print()

# Show distribution
from collections import Counter
by_course = Counter([cw['course_name'] for cw in all_coursework])
print('Assignments by course:')
for course_name, count in by_course.most_common():
    print(f'  {course_name}: {count}')

print()
print('Sample assignment structure:')
if all_coursework:
    sample = all_coursework[0]
    print(f"  Title: {sample.get('title')}")
    print(f"  Work Type: {sample.get('workType')}")
    print(f"  Max Points: {sample.get('maxPoints')}")
    print(f"  Due Date: {sample.get('dueDate', 'No due date')}")
    print(f"  State: {sample.get('state')}")
    print(f"  Course: {sample.get('course_name')}")
    print(f"  Fields: {', '.join(sample.keys())}")
