"""
Management command to sync Google Classroom data and attendance
Usage: python manage.py sync [--clear]

Note: --clear will delete data ONLY for the currently ACTIVE cohort (within date range).
      All inactive and closed cohort data is protected and never touched.
      Attendance data is also synced and cleared only for the active cohort.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.services import sync_all_classroom_data, sync_attendance_from_sheets
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
            help='Clear existing data before syncing (only for active cohort)',
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
            from core.models import Course, Student, Assignment, Submission, StudentMetrics, SyncLog, Cohort, AttendanceRecord
            
            logger.info('[CLEAR] Clearing existing data...')
            self.stdout.write('🗑️  Clearing existing data...')
            
            # Find active cohort using is_active property
            active_cohort = None
            for cohort in Cohort.objects.filter(is_closed=False):
                if cohort.is_active:
                    active_cohort = cohort
                    break
            
            if not active_cohort:
                logger.warning('[NO ACTIVE COHORT] No active cohort found. Cannot clear data.')
                self.stdout.write(self.style.WARNING('⚠️  No active cohort found (current date not within any cohort range).'))
                self.stdout.write(self.style.WARNING('   Clear operation skipped - no data will be modified.'))
                return
            
            logger.info(f'[TARGET] Target cohort for clearing: {active_cohort.name}')
            self.stdout.write(self.style.SUCCESS(f'✅ Target cohort for clearing: {active_cohort.name}'))
            
            # Get courses from active cohort - ONLY these will be cleared
            active_courses = Course.objects.filter(cohort=active_cohort)
            active_course_ids = list(active_courses.values_list('id', flat=True))
            
            # Protect all inactive cohorts
            inactive_cohorts = Cohort.objects.exclude(id=active_cohort.id)
            protected_courses = Course.objects.exclude(cohort=active_cohort)
            protected_course_ids = list(protected_courses.values_list('id', flat=True))
            
            if inactive_cohorts.exists():
                logger.warning(f'[PROTECT] Protecting {inactive_cohorts.count()} inactive cohort(s) from deletion')
                self.stdout.write(self.style.WARNING(
                    f'⚠️  Protecting {inactive_cohorts.count()} inactive cohort(s):'
                ))
                for cohort in inactive_cohorts:
                    status = 'closed' if cohort.is_closed else 'inactive'
                    logger.info(f'   [LOCKED] {cohort.name} ({status})')
                    self.stdout.write(f'   🔒 {cohort.name} ({status})')
            
            if protected_courses.exists():
                logger.info(f'   [PROTECT] Protecting {protected_courses.count()} course(s) from inactive cohorts')
                self.stdout.write(f'   📚 Protecting {protected_courses.count()} course(s) from inactive cohorts')
            
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
            
            # Clear attendance records ONLY for active cohort
            attendance_count = AttendanceRecord.objects.filter(cohort=active_cohort).count()
            AttendanceRecord.objects.filter(cohort=active_cohort).delete()
            
            logger.info(f'[CLEARED] Data cleared for target cohort ({active_cohort.name}):')
            logger.info(f'   Courses: {courses_count}')
            logger.info(f'   Students: {students_count}')
            logger.info(f'   Assignments: {assignments_count}')
            logger.info(f'   Submissions: {submissions_count}')
            logger.info(f'   Metrics: {metrics_count}')
            logger.info(f'   Sync Logs: {sync_logs_count}')
            logger.info(f'   Attendance Records: {attendance_count}')
            
            self.stdout.write(self.style.SUCCESS(f'✅ Data cleared for target cohort ({active_cohort.name}):'))
            self.stdout.write(f'   Courses: {courses_count}')
            self.stdout.write(f'   Students: {students_count}')
            self.stdout.write(f'   Assignments: {assignments_count}')
            self.stdout.write(f'   Submissions: {submissions_count}')
            self.stdout.write(f'   Metrics: {metrics_count}')
            self.stdout.write(f'   Sync Logs: {sync_logs_count}')
            self.stdout.write(f'   Attendance Records: {attendance_count}')
        
        # Run sync - ONLY if there's an active cohort
        from core.models import Cohort
        from django.utils import timezone
        today = timezone.now().date()
        
        # Find active cohort using is_active property
        target_cohort = None
        for cohort in Cohort.objects.filter(is_closed=False):
            if cohort.is_active:
                target_cohort = cohort
                break
        
        if not target_cohort:
            logger.warning('[NO ACTIVE COHORT] No active cohort found. Sync skipped.')
            self.stdout.write(self.style.WARNING('⚠️  No active cohort found (current date not within any cohort range).'))
            self.stdout.write(self.style.WARNING('   Sync skipped - no data will be modified.'))
            self.stdout.write(f'\n   Current date: {today}')
            
            # Show available cohorts for reference
            all_cohorts = Cohort.objects.all().order_by('start_date')
            if all_cohorts.exists():
                self.stdout.write('\n   Available cohorts:')
                for c in all_cohorts:
                    status = 'closed' if c.is_closed else ('active' if c.is_active else ('future' if c.start_date > today else 'ended'))
                    self.stdout.write(f'   • {c.name}: {c.start_date} to {c.end_date} [{status}]')
            return
        
        logger.info('='*60)
        logger.info(f'Starting sync for user: {user.email}')
        logger.info(f'Target cohort: {target_cohort.name}')
        logger.info('='*60)
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'Starting sync for user: {user.email}')
        self.stdout.write(f'🎯 Target cohort: {target_cohort.name}')
        self.stdout.write('='*60 + '\n')
        
        try:
            # Sync classroom data for target cohort only
            sync_log = sync_all_classroom_data(user, target_cohort=target_cohort)
            
            logger.info('='*60)
            logger.info('[SUCCESS] Classroom sync completed successfully!')
            logger.info('='*60)
            logger.info(f'Courses synced: {sync_log.courses_synced}')
            logger.info(f'Students synced: {sync_log.students_synced}')
            logger.info(f'Assignments synced: {sync_log.assignments_synced}')
            logger.info(f'Submissions synced: {sync_log.submissions_synced}')
            logger.info(f'Started: {sync_log.started_at}')
            logger.info(f'Completed: {sync_log.completed_at}')
            logger.info('='*60)
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('✅ Classroom sync completed successfully!'))
            self.stdout.write('='*60)
            self.stdout.write(f'📊 Courses synced: {sync_log.courses_synced}')
            self.stdout.write(f'👥 Students synced: {sync_log.students_synced}')
            self.stdout.write(f'📝 Assignments synced: {sync_log.assignments_synced}')
            self.stdout.write(f'📄 Submissions synced: {sync_log.submissions_synced}')
            self.stdout.write(f'⏱️  Started: {sync_log.started_at}')
            self.stdout.write(f'✅ Completed: {sync_log.completed_at}')
            self.stdout.write('='*60 + '\n')
            
            # Sync attendance data from Google Sheets
            logger.info('\n' + '='*60)
            logger.info('[ATTENDANCE] Starting attendance sync from Google Sheets')
            logger.info('='*60)
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.WARNING('📋 Starting attendance sync from Google Sheets'))
            self.stdout.write('='*60 + '\n')
            
            attendance_stats = sync_attendance_from_sheets(user=user, target_cohort=target_cohort, clear_existing=False)
            
            logger.info('='*60)
            logger.info('[SUCCESS] Attendance sync completed!')
            logger.info('='*60)
            logger.info(f'Created/Updated: {attendance_stats["created"]} records')
            logger.info(f'Skipped: {attendance_stats["skipped"]} records')
            logger.info(f'Errors: {attendance_stats["errors"]} records')
            logger.info('='*60)
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('✅ Attendance sync completed!'))
            self.stdout.write('='*60)
            self.stdout.write(f'📝 Created/Updated: {attendance_stats["created"]} records')
            self.stdout.write(f'⚠️  Skipped: {attendance_stats["skipped"]} records')
            self.stdout.write(f'❌ Errors: {attendance_stats["errors"]} records')
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
