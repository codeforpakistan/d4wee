from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.socialaccount.signals import pre_social_login
from .models import Student


@receiver(pre_social_login)
def create_student_on_google_signup(sender, request, sociallogin, **kwargs):
    """
    Automatically create Student profile when user signs in with Google OAuth
    Everyone who signs up becomes a Student
    """
    # Get user from sociallogin
    user = sociallogin.user
    
    # Only proceed if user exists (after creation)
    if not user.pk:
        return
    
    # Skip if already has student profile or is staff
    if hasattr(user, 'student_profile') or user.is_staff:
        return
    
    # Get data from social account
    extra_data = sociallogin.account.extra_data
    
    # Create Student profile automatically
    Student.objects.get_or_create(
        user=user,
        defaults={
            'google_id': extra_data.get('id', f'user_{user.id}'),
            'full_name': extra_data.get('name', user.get_full_name() or user.username),
            'email': extra_data.get('email', user.email),
            'profile_photo': extra_data.get('picture', ''),
        }
    )
