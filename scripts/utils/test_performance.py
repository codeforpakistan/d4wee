#!/usr/bin/env python
"""Performance test script for views"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.test import RequestFactory
from django.db import connection, reset_queries
from django.contrib.auth.models import User
from app.views import views

# Create request factory
factory = RequestFactory()

# Get admin user
admin = User.objects.filter(is_staff=True).first()
if not admin:
    print("No admin user found!")
    exit(1)

# Test each view
views_to_test = [
    ('cohorts', None, 'Cohorts List'),
    ('courses', None, 'Courses List'),
    ('students_list', None, 'Students List'),
    ('course_detail', {'course_id': 43}, 'Course Detail (ID=43)'),
    ('student_detail', {'google_id': '104465743959587055209'}, 'Student Detail'),
]

print("=" * 70)
print("DATABASE QUERY PERFORMANCE TEST")
print("=" * 70)

for view_name, kwargs, description in views_to_test:
    reset_queries()
    
    # Create request
    request = factory.get('/')
    request.user = admin
    
    # Call view
    try:
        view_func = getattr(views, view_name)
        if kwargs:
            response = view_func(request, **kwargs)
        else:
            response = view_func(request)
        
        query_count = len(connection.queries)
        
        print(f"\n{description:30}")
        print(f"  View Function: {view_name}")
        print(f"  Query Count: {query_count}")
        
        if query_count > 50:
            print(f"  ⚠️  WARNING: High query count (N+1 problem likely)")
        elif query_count > 20:
            print(f"  ⚠️  Moderate query count")
        else:
            print(f"  ✓ Good performance")
            
    except Exception as e:
        print(f"\n{description:30}")
        print(f"  ❌ Error: {str(e)}")

print("\n" + "=" * 70)

