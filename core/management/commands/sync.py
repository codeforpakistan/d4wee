"""
Management command to sync Google Classroom data
Usage: python manage.py sync [--clear]

Note: --clear will delete all data EXCEPT courses/students/assignments from CLOSED cohorts.
      Closed cohort data is always protected to preserve historical records and certificates.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.services import sync_all_classroom_data
import traceback
import logging
from pathlib import Path
from datetime import datetime
import os


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
            help='Clear existing data before syncing (protects closed cohort data)',
        )

    def handle(self, *args, **options):
        # Setup file logging
        # Use /var/log/d4wee on Linux, logs/ in project dir on Windows
        if os.name == 'posix':
            log_dir = Path('/var/log/d4wee')
        else:
            log_dir = Path(__file__).resolve().parent.parent.parent.parent / 'logs'
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        log_file = log_dir / f'sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()  # Also log to console/systemd journal
            ],
            force=True  # Override any existing configuration
        )
        logger = logging.getLogger(__name__)
        
        logger.info('='*60)
        logger.info('D4WEE Google Classroom Data Sync')
        logger.info(f'Log file: {log_file}')
        logger.info('='*60)
        
        user_email = options['user']
        clear_data = options.get('clear', False)
        
        logger.info(f'User: {user_email}')
        logger.info(f'Clear data: {clear_data}')
        
        # Get user
        logger.info('Looking up user...')
        try:
            user = User.objects.get(email=user_email)
            logger.info(f'[OK] Found user: {user.email}')
            self.stdout.write(self.style.SUCCESS(f'Found user: {user.email}'))
        except User.DoesNotExist:
            logger.error(f'[ERROR] User not found: {user_email}')
            self.stdout.write(self.style.ERROR(f'User not found: {user_email}'))
            return
        
        # Clear data if requested
        if clear_data:
            from core.models import Course, Student, Assignment, Submission, StudentMetrics, SyncLog, Cohort
            
            logger.info('[CLEAR] Clearing existing data...')
            self.stdout.write('🗑️  Clearing existing data...')
            
            # Get closed cohorts - we NEVER clear their data
            closed_cohorts = Cohort.objects.filter(is_closed=True)
            closed_cohort_ids = list(closed_cohorts.values_list('id', flat=True))
            
            if closed_cohorts.exists():
                logger.warning(f'[PROTECT] Protecting {closed_cohorts.count()} closed cohort(s) from deletion')
                self.stdout.write(self.style.WARNING(
                    f'⚠️  Protecting {closed_cohorts.count()} closed cohort(s) from deletion:'
                ))
                for cohort in closed_cohorts:
                    logger.info(f'   [LOCKED] {cohort.name} (closed on {cohort.closed_date})')
                    self.stdout.write(f'   🔒 {cohort.name} (closed on {cohort.closed_date})')
            
            # Get courses from closed cohorts - these are protected
            protected_courses = Course.objects.filter(cohort_id__in=closed_cohort_ids)
            protected_course_ids = list(protected_courses.values_list('id', flat=True))
            
            if protected_courses.exists():
                logger.info(f'   [PROTECT] Protecting {protected_courses.count()} course(s) from closed cohorts')
                self.stdout.write(f'   📚 Protecting {protected_courses.count()} course(s) from closed cohorts')
            
            # Delete only data NOT from closed cohorts
            # Start from the bottom of the dependency chain
            metrics_count = StudentMetrics.objects.exclude(course_id__in=protected_course_ids).count()
            StudentMetrics.objects.exclude(course_id__in=protected_course_ids).delete()
            
            submissions_count = Submission.objects.exclude(assignment__course_id__in=protected_course_ids).count()
            Submission.objects.exclude(assignment__course_id__in=protected_course_ids).delete()
            
            assignments_count = Assignment.objects.exclude(course_id__in=protected_course_ids).count()
            Assignment.objects.exclude(course_id__in=protected_course_ids).delete()
            
            students_count = Student.objects.exclude(course_id__in=protected_course_ids).count()
            Student.objects.exclude(course_id__in=protected_course_ids).delete()
            
            courses_count = Course.objects.exclude(id__in=protected_course_ids).count()
            Course.objects.exclude(id__in=protected_course_ids).delete()
            
            # We can clear all sync logs as they're just audit trail
            sync_logs_count = SyncLog.objects.all().count()
            SyncLog.objects.all().delete()
            
            logger.info('[CLEARED] Data cleared (protected closed cohorts):')
            logger.info(f'   Courses: {courses_count}')
            logger.info(f'   Students: {students_count}')
            logger.info(f'   Assignments: {assignments_count}')
            logger.info(f'   Submissions: {submissions_count}')
            logger.info(f'   Metrics: {metrics_count}')
            logger.info(f'   Sync Logs: {sync_logs_count}')
            
            self.stdout.write(self.style.SUCCESS('✅ Data cleared (protected closed cohorts):'))
            self.stdout.write(f'   Courses: {courses_count}')
            self.stdout.write(f'   Students: {students_count}')
            self.stdout.write(f'   Assignments: {assignments_count}')
            self.stdout.write(f'   Submissions: {submissions_count}')
            self.stdout.write(f'   Metrics: {metrics_count}')
            self.stdout.write(f'   Sync Logs: {sync_logs_count}')
        
        # Run sync
        logger.info('='*60)
        logger.info(f'Starting sync for user: {user.email}')
        logger.info('='*60)
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'Starting sync for user: {user.email}')
        self.stdout.write('='*60 + '\n')
        
        try:
            sync_log = sync_all_classroom_data(user)
            
            logger.info('='*60)
            logger.info('[SUCCESS] Sync completed successfully!')
            logger.info('='*60)
            logger.info(f'Courses synced: {sync_log.courses_synced}')
            logger.info(f'Students synced: {sync_log.students_synced}')
            logger.info(f'Assignments synced: {sync_log.assignments_synced}')
            logger.info(f'Submissions synced: {sync_log.submissions_synced}')
            logger.info(f'Started: {sync_log.started_at}')
            logger.info(f'Completed: {sync_log.completed_at}')
            logger.info('='*60)
            
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
            logger.error('='*60)
            logger.error('[ERROR] ERROR during sync:')
            logger.error(str(e))
            logger.error('Full traceback:')
            logger.error(traceback.format_exc())
            logger.error('='*60)
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.ERROR('❌ ERROR during sync:'))
            self.stdout.write(self.style.ERROR(str(e)))
            self.stdout.write('\nFull traceback:')
            self.stdout.write('='*60)
            traceback.print_exc()
            self.stdout.write('='*60 + '\n')
