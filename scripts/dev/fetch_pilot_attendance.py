"""
Fetch attendance data from Google Sheets for PILOT cohort
"""
import os
import django
import json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from app.services import get_sheets_service

# Get teacher user
user = User.objects.get(email='teacher@codeforpakistan.org')

# Get Google Sheets service
service = get_sheets_service(user)

# PILOT attendance spreadsheet
spreadsheet_id = '1hWGkuHAKFT-Z6I_I5A0hML9WxLd9sU5wEIOk1WP_4F4'

print('=' * 80)
print('FETCHING ATTENDANCE DATA FROM GOOGLE SHEETS')
print('=' * 80)
print(f'Spreadsheet ID: {spreadsheet_id}')
print()

try:
    # Get sheet metadata to see available sheets
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = spreadsheet.get('sheets', [])
    
    print('Available sheets:')
    for sheet in sheets:
        title = sheet['properties']['title']
        print(f'  - {title}')
    
    print()
    
    # Read the main data sheet
    range_name = 'Form Responses 1!A:K'
    
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()
    
    values = result.get('values', [])
    
    if not values:
        print('No data found in spreadsheet')
    else:
        print(f'Found {len(values)} rows (including header)')
        print()
        
        # First row is header
        headers = values[0]
        print('Column headers:')
        for i, header in enumerate(headers):
            print(f'  {i}: {header}')
        
        print()
        print(f'Total attendance records: {len(values) - 1}')
        print()
        
        # Convert to list of dictionaries
        attendance_data = []
        for row in values[1:]:
            # Pad row if needed
            while len(row) < len(headers):
                row.append('')
            
            record = dict(zip(headers, row))
            attendance_data.append(record)
        
        # Save to JSON
        os.makedirs('data', exist_ok=True)
        output_file = 'data/pilot_attendance.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(attendance_data, f, indent=2, ensure_ascii=False)
        
        print(f'✓ Saved {len(attendance_data)} attendance records to {output_file}')
        print()
        
        # Show sample record
        if attendance_data:
            print('Sample attendance record:')
            sample = attendance_data[0]
            for key, value in sample.items():
                print(f'  {key}: {value}')
        
        print()
        print('=' * 80)

except Exception as e:
    print(f'Error fetching data: {e}')
    import traceback
    traceback.print_exc()
