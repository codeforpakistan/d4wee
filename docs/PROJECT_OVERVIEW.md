# D4WEE Project Overview

**Digital for Women's Economic Empowerment** - Learning Management System  
Built for UN Women/Code for Pakistan

## Tech Stack

- **Backend**: Django 5.2
- **Authentication**: django-allauth (Google OAuth)
- **API Integration**: Google Classroom API, Google Sheets API
- **Database**: PostgreSQL (production and development)
- **Frontend**: Tailwind CSS
- **Package Manager**: uv
- **Deployment**: Gunicorn + Caddy, systemd timers
- **Hosting**: DigitalOcean (d4wee.codeforpakistan.org)

## Core Concept

Cohort-based learning system that integrates with Google Classroom to track student progress across time-bound training programs (typically 3 months).

## Data Model Architecture

### Primary Entities

1. **Student** (`app/models/user.py`)
   - Links to Django User (one-to-one)
   - Stores Google ID, email, profile info
   - Created when first registration is approved

2. **Course** (`app/models/program.py`)
   - Independent course catalog
   - Links to Google Classroom via `google_id`
   - Status: DRAFT, ACTIVE, ARCHIVED

3. **Cohort** (`app/models/program.py`)
   - Time-bound training batches (3 months)
   - Has start/end dates
   - Status: UPCOMING, ACTIVE, CLOSED
   - Manages registration limits

4. **Registration** (`app/models/relationship.py`)
   - Student's enrollment in a Cohort
   - Workflow: PENDING → APPROVED → ACTIVE → COMPLETED/DROPPED
   - Tracks overall cohort participation
   - Certificate eligibility: 75% attendance + 50% avg score + all tests attempted

5. **Enrollment** (`app/models/relationship.py`)
   - Student taking specific Course within Cohort context
   - Tracks per-course metrics
   - Calculates completion rates, scores, categorization

6. **Assignment & Submission** (`app/models/content.py`)
   - Synced from Google Classroom
   - Types: PRE_TEST, POST_TEST, ASSIGNMENT, QUIZ
   - Submissions track state, grades, late status

7. **Attendance** (`app/models/tracking.py`)
   - Weekly attendance tracking
   - Synced from Google Sheets
   - Tracks hours spent learning per week

8. **Certificate** (`app/models/tracking.py`)
   - Issued certificates for course/cohort completion

9. **SyncLog** (`app/models/tracking.py`)
   - Tracks data synchronization from Google Classroom

## Key Features

### Staff Dashboard
- Cohort/course/student statistics
- Student categorization:
  - **FOCUS**: <60% completion or <60% scores
  - **PUSH**: 60-85% completion/scores  
  - **PRAISE**: >85% completion and >85% scores
- Attendance tracking and mismatch detection
- Certificate eligibility checking
- Manual data sync trigger

### Student Dashboard
- Registration status
- Course enrollments
- Completion rates and scores
- Attendance rates

### Automated Sync
- Runs nightly at 2 AM via systemd timer (`d4wee-sync.timer`)
- Syncs Google Classroom data (courses, students, assignments, submissions)
- Syncs attendance from Google Sheets
- **Only syncs data for currently active cohort** (protects historical data)

## Project Structure

```
D4WEE/
├── app/                      # Main Django app
│   ├── models/              # Fat models with business logic
│   │   ├── user.py         # Student
│   │   ├── program.py      # Course, Cohort
│   │   ├── relationship.py # Registration, Enrollment
│   │   ├── content.py      # Assignment, Submission
│   │   └── tracking.py     # Attendance, Certificate, SyncLog
│   ├── views.py            # View controllers
│   ├── services.py         # Google API integration
│   ├── admin.py            # Django admin customization
│   ├── urls.py             # URL routing
│   ├── management/commands/ # CLI commands
│   │   ├── sync.py        # Data sync command
│   │   ├── seed.py        # Database seeding
│   │   └── cohort_stats.py # Cohort statistics
│   ├── templates/          # HTML templates with Tailwind
│   ├── templatetags/       # Custom template filters
│   └── fixtures/           # Fixture data (cohorts.json)
├── project/                 # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── docs/                    # Documentation
├── logs/                    # Application logs
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
├── pyproject.toml          # uv package config
├── README.md               # Main readme
├── DEPLOYMENT.md           # Deployment guide
├── SYNC_SETUP.md           # Sync setup instructions
├── Caddyfile               # Caddy web server config
├── Procfile                # Heroku/deployment config
├── d4wee.service           # systemd service file
├── d4wee-sync.service      # systemd sync service
└── d4wee-sync.timer        # systemd timer for automated sync
```

## Important Business Logic (Fat Models)

Models contain rich business logic as properties and methods:

### Registration Properties
- `.certificate_eligible` - checks 75% attendance, 50% score, all tests
- `.session_attendance_rate` - calculates attendance percentage
- `.overall_completion_rate` - average across enrollments
- `.overall_average_score` - average score across enrollments
- `.eligibility_notes` - reasons for certificate ineligibility
- `.approve(admin_user)` - approve registration
- `.decline(admin_user, reason)` - decline registration
- `.activate()` - move from approved to active
- `.complete()` - mark as completed (if eligible)

### Enrollment Properties
- `.category` - FOCUS/PUSH/PRAISE categorization
- `.completion_rate` - overall completion percentage
- `.pre_test_attempted`, `.pre_test_score` - pre-test metrics
- `.post_test_attempted`, `.post_test_score` - post-test metrics
- `.improvement_rate` - improvement from pre to post test
- `.assignment_completion_rate` - assignment completion %
- `.assignment_average_score` - average score for assignments
- `.quiz_average_score` - average score for quizzes
- `.overall_average_score` - average across assignments and quizzes
- `.missing_assignments_count` - count of missing assignments
- `.late_assignments_count` - count of late submissions
- `.on_time_rate` - percentage submitted on time

### Cohort Properties
- `.is_active` - checks if current date within start/end range
- `.total_weeks` - calculates weeks in cohort
- `.current_registrations_count` - count of approved/active registrations
- `.can_accept_registrations` - checks limits and open status

### Course Properties
- `.has_classroom_integration` - checks if linked to Google Classroom

## URL Routes

| Route | View | Access | Description |
|-------|------|--------|-------------|
| `/` | dashboard | Public/Auth | Landing page or user dashboard |
| `/profile/` | profile | Auth | User profile |
| `/courses/` | courses | Staff | Course list |
| `/students/` | students_list | Staff | Student list |
| `/cohorts/` | cohorts | Auth | Cohort list |
| `/cohort/<id>/` | cohort_detail | Auth | Cohort detail page |
| `/course/<id>/` | course_detail | Auth | Course detail page |
| `/student/<google_id>/` | student_detail | Staff | Student detail page |
| `/attendance/` | attendance | Auth | Attendance tracking |
| `/issues/` | issues | Staff | Issue tracking |
| `/issues/attendance-emails/` | attendance_mismatches | Staff | Email mismatch issues |

## Data Sync Strategy

### Sync Command

**Local Development (using uv):**
```bash
uv run python manage.py sync [--clear]
```

**Production:**
```bash
python manage.py sync [--clear]
```

### Sync Behavior
- Targets **only the currently active cohort** (determined by date range)
- Protects historical data from past/closed cohorts
- `--clear` flag only clears active cohort data before syncing
- Syncs from multiple sources:
  - Google Classroom API (courses, students, assignments, submissions)
  - Google Sheets (attendance data)

### Management Commands Available

| Command | Purpose | Example |
|---------|---------|---------|
| `sync` | Sync data for active cohort | `uv run python manage.py sync` |
| `sync_old_data` | One-time migration (historical) | `uv run python manage.py sync_old_data --user EMAIL` |
| `seed` | Initialize database with fixtures | `uv run python manage.py seed` |
| `cohort_stats` | Display cohort statistics | `uv run python manage.py cohort_stats` |
| `sync_courses` | Sync only courses | `uv run python manage.py sync_courses` |
| `sync_students` | Sync only students | `uv run python manage.py sync_students` |
| `sync_assignments` | Sync only assignments | `uv run python manage.py sync_assignments` |
| `sync_submissions` | Sync only submissions | `uv run python manage.py sync_submissions` |

### Sync Process
1. Identifies active cohort (current date within start/end range)
2. Fetches courses from Google Classroom
3. Assigns unassigned courses to active cohort
4. Syncs students (creates Student records, links to enrollments)
5. Syncs assignments (creates Assignment records)
6. Syncs submissions (creates/updates Submission records)
7. Syncs attendance from Google Sheets
8. Calculates student metrics
9. Creates SyncLog record

### Automated Sync
- Configured via systemd timer (`d4wee-sync.timer`)
- Runs at 2:00 AM daily with 0-15 min randomized delay
- Logs to `/var/log/d4wee/sync_YYYYMMDD_HHMMSS.log` (Linux)
- Logs to `logs/sync_YYYYMMDD_HHMMSS.log` (Windows)

## Deployment Details

### Production Environment
- **Server**: DigitalOcean VPS
- **Domain**: d4wee.codeforpakistan.org
- **Web Server**: Caddy (reverse proxy + static file serving)
- **App Server**: Gunicorn
- **Database**: PostgreSQL
- **Service Management**: systemd
  - `d4wee.service` - Django application
  - `d4wee-sync.service` - Sync job
  - `d4wee-sync.timer` - Sync scheduler

### Deployment Process
```bash
cd /root/d4wee
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart d4wee.service
```

### Management Commands

```bash
# Sync data for default teacher account
python manage.py sync

# Sync and clear active cohort data first
python manage.py sync --clear

# Sync for specific user
python manage.py sync --user teacher@codeforpakistan.org

# Show cohort statistics  
python manage.py cohort_stats

# Seed initial data (cohorts, courses)
python manage.py seed

# Run development server
python manage.py runserver
```

### Service Management
```bash
# Application service
sudo systemctl start d4wee.service
sudo systemctl stop d4wee.service
sudo systemctl restart d4wee.service
sudo systemctl status d4wee.service

# Sync timer
sudo systemctl start d4wee-sync.timer
sudo systemctl stop d4wee-sync.timer
sudo systemctl status d4wee-sync.timer
sudo systemctl list-timers d4wee-sync.timer

# View sync logs
sudo journalctl -u d4wee-sync.service -f
sudo journalctl -u d4wee-sync.service --since today
```

## Key Environment Variables

Set in `.env` file:

```bash
SECRET_KEY=<django-secret-key>
DEBUG=True/False
ALLOWED_HOSTS=d4wee.codeforpakistan.org,*.ondigitalocean.app
DATABASE_URL=postgresql://user:pass@host:port/dbname  # Optional, falls back to SQLite
```

## Google API Integration

### Required OAuth Scopes
- `profile` - User profile
- `email` - User email
- `classroom.courses.readonly` - Read classroom courses
- `classroom.rosters.readonly` - Read student rosters
- `classroom.coursework.students.readonly` - Read coursework
- `classroom.student-submissions.students.readonly` - Read submissions
- `classroom.profile.emails` - Student email addresses
- `spreadsheets.readonly` - Read Google Sheets (attendance)
- `drive.readonly` - Read Google Drive files

### Service Account Setup
1. Google Cloud Console: https://console.cloud.google.com/apis/credentials
2. Project: code4pk
3. OAuth 2.0 Client ID configured with redirect URIs
4. Tokens stored via django-allauth's SocialToken model

## Important Notes

- **Fat Model Philosophy**: Business logic lives in model properties/methods, not views
- **Active Cohort Protection**: Sync operations only affect the currently active cohort (date-based)
- **OAuth Token Management**: django-allauth handles token refresh automatically
- **Static Files**: 
  - Development: Served by Django + Whitenoise
  - Production: Served by Caddy with long cache headers
- **Database**: SQLite for dev, PostgreSQL for production (configurable via DATABASE_URL)
- **Time Zones**: Uses Django's timezone utilities for all date/time operations
- **Authentication**: 
  - Staff users see admin dashboard
  - Regular users see student dashboard
  - Unauthenticated users see public landing page

## Student Categorization Logic

Students are automatically categorized based on their performance:

### FOCUS (Needs Attention)
- Assignment completion rate < 60%, OR
- Average score < 60%

### PUSH (Needs Encouragement)
- Assignment completion rate 60-85%, OR
- Average score 60-85%

### PRAISE (Excellent Performance)
- Assignment completion rate ≥ 85%, AND
- Average score ≥ 85% (or no scores yet)

## Certificate Eligibility Criteria

To be eligible for a certificate, a student must meet ALL of these requirements:

1. **Attendance**: ≥ 75% session attendance rate
2. **Average Score**: ≥ 50% overall average score
3. **Pre-tests**: Must have attempted pre-test for ALL enrolled courses
4. **Post-tests**: Must have attempted post-test for ALL enrolled courses

If ineligible, the `Registration.eligibility_notes` property explains why.

## Development Workflow

### Local Setup
1. Clone repository
2. Create virtual environment: `uv venv` or `python -m venv .venv`
3. Activate: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux)
4. Install dependencies: `uv pip install -r requirements.txt`
5. Create `.env` file with environment variables
6. Run migrations: `python manage.py migrate`
7. Seed data: `python manage.py seed`
8. Create superuser: `python manage.py createsuperuser`
9. Run server: `python manage.py runserver`
10. Visit: http://localhost:8000

### Testing Sync
```bash
# Dry run (don't clear)
python manage.py sync

# Full sync with clear
python manage.py sync --clear

# Check sync logs in database
# Visit admin panel: http://localhost:8000/admin/app/synclog/
```

## Troubleshooting

### Sync Issues
- Check user has Google OAuth connected: Admin → Social Accounts
- Verify OAuth scopes are correct in settings.py
- Check sync logs: `python manage.py cohort_stats`
- Manual test: Access Google Classroom API via admin user

### Attendance Mismatches
- Visit `/issues/attendance-emails/` to see email mismatches
- Attendance records use email matching to link to students
- Fix by updating student email or attendance sheet

### Certificate Eligibility
- Check `Registration.eligibility_notes` for specific reasons
- Verify attendance data is synced
- Ensure pre/post tests are correctly categorized in assignments

---

**Last Updated**: May 23, 2026
