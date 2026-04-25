"""
Management command to seed initial data for Google OAuth configuration
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.core.management import call_command
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
        
        # Create default admin superuser
        self.stdout.write('\n👤 Setting up admin user...')
        admin_email = 'admin@example.com'
        admin_username = 'admin'
        admin_password = 'admin'
        
        if User.objects.filter(username=admin_username).exists():
            self.stdout.write(self.style.WARNING(f'⚠️  Admin user "{admin_username}" already exists'))
        else:
            User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Created superuser: {admin_username}'))
            self.stdout.write(f'   Email: {admin_email}')
            self.stdout.write(f'   Password: {admin_password}')
        
        # Load cohorts from fixture
        self.stdout.write('\n📅 Setting up cohorts...')
        try:
            call_command('loaddata', 'cohorts.json', verbosity=0)
            from core.models import Cohort
            cohort_count = Cohort.objects.count()
            active_cohort = Cohort.objects.filter(is_active=True).first()
            
            if active_cohort:
                self.stdout.write(self.style.SUCCESS(f'✅ Loaded {cohort_count} cohort(s)'))
                self.stdout.write(f'   📍 Current active cohort: {active_cohort.name}')
                self.stdout.write(f'   📅 Period: {active_cohort.start_date} to {active_cohort.end_date}')
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  Loaded {cohort_count} cohorts but none are active'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Could not load cohorts fixture: {e}'))
            self.stdout.write('   Run: python manage.py loaddata cohorts.json')
        
        self.stdout.write('\n' + self.style.SUCCESS('✅ Google OAuth is now configured!'))
        self.stdout.write('\n📝 Next steps:')
        self.stdout.write('   1. Make sure http://localhost:8000/accounts/google/login/callback/ is in Google Cloud Console')
        self.stdout.write('   2. Sign in at http://localhost:8000')
        self.stdout.write('   3. Click "Sync Data" to import classroom data')
        self.stdout.write(f'\n🔑 Admin access: http://localhost:8000/admin/ (username: admin, password: admin)\n')
