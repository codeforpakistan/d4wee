"""
Analyze unmatched attendance emails and find closest matches
"""
import os
import django
import difflib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Student

# Unmatched emails from attendance
unmatched = [
    'aishashafi@829gmail.com',
    'ayankabee4556@gmail.com',
    'ayshazal159@gmail.com',
    'habibagulzar2004@gmail.com',
    'hafsasajjad5194444@gmail.com',
    'hosnafirdous07@gamil.com',
    'hudaibia603561@gmal.com',
    'husnakarimk@gmail.co',
    'qtehreem933@gmail.com',
    'robeenaaimal7@gmail.com',
    'sana.bukhaarii@gmail.com',
    'syedamadihashah902@gmail.com',
    'yousragulwum@gmail.com',
    'zainabnavid01@gmail.com',
]

# Get all student emails
all_emails = list(Student.objects.values_list('email', flat=True))

print('='*80)
print('UNMATCHED ATTENDANCE EMAILS - FINDING CLOSEST STUDENT EMAIL MATCHES')
print('='*80)
print(f'Total unmatched: {len(unmatched)}')
print(f'Total students: {len(all_emails)}\n')

for email in unmatched:
    # Find closest matches
    matches = difflib.get_close_matches(email, all_emails, n=3, cutoff=0.6)
    
    if matches:
        print(f'❌ {email}')
        for match in matches:
            similarity = difflib.SequenceMatcher(None, email, match).ratio()
            print(f'   ✓ {match} (similarity: {similarity:.2%})')
    else:
        print(f'❌ {email}')
        print(f'   ⚠️  NO CLOSE MATCH FOUND')
    print()

print('='*80)
print('OBVIOUS TYPOS DETECTED:')
print('='*80)

typos = {
    'aishashafi@829gmail.com': 'Typo: @829gmail.com -> should be @gmail.com',
    'hosnafirdous07@gamil.com': 'Typo: @gamil.com -> should be @gmail.com',
    'hudaibia603561@gmal.com': 'Typo: @gmal.com -> should be @gmail.com',
    'husnakarimk@gmail.co': 'Typo: @gmail.co -> should be @gmail.com',
}

for email, reason in typos.items():
    print(f'{email:40} - {reason}')
