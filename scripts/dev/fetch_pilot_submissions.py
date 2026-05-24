"""
Fetch ALL student submissions from PILOT assignments
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from app.services import get_classroom_service
from app.models import Assignment
import json

# Get teacher user
teacher = User.objects.get(email='teacher@codeforpakistan.org')
service = get_classroom_service(teacher)

# Get PILOT assignments
pilot_assignments = Assignment.objects.filter(
    course__name__in=[
        'Orientation Class - Pilot Phase',
        'Basic Computer Literacy',
        'AI Essentials and Prompt Engineering',
        'Digital Safety & Online Security',
        'Modern Digital Workspace'
    ]
)

print(f'Found {pilot_assignments.count()} PILOT assignments')
print()

all_submissions = []
total_count = 0

for assignment in pilot_assignments[:3]:  # Test with first 3 assignments
    print(f'Fetching submissions for: {assignment.title[:60]}...', end=' ')
    
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
        
        print(f'✓ {len(submissions_list)} submissions')
        total_count += len(submissions_list)
        
        # Add to collection (only save a few samples)
        if len(all_submissions) < 10:
            for sub in submissions_list[:3]:
                sub['assignment_title'] = assignment.title
                sub['course_name'] = assignment.course.name
                all_submissions.append(sub)
            
    except Exception as e:
        print(f'✗ Error: {e}')

print()
print(f'Total submissions checked: {total_count} (from 3 assignments)')
print(f'Sample submissions saved: {len(all_submissions)}')

# Save sample to file
output_file = 'data/pilot_submissions_sample.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_submissions, f, indent=2, ensure_ascii=False)

print(f'Saved samples to {output_file}')
print()

if all_submissions:
    print('Sample submission structure:')
    sample = all_submissions[0]
    print(f"  Assignment: {sample.get('assignment_title')}")
    print(f"  User ID: {sample.get('userId')}")
    print(f"  State: {sample.get('state')}")
    print(f"  Assigned Grade: {sample.get('assignedGrade')}")
    print(f"  Late: {sample.get('late')}")
    print(f"  Fields: {', '.join(sample.keys())}")
