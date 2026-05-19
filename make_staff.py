#!/usr/bin/env python
"""Make a user staff so they can access admin"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User

# Get email from command line or use first user
if len(sys.argv) > 1:
    email = sys.argv[1]
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        print(f"❌ User with email {email} not found")
        sys.exit(1)
else:
    user = User.objects.first()
    if not user:
        print("❌ No users found. Sign in with Google first.")
        sys.exit(1)

# Make them staff
user.is_staff = True
user.save()

print(f"✅ {user.email} is now staff and can access admin at /admin/")
