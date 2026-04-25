"""
Management command to show cohort completion statistics
"""
from django.core.management.base import BaseCommand
from core.models import Cohort, CohortEnrollment, Certificate


class Command(BaseCommand):
    help = 'Show cohort completion statistics'

    def handle(self, *args, **options):
        self.stdout.write('\nCohort Completion Statistics')
        self.stdout.write('=' * 80)

        cohorts = Cohort.objects.all()

        for cohort in cohorts:
            self.stdout.write(f'\n{cohort.name}')
            self.stdout.write(f'  Period: {cohort.start_date} to {cohort.end_date}')
            status = "Active" if cohort.is_active else "Inactive"
            closed = "Closed" if cohort.is_closed else "Open"
            self.stdout.write(f'  Status: {status}, {closed}')
            
            enrollments = CohortEnrollment.objects.filter(cohort=cohort)
            total = enrollments.count()
            completed = enrollments.filter(status='COMPLETED').count()
            in_progress = enrollments.filter(status='IN_PROGRESS').count()
            dropped = enrollments.filter(status='DROPPED').count()
            enrolled = enrollments.filter(status='ENROLLED').count()
            
            self.stdout.write(f'\n  Enrollments:')
            self.stdout.write(f'    Total: {total}')
            self.stdout.write(f'    Completed: {completed}')
            self.stdout.write(f'    In Progress: {in_progress}')
            self.stdout.write(f'    Enrolled: {enrolled}')
            self.stdout.write(f'    Dropped: {dropped}')
            
            if total > 0:
                completion_rate = (completed / total) * 100
                self.stdout.write(f'    Completion Rate: {completion_rate:.1f}%')
            
            certificates = Certificate.objects.filter(cohort=cohort)
            self.stdout.write(f'\n  Certificates Issued: {certificates.count()}')
            
            # Show courses in this cohort
            courses = cohort.courses.all()
            if courses.exists():
                self.stdout.write(f'\n  Courses ({courses.count()}):')
                for course in courses:
                    self.stdout.write(f'    - {course.name}')

        self.stdout.write('\n' + '=' * 80 + '\n')
