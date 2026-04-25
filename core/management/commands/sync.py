"""
Management command to sync Google Classroom data
Usage: python manage.py sync [--clear]
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.services import sync_all_classroom_data
import traceback


class Command(BaseCommand):
    help = 'Sync Google Classroom data for teacher@codeforpakistan.org'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='teacher@codeforpakistan.org',
            help='Email of the user to sync data for (default: teacher@codeforpakistan.org)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing data before syncing',
        )

    def handle(self, *args, **options):
        user_email = options['user']
        clear_data = options.get('clear', False)
        
        # Get user
        try:
            user = User.objects.get(email=user_email)
            self.stdout.write(self.style.SUCCESS(f'Found user: {user.email}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User not found: {user_email}'))
            return
        
        # Clear data if requested
        if clear_data:
            from core.models import Course, Student, Assignment, Submission, StudentMetrics, SyncLog
            self.stdout.write('🗑️  Clearing existing data...')
            StudentMetrics.objects.all().delete()
            Submission.objects.all().delete()
            Assignment.objects.all().delete()
            Student.objects.all().delete()
            Course.objects.all().delete()
            SyncLog.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Data cleared'))
        
        # Run sync
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'Starting sync for user: {user.email}')
        self.stdout.write('='*60 + '\n')
        
        try:
            sync_log = sync_all_classroom_data(user)
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('✅ Sync completed successfully!'))
            self.stdout.write('='*60)
            self.stdout.write(f'📊 Courses synced: {sync_log.courses_synced}')
            self.stdout.write(f'👥 Students synced: {sync_log.students_synced}')
            self.stdout.write(f'📝 Assignments synced: {sync_log.assignments_synced}')
            self.stdout.write(f'📄 Submissions synced: {sync_log.submissions_synced}')
            self.stdout.write(f'⏱️  Started: {sync_log.started_at}')
            self.stdout.write(f'✅ Completed: {sync_log.completed_at}')
            self.stdout.write('='*60 + '\n')
            
        except Exception as e:
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.ERROR('❌ ERROR during sync:'))
            self.stdout.write(self.style.ERROR(str(e)))
            self.stdout.write('\nFull traceback:')
            self.stdout.write('='*60)
            traceback.print_exc()
            self.stdout.write('='*60 + '\n')
