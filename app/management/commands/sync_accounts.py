from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from app.models import Student


class Command(BaseCommand):
    help = 'Sync student social accounts with their student accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate without writing changes to database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run activated; no changes will be saved'))

        users = User.objects.prefetch_related('socialaccount_set', 'student_profile').order_by('email')

        same = []
        diff = []
        none = []

        for user in users:
            try:
                social_uid = [account.uid for account in user.socialaccount_set.all()]
                profile = getattr(user, 'student_profile', None)
                if profile and social_uid:
                    msg = f'{user.email}: {profile.google_id} > {social_uid[0]}'
                    if profile.google_id != social_uid[0]:
                        if not dry_run:
                            profile.google_id = social_uid[0]
                            profile.save()
                        diff.append(msg)
                        self.stdout.write(self.style.WARNING(msg))
                    else:
                        same.append(msg)
                        self.stdout.write(f'{user.email}: {profile.google_id} > {social_uid[0]}')
                elif not profile:
                    msg = f'{user.email}: None > {social_uid[0]}'
                    none.append(msg)
                    self.stdout.write(self.style.WARNING(f'{user.email}: No student profile'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(str(e)))

        self.stdout.write(f'{len(same)} same IDs')
        self.stdout.write(f'{len(diff)} different IDs')
        self.stdout.write('; '.join(diff))
        self.stdout.write(f'{len(none)} no IDs')
