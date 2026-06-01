"""
Management command to re-categorize assignment types based on titles
Usage: python manage.py recategorize_assignments [--dry-run]
"""
from django.core.management.base import BaseCommand
from app.models import Assignment
import re


class Command(BaseCommand):
    help = 'Re-categorize assignment types based on their titles'
    
    def categorize_assignment_type(self, title):
        """
        Automatically categorize assignment type based on title
        Returns: 'PRE_TEST', 'POST_TEST', 'QUIZ', or 'ASSIGNMENT'
        """
        title_lower = title.lower()
        
        # Check for pre-test/pre-assessment
        if re.search(r'\b(pre[-\s]?(test|assessment|survey))\b', title_lower):
            return 'PRE_TEST'
        
        # Check for post-test/post-assessment
        if re.search(r'\b(post[-\s]?(test|assessment|survey))\b', title_lower):
            return 'POST_TEST'
        
        # Check for quiz
        if re.search(r'\bquiz\b', title_lower):
            return 'QUIZ'
        
        # Default to assignment
        return 'ASSIGNMENT'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('📝 Re-categorize Assignment Types'))
        self.stdout.write('='*60)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        self.stdout.write('')
        
        # Get all assignments
        assignments = Assignment.objects.select_related('course').all()
        
        changes = {
            'PRE_TEST': [],
            'POST_TEST': [],
            'QUIZ': [],
            'ASSIGNMENT': [],
        }
        
        unchanged_count = 0
        
        for assignment in assignments:
            new_type = self.categorize_assignment_type(assignment.title)
            
            if assignment.assignment_type != new_type:
                changes[new_type].append({
                    'assignment': assignment,
                    'old_type': assignment.assignment_type,
                    'new_type': new_type,
                })
                
                if not dry_run:
                    assignment.assignment_type = new_type
                    assignment.save()
            else:
                unchanged_count += 1
        
        # Display changes
        self.stdout.write('Changes to be made:' if dry_run else 'Changes made:')
        self.stdout.write('')
        
        total_changes = 0
        
        for type_name, assignment_list in changes.items():
            if assignment_list:
                self.stdout.write(self.style.SUCCESS(f'\n{type_name}:'))
                for item in assignment_list:
                    self.stdout.write(
                        f"  [{item['old_type']} → {item['new_type']}] "
                        f"{item['assignment'].course.name}: {item['assignment'].title}"
                    )
                    total_changes += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write('='*60)
        self.stdout.write(f'Changed: {total_changes}')
        self.stdout.write(f'Unchanged: {unchanged_count}')
        self.stdout.write(f'Total: {assignments.count()}')
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes'))
        
        self.stdout.write('')
