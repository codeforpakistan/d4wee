# D4WEE Database Setup Guide

This document describes the complete sequence for setting up a fresh database instance, either for local development or production deployment.

## Prerequisites

- PostgreSQL database created (e.g., `d4wee`)
- `.env` file configured with `DATABASE_URL`
- Google OAuth credentials configured in `.env`
- `uv` package manager installed (for local development)
- Virtual environment activated (or using `uv run` commands)

## Initial Database Setup Sequence

### 1. Set Database Connection

Configure the PostgreSQL connection in `.env`:

```bash
DATABASE_URL=postgresql://username:password@host:port/d4wee
```

**Local Example:**
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/d4wee
```

**Production Example:**
```bash
DATABASE_URL=postgresql://user:pass@db-host.com:25060/d4wee?sslmode=require
```

### 2. Create PostgreSQL Database

If the database doesn't exist yet:

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database
CREATE DATABASE d4wee;

-- Grant permissions (if needed)
GRANT ALL PRIVILEGES ON DATABASE d4wee TO your_user;
```

### 3. Run Database Migrations

Apply all database schema migrations:

**Local Development (using uv):**
```bash
uv run python manage.py migrate
```

**Production:**
```bash
python manage.py migrate
```

**Local Development (using uv):**
```bash
uv run python manage.py seed
```

**Production:**
This creates all tables: courses, students, assignments, submissions, cohorts, attendance, etc.

### 4. Seed Initial Data

Load initial configuration and cohort data:

```bash
python manage.py seed
```

This command:
- ✅ Configures the Site for OAuth
- ✅ Sets up Google OAuth SocialApp with credentials from `.env`
- ✅ Creates default admin user (`admin` / `admin`)
- ✅ Loads cohort fixture (Pilot, Cohort 1-6)
- ✅ Displays which cohort is currently active

**Output Example:**
```
✅ Updated site to localhost:8000
✅ Created new Google OAuth app
✅ Added OAuth app to site: localhost:8000
✅ Created superuser: admin
📅 Setting up cohorts...
✅ Loaded 7 cohort(s)
✅ Active cohort: Cohort 1 (2026-06-01 to 2026-08-31)
```

   **Local Development (using uv):**
   ```bash
   uv run python manage.py runserver
   ```
   
   **Production:**
   
### 5. Authenticate with Google

Before syncing data, you need to authenticate:

1. Start the development server:
   ```bash
   python manage.py runserver
   ```

2. Visit `http://localhost:8000/admin/` and login with `admin` / `admin`

3. Navigate to **Social Accounts** → **Social Accounts** → **Add Social Account**
   - Or login with Google OAuth at `http://localhost:8000/accounts/login/`

4. Authenticate with your Google Classroom admin account (e.g., `teacher@codeforpakistan.org`)
**Local Development (using uv):**
```bash
uv run python manage.py sync_old_data --user teacher@codeforpakistan.org
```

**Production:**

5. Grant all requested permissions for Google Classroom access

### 6. Sync Historical Data from Google Classroom

After authentication, run the **one-time** migration command to populate the database with historical Google Classroom data:

```bash
python manage.py sync_old_data --user teacher@codeforpakistan.org
```

This command orchestrates the complete migration process:

**What it does:**
1. **Fetches** data from Google Classroom API → JSON files in `data/` folder
   - All courses
   - All students  
   - All assignments/coursework
   - Student submissions (samples)
   - Attendance from Google Sheet - Local
uv run python manage.py sync_old_data --user teacher@codeforpakistan.org

# Only fetch to JSON (for inspection) - Local
uv run python manage.py sync_old_data --user teacher@codeforpakistan.org --fetch-only

# Only import from existing JSON - Local
uv run python manage.py sync_old_data --user teacher@codeforpakistan.org --import-only

# Production (omit 'uv run')
python manage.py sync_old_data --user teacher@codeforpakistan.org

3. **Verifies** data integrity

**Command options:**
```bash
# Full migration (fetch + import)
python manage.py sync_old_data --user teacher@codeforpakistan.org

# Only fetch to JSON (for inspection)
python manage.py sync_old_data --user teacher@codeforpakistan.org --fetch-only
uv run python manage.py sync` for local, `python manage.py sync` for production
# Only import from existing JSON
python manage.py sync_old_data --user teacher@codeforpakistan.org --import-only
```

**Important Notes:**
- ⚠️ This is a **ONE-TIME** command for initial database setup
- ✅ Fetched data is saved to `data/` folder for inspection/debugging
- ✅ Safe to re-run with `--fetch-only` to refresh JSON files
- ⚠️ Do NOT use this for ongoing sync (use `python manage.py sync` instead - future)

**After successful migration:**

Check that data was loaded correctly:

```bash
# View cohort statistics
python manage.py cohort_stats

# Or check via Django admin
python manage.py runserver
# Visit http://localhost:8000/admin/
```

### 7. Verify Data
**Local Development (using uv):**
```bash
# View cohort statistics
uv run python manage.py cohort_stats

# Or use verification scripts
uv run python scripts/utils/verify_enrollments.py
uv run python manage.py runserver
# Visit http://localhost:8000/admin/
```

**Production:**
```bash
# View cohort statistics
python manage.py cohort_statsy
python scripts/utils/verify_assignments.py
python scripts/utils/verify_submissions.py
python scripts/utils/verify_attendance.py

# Or check via Django admin
python manage.py runserver
# Visit http://localhost:8000/admin/
```

## Production Deployment Sequence

For deploying to production (e.g., DigitalOcean):

```bash
# 1. SSH into server
ssh root@your-server.com

# 2. Navigate to application directory
cd /root/d4wee

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Set environment variables (edit .env file)
nano .env
# Add production DATABASE_URL, SECRET_KEY, etc.

# 5. Run migrations
python manage.py migrate

# 6. Seed initial data
python manage.py seed

# 7. Update site domain (production)
python manage.py shell
>>> from django.contrib.sites.models import Site
>>> site = Site.objects.get_current()
>>> site.domain = 'd4wee.codeforpakistan.org'
>>> site.name = 'D4WEE - Digital for Women Economic Empowerment'
>>> site.save()
>>> exit()

# 8. Collect static files
python manage.py collectstatic --noinput

# 9. Create certificates directory
mkdir -p certificates
chmod 755 certificates

# 10. Authenticate with Google (via web browser)
# Visit https://d4wee.codeforpakistan.org/accounts/login/
# Login with teacher@codeforpakistan.org

# 11. Run one-time historical data migration
python manage.py sync_old_data --user teacher@codeforpakistan.org
# This fetches all data from Google Classroom and imports to database

# 12. Verify data was loaded
python manage.py cohort_stats

# 13. Set up automated nightly sync (optional)
sudo cp d4wee-sync.service d4wee-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable d4wee-sync.timer
sudo systemctl start d4wee-sync.timer

# 13. Restart application
sudo systemctl restart d4wee.service
```

## Re-syncing Data

**For ongoing sync (after initial setup):**

⚠️ **TODO:** The regular `sync` command needs updates for the new database schema. For now:

```bash
# This command needs updates to work with new schema
python manage.py sync --user teacher@codeforpakistan.org

# Options:
# --clear: Clear existing data for active cohort before syncing
```

**Note:** The `sync_old_data` command is for **initial migration only**. Do not use it for regular updates.

**For re-fetching historical data:**

If you need to refresh the JSON files from Google Classroom:

```bash
python manage.py sync_old_data --user teacher@codeforpakistan.org --fetch-only
```

**For manual script access:**

```bash
# Check/debug scripts are in scripts/utils/
python scripts/utils/check_cohorts.py
python scripts/utils/check_enrollments.py
python scripts/utils/verify_enrollments.py

# Migration scripts are in scripts/dev/ (reference only)
python scripts/dev/fetch_all_students.py
```

## Troubleshooting

### OAuth Token Expired

If sync fails with authentication errors:

1. Delete existing social account in Django admin
2. Re-authenticate via `/accounts/login/`
3. Ensure "prompt: consent" forces refresh token

### No Active Cohort

If you see "No active cohort found":

1. Check cohort dates in admin panel
2. Ensure current date falls within a cohort's start/end date
3. Update cohort dates if needed

### Database Connection Errors

Check your `DATABASE_URL` format:

```bash
# PostgreSQL format
postgresql://user:password@host:port/database

# With SSL (production)
postgresql://user:password@host:port/database?sslmode=require
```

### Permission Errors

If Google Classroom API returns permission errors:

1. Verify all required scopes are in `settings.py`
2. Re-authenticate to grant new permissions
3. Check Google Cloud Console API enablement
4. Verify service account credentials (if using service account)

## Environment Variables Reference

Required variables in `.env`:

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database
DATABASE_URL=postgresql://user:pass@host:port/d4wee

# Google OAuth
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_OAUTH2_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH2_CLIENT_SECRET=your-client-secret

# Admin
ADMIN_EMAIL=admin@example.com
```

## Next Steps

After initial setup:

1. ✅ Configure automated nightly sync (see [SYNC_SETUP.md](SYNC_SETUP.md))
2. ✅ Set up Caddy for static file serving (see [DEPLOYMENT.md](DEPLOYMENT.md))
3. ✅ Configure SSL certificates
4. ✅ Set up monitoring and logging
5. ✅ Create additional admin users if needed

---

## Quick Reference: Initial Data Migration

The D4WEE initial setup uses a **Django management command** for one-time historical data migration:

### Command Workflow

```bash
python manage.py sync_old_data --user teacher@codeforpakistan.org
```

This command:
1. **Fetches** data from Google Classroom API → `data/` folder (JSON files)
2. **Imports** data from JSON files → PostgreSQL database
3. **Verifies** data integrity

### Data Flow Diagram

```
Google Classroom API
        ↓
  [sync_old_data command - FETCH]
        ↓
  data/*.json files  ← You can inspect these!
        ↓
  [sync_old_data command - IMPORT]
        ↓
PostgreSQL Database
```

### JSON Files Created

| File | Content |
|------|---------|
| `data/google_classroom_courses.json` | All courses |
| `data/all_students.json` | All students (unique by userId) |
| `data/pilot_assignments.json` | All assignments/coursework |
| `data/pilot_submissions_sample.json` | Student submissions (samples) |
| `data/pilot_attendance.json` | Attendance records from Google Sheets |

### Benefits of Two-Step Process

- ✅ Can inspect fetched data before importing
- ✅ Can re-import without re-fetching (saves API calls)
- ✅ Easier debugging if API or import fails
- ✅ Preserves raw Google Classroom data structure for reference

### Migration Scripts (Historical Reference)

Old standalone migration scripts are archived in `scripts/dev/`:
- `fetch_all_students.py`
- `fetch_classroom_data.py`
- `fetch_pilot_assignments.py`
- `fetch_pilot_submissions.py`
- `fetch_pilot_attendance.py`

**These are reference only.** Use the management command instead:
```bash
python manage.py sync_old_data
```

### Utility Scripts

Verification and debugging scripts are in `scripts/utils/`:
- `verify_enrollments.py` — Verify student enrollments
- `verify_assignments.py` — Verify assignments
- `verify_submissions.py` — Verify submissions
- `verify_attendance.py` — Verify attendance
- `check_cohorts.py` — View cohort status
- `check_enrollments.py` — Check enrollment data
- Plus more debugging utilities

See [scripts/README.md](scripts/README.md) for complete documentation.
