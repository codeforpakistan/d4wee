"""
Management command to seed initial data for Google OAuth configuration
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from dotenv import load_dotenv


class Command(BaseCommand):
    help = 'Setup Google OAuth SocialApp and configure site for local development'

    def handle(self, *args, **options):
        load_dotenv()
        
        # Update site for local development
        site = Site.objects.get_current()
        site.domain = 'localhost:8000'
        site.name = 'Local Development'
        site.save()
        self.stdout.write(self.style.SUCCESS(f'✅ Updated site to {site.domain}'))
        
        # Setup Google OAuth SocialApp
        client_id = os.getenv('GOOGLE_OAUTH2_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_OAUTH2_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            self.stdout.write(self.style.ERROR(
                '❌ Error: GOOGLE_OAUTH2_CLIENT_ID and GOOGLE_OAUTH2_CLIENT_SECRET must be set in .env file'
            ))
            return
        
        # Delete any existing Google OAuth apps (clean slate)
        existing_count = SocialApp.objects.filter(provider='google').count()
        if existing_count > 0:
            SocialApp.objects.filter(provider='google').delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Deleted {existing_count} existing Google OAuth app(s)'))
        
        # Create fresh SocialApp
        social_app = SocialApp.objects.create(
            provider='google',
            name='Google Classroom OAuth',
            client_id=client_id,
            secret=client_secret,
        )
        created = True
        
        if not created:
            # Update existing app
            social_app.client_id = client_id
            social_app.secret = client_secret
            social_app.name = 'Google Classroom OAuth'
            social_app.save()
            self.stdout.write(self.style.SUCCESS('✅ Updated existing Google OAuth app'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Created new Google OAuth app'))
        
        # Add to site
        if site not in social_app.sites.all():
            social_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS(f'✅ Added OAuth app to site: {site.domain}'))
        
        self.stdout.write('\n📋 Configuration:')
        self.stdout.write(f'   Provider: {social_app.provider}')
        self.stdout.write(f'   Client ID: {social_app.client_id}')
        self.stdout.write(f'   Sites: {", ".join(str(s) for s in social_app.sites.all())}')
        
        self.stdout.write('\n' + self.style.SUCCESS('✅ Google OAuth is now configured!'))
        self.stdout.write('\n📝 Next steps:')
        self.stdout.write('   1. Make sure http://localhost:8000/accounts/google/login/callback/ is in Google Cloud Console')
        self.stdout.write('   2. Sign in at http://localhost:8000')
        self.stdout.write('   3. Click "Sync Data" to import classroom data\n')
