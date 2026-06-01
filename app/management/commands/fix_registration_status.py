"""
Management command to update ACTIVE registrations to APPROVED status
Usage: python manage.py fix_registration_status [--dry-run]
"""
from django.core.management.base import BaseCommand
from app.models import Registration
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Update all ACTIVE registrations to APPROVED status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--approved-by',
            type=str,
            default='teacher@codeforpakistan.org',
            help='Email of the user to set as approved_by (default: teacher@codeforpakistan.org)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        approved_by_email = options.get('approved_by')
        
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('🔧 Fix Registration Status'))
        self.stdout.write('='*60)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        self.stdout.write('')
        
        # Get admin user for approved_by
        try:
            admin_user = User.objects.get(email=approved_by_email)
            self.stdout.write(self.style.SUCCESS(f'✓ Found admin user: {admin_user.email}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'⚠ Admin user not found: {approved_by_email}'))
            self.stdout.write(self.style.WARNING('  Approved_by will be set to None'))
            admin_user = None
        
        self.stdout.write('')
        
        # Find all ACTIVE registrations
        active_registrations = Registration.objects.filter(status='ACTIVE')
        count = active_registrations.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No ACTIVE registrations found'))
            return
        
        self.stdout.write(f'Found {count} ACTIVE registrations')
        self.stdout.write('')
        
        # Show sample
        self.stdout.write('Sample registrations to update:')
        for reg in active_registrations[:10]:
            self.stdout.write(
                f"  ID {reg.id}: {reg.student.full_name} - {reg.cohort.name} "
                f"(status: '{reg.status}')"
            )
        
        if count > 10:
            self.stdout.write(f"  ... and {count - 10} more")
        
        self.stdout.write('')
        
        if not dry_run:
            # Update all ACTIVE to APPROVED
            from django.utils import timezone
            
            updated = 0
            for reg in active_registrations:
                reg.status = 'APPROVED'
                if admin_user:
                    reg.approved_by = admin_user
                    reg.approved_date = timezone.now()
                reg.save()
                updated += 1
            
            self.stdout.write('')
            self.stdout.write('='*60)
            self.stdout.write(self.style.SUCCESS(f'✓ Updated {updated} registrations to APPROVED'))
            self.stdout.write('='*60)
        else:
            self.stdout.write('')
            self.stdout.write('='*60)
            self.stdout.write(self.style.WARNING(f'Would update {count} registrations to APPROVED'))
            self.stdout.write('='*60)
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes'))
        
        self.stdout.write('')
