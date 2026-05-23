import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Cohort

print('=' * 60)
print('COHORT CHECK')
print('=' * 60)
print(f'Total cohorts: {Cohort.objects.count()}')
print()

pilot = Cohort.objects.filter(name='Pilot').first()
if pilot:
    print(f'✓ PILOT cohort found')
    print(f'  Name: {pilot.name}')
    print(f'  Dates: {pilot.start_date} to {pilot.end_date}')
    print(f'  Status: {pilot.status}')
else:
    print('✗ PILOT cohort NOT FOUND')
    print()
    print('All cohorts:')
    for cohort in Cohort.objects.all():
        print(f'  - {cohort.name} ({cohort.start_date} to {cohort.end_date})')
