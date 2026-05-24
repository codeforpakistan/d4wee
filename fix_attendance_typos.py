"""
Fix typos in attendance JSON file
"""
import json
from pathlib import Path

# Email typo mappings (wrong -> correct)
EMAIL_FIXES = {
    'aishashafi@829gmail.com': 'aishashafi829@gmail.com',
    'ayankabee4556@gmail.com': 'ayankabeer4556@gmail.com',
    'ayshazal159@gmail.com': 'ayshazak159@gmail.com',
    'hosnafirdous07@gamil.com': 'hosnafirdous07@gmail.com',
    'hudaibia603561@gmal.com': 'hudaibia603561@gmail.com',
    'husnakarimk@gmail.co': 'husnakarimk@gmail.com',
    'sana.bukhaarii@gmail.com': 'sanaa.bukhaarii@gmail.com',
    'syedamadihashah902@gmail.com': 'syedamadihashah25@gmail.com',
    'habibagulzar2004@gmail.com': 'gulzarkhan0313930@gmail.com',
}

# Load attendance data
attendance_file = Path('data/pilot_attendance.json')
print(f'Loading {attendance_file}...')
with open(attendance_file, 'r', encoding='utf-8') as f:
    attendance_data = json.load(f)

print(f'Total attendance records: {len(attendance_data)}')

# Fix emails
fixes_made = 0
for record in attendance_data:
    email = record.get('Email Address', '')
    if email in EMAIL_FIXES:
        old_email = email
        new_email = EMAIL_FIXES[email]
        record['Email Address'] = new_email
        fixes_made += 1
        print(f'✅ Fixed: {old_email} → {new_email}')

# Save updated data
if fixes_made > 0:
    print(f'\nSaving {fixes_made} fixes to {attendance_file}...')
    with open(attendance_file, 'w', encoding='utf-8') as f:
        json.dump(attendance_data, f, indent=2, ensure_ascii=False)
    print('✅ Attendance data updated successfully!')
else:
    print('⚠️  No typos found to fix')

print(f'\nSummary:')
print(f'  Total records: {len(attendance_data)}')
print(f'  Fixes applied: {fixes_made}')
