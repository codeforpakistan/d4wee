from django.utils import timezone
from django.core.management.base import BaseCommand
from app.models.enrollment import Enrollment
from app.models.certificate import Certificate


class Command(BaseCommand):
    help = 'Generate certificats for eligible enrollments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate without writing changes to database',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Remove existing certificates',
        )
        parser.add_argument(
            '--num',
            type=int,
            default=0,
            help='Number of enrollments for which to generate data',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear = options['clear']
        num = options['num']

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run activated; no changes will be saved'))

        if clear:
            count = Certificate.objects.count()
            if not dry_run:
                Certificate.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'{count } certificates deleted...'))

        enrollments = Enrollment.objects.all().order_by('registration__student')
        self.stdout.write(f'Found {len(enrollments)} enrollments')

        if num:
            enrollments = enrollments[:num]
            self.stdout.write(f'Limiting current run to {num} enrollments')
        
        count = 0
        for enrollment in enrollments:
            if enrollment.certificate_eligible:
                count += 1
                certificiate = Certificate(
                    enrollment=enrollment,
                    issued_date=timezone.localdate(),
                    completion_percentage=enrollment.completion_rate or 0,
                    average_grade=enrollment.overall_average_score,
                )
                if not dry_run:
                    certificiate.save()

                enrollment.status = Enrollment.StatusChoices.COMPLETED
                enrollment.completion_date = timezone.localtime()

                if not dry_run:
                    enrollment.save()

                self.stdout.write(f'{enrollment.student.email} - {enrollment.course.name} (Completion: {round(enrollment.completion_rate)}%, Grade: {round(enrollment.overall_average_score)}%)')

        self.stdout.write(self.style.SUCCESS(f'{count} Certificates generated'))
