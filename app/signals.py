from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.socialaccount.signals import pre_social_login
from .models import Student


@receiver(pre_social_login)
def create_student_profile(sender, request, sociallogin, **kwargs):
    """
    Automatically create Student profile when user signs in with Google OAuth
    """
    # Get user from sociallogin (might be None for new users)
    user = sociallogin.user
    
    # Only proceed if user is being created
    if not user.pk:
        return
    
    # Check if student profile already exists
    if hasattr(user, 'student_profile'):
        return
    
    # Get data from social account
    extra_data = sociallogin.account.extra_data
    
    # Create Student profile
    Student.objects.get_or_create(
        user=user,
        defaults={
            'google_id': extra_data.get('id', ''),
            'full_name': extra_data.get('name', user.get_full_name() or user.username),
            'email': extra_data.get('email', user.email),
            'profile_photo': extra_data.get('picture', ''),
        }
    )


@receiver(post_save, sender=User)
def ensure_student_profile(sender, instance, created, **kwargs):
    """
    Backup signal to ensure Student profile exists for every User
    This catches cases where user might be created outside of OAuth flow
    """
    if created and not hasattr(instance, 'student_profile'):
        # Try to create basic student profile
        Student.objects.get_or_create(
            user=instance,
            defaults={
                'google_id': f'user_{instance.id}',  # Temporary ID until OAuth
                'full_name': instance.get_full_name() or instance.username,
                'email': instance.email or f'{instance.username}@temp.local',
            }
        )
