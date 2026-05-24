# D4WEE - Digital for Women's Economic Empowerment

Learning Management System for UN Women/Code for Pakistan

## Tech Stack

- **Backend**: Django 5.2
- **Authentication**: django-allauth (Google OAuth)
- **API Integration**: Google Classroom API, Google Sheets API
- **Database**: PostgreSQL
- **Frontend**: Tailwind CSS
- **Package Manager**: uv
- **Deployment**: Gunicorn + Caddy, systemd timers
- **Hosting**: DigitalOcean (d4wee.codeforpakistan.org)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Google Cloud Console project with OAuth credentials
- `uv` package manager

### Installation

1. **Install Dependencies**

   ```bash
   uv sync
   ```

2. **Configure Environment Variables**

   Create a `.env` file with:
   ```env
   SECRET_KEY=your-secret-key
   DATABASE_URL=postgresql://user:pass@localhost:5432/d4wee
   GOOGLE_OAUTH_CLIENT_ID=your-client-id
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
   ALLOWED_HOSTS=localhost,127.0.0.1
   DEBUG=True
   ```

3. **Setup Database**

   ```bash
   # Run migrations
   uv run python manage.py migrate
   
   # Seed initial data (creates admin user, cohorts, etc.)
   uv run python manage.py seed
   ```

4. **Run Development Server**

   ```bash
   uv run python manage.py runserver
   ```

5. **Access the Application**

   - Open http://localhost:8000
   - Login with `admin` / `admin` or sign in with Google
   - Navigate to dashboard to view cohorts, courses, and students

### Initial Data Migration

For first-time setup, sync historical data from Google Classroom:

```bash
uv run python manage.py sync_old_data --user teacher@codeforpakistan.org
```

This command fetches and imports all historical data (courses, students, assignments, submissions, attendance).

## Key Features

### Cohort-Based Learning
- Time-bound training programs (typically 3 months)
- Student registration workflow: PENDING → APPROVED → ACTIVE → COMPLETED
- Certificate eligibility tracking (75% attendance + 50% avg score + all tests attempted)

### Student Progress Tracking
- **Completion Rates**: Track assignment and course completion
- **Performance Metrics**: Average scores, improvement rates (pre-test to post-test)
- **Student Categorization**:
  - **FOCUS**: <60% completion or <60% scores
  - **PUSH**: 60-85% completion/scores
  - **PRAISE**: >85% completion and >85% scores

### Google Classroom Integration
- Automatic sync of courses, students, assignments, and submissions
- Google Sheets integration for attendance tracking
- OAuth authentication via Google
- Nightly automated sync (production only)

### Staff Dashboard
- CManagement Commands

| Command | Purpose |
|---------|---------|
| `uv run python manage.py seed` | Initialize database with fixtures |
| `uv run python manage.py sync` | Sync data for active cohort |
| `uv run python manage.py sync --clear` | Clear and re-sync active cohort |
| `uv run python manage.py sync_old_data --user EMAIL` | One-time historical data migration |
| `uv run python manage.py cohort_stats` | Display cohort statistics |
| `uv run python manage.py sync_courses` | Sync only courses |
| `uv run python manage.py sync_students` | Sync only students |
| `uv run python manage.py sync_assignments` | Sync only assignments |
| `uv run python manage.py sync_submissions` | Sync only submissions |

> **Note**: In production, omit the `uv run` prefix and use `python manage.py` directly.

## Documentation

For detailed information, see the documentation in the `/docs` folder:

- **[DATABASE_SETUP.md](docs/DATABASE_SETUP.md)** - Complete database setup guide for local and production
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deployment instructions for production server
- **[PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)** - Comprehensive project architecture and data model documentation
- **[SYNC_SETUP.md](docs/SYNC_SETUP.md)** - Automated sync configuration with systemd timers

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
│   ├── templates/          # HTML templates with Tailwind
│   └── fixtures/           # Fixture data (cohorts.json)
├── project/                 # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── data/                    # JSON data exports
├── logs/                    # Application logs
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
├── pyproject.toml          # uv package config
├── Caddyfile               # Caddy web server config
├── d4wee.service           # systemd service file
├── d4wee-sync.service      # systemd sync service
└── d4wee-sync.timer        # systemd timer for automated sync
```

## License

Built for UN Women by Code for Pakistannt variables (Google OAuth credentials)
├── db.sqlite3          # SQLite database
├── manage.py           # Django management script
└── pyproject.toml      # uv dependencies
```

## How It Works

### Authentication Flow

1. User clicks "Sign in with Google"
2. django-allauth handles OAuth flow
3. User authorizes Google Classroom scopes
4. OAuth tokens are stored in database
5. Tokens are used to access Google Classroom API

### Data Sync Flow

1. User clicks "Sync Data" button
2. System fetches all courses from Google Classroom
3. For each course:
   - Fetch students
   - Fetch assignments with due dates
   - Fetch student submissions with grades
4. Calculate metrics for each student:
   - Completion rate (% of assignments submitted)
   - Average score (across graded assignments)
   - On-time rate (% submitted before due date)
   - Late submission count
   - Missing assignment count
5. Categorize students based on performance
6. Display updated data in dashboard

## Next Steps (Phase 2)

- Individual student detail view
- Timeline progress tracking
- Topic/area performance analysis
- Charts and visualizations
- Export functionality
- Email notifications
- Mobile responsive design improvements

## Troubleshooting

### OAuth Error: "User is not connected to Google Classroom"

**Solution**: Sign out and sign back in. The OAuth tokens need to be stored in the database.

1. Visit http://localhost:8000/debug-auth/ to check token status
2. If `social_token` shows "Not found", sign out and sign in again
3. You'll see the Google consent screen again (this is expected)
4. After signing in, verify at /debug-auth/ that `has_refresh_token: true`

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed diagnostics.

### OAuth Error: redirect_uri_mismatch

Make sure you added `http://localhost:8000/accounts/google/login/callback/` to authorized redirect URIs in Google Cloud Console.

### No data showing

Click "Sync Data" button after signing in to import Google Classroom data.

### Module not found errors

Run: `uv pip install <missing-module>`

## Development Commands

```bash
# Run development server
.venv\Scripts\python manage.py runserver

# Sync Google Classroom data via command line
.venv\Scripts\python manage.py sync_classroom --user <your-email@domain.com>

# Sync with clearing old data first
.venv\Scripts\python manage.py sync_classroom --user <your-email@domain.com> --clear

# Setup Google OAuth configuration
.venv\Scripts\python manage.py seed

# Create migrations after model changes
.venv\Scripts\python manage.py makemigrations

# Apply migrations
.venv\Scripts\python manage.py migrate

# Create superuser for Django admin
.venv\Scripts\python manage.py createsuperuser

# Django shell (for testing)
.venv\Scripts\python manage.py shell
```

## API Scopes

The application requests these Google Classroom API scopes:

- `profile` - User profile information
- `email` - User email address
- `classroom.courses.readonly` - Read course information
- `classroom.rosters.readonly` - Read student rosters
- `classroom.coursework.students.readonly` - Read assignments
- `classroom.student-submissions.students.readonly` - Read student submissions and grades
