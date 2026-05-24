# D4WEE Scripts Documentation

This folder contains utility scripts for development, debugging, and one-time migration tasks.

## 📁 Folder Structure

### `dev/` — Development & Migration Scripts

One-time scripts used during initial development and database migration. These are **historical reference only** and should not be needed after initial setup.

**Migration Scripts (one-time use):**
- `fetch_all_students.py` — Fetch all students from Google Classroom to JSON
- `fetch_classroom_data.py` — Fetch courses and basic data to JSON
- `fetch_pilot_assignments.py` — Fetch assignments/coursework to JSON
- `fetch_pilot_attendance.py` — Fetch attendance from Google Sheets to JSON
- `fetch_pilot_submissions.py` — Fetch student submissions to JSON
- `import_pilot_attendance.py` — Import attendance from JSON to database
- `fix_attendance_google_id.py` — Fix attendance Google ID mapping
- `assign_pilot_courses.py` — Assign courses to Pilot cohort

**Note:** These scripts were used to migrate historical data to the new PostgreSQL database. For new deployments, use the Django management command instead:
```bash
python manage.py sync_old_data
```

### `utils/` — Utility & Verification Scripts

Reusable scripts for checking data integrity, debugging, and administrative tasks.

**Verification Scripts:**
- `verify_enrollments.py` — Verify student enrollments are correct
- `verify_assignments.py` — Verify assignments are synced properly
- `verify_submissions.py` — Verify student submissions data
- `verify_attendance.py` — Verify attendance records

**Check/Debug Scripts:**
- `check_cohorts.py` — View cohort status and dates
- `check_enrollments.py` — Check enrollment data
- `check_grades.py` — Check student grades
- `check_pilot.py` — Check Pilot cohort data
- `check_student.py` — Look up individual student data

**Admin Utilities:**
- `list_courses.py` — List all courses in database
- `make_staff.py` — Make a user staff/superuser
- `pilot_complete_verification.py` — Complete verification of Pilot cohort
- `test_performance.py` — Test database query performance

## 🚀 Usage

### Running Scripts

All scripts are Django-aware. Run them from the project root:

```bash
# From project root
python scripts/utils/check_cohorts.py
python scripts/utils/verify_enrollments.py
python scripts/dev/fetch_all_students.py
```

Or use `uv run`:

```bash
uv run scripts/utils/check_cohorts.py
```

### When to Use These Scripts

**Use verification scripts:**
- After syncing data to verify correctness
- When debugging data issues
- To generate reports

**Use check scripts:**
- During development to inspect database state
- To debug specific data issues
- To understand current system status

**Do NOT use migration scripts:**
- After initial setup is complete
- Instead use: `python manage.py sync_old_data` for fresh deployments
- Keep migration scripts as reference/documentation only

## 📝 Django Management Commands vs Scripts

**Prefer Django management commands over standalone scripts:**

✅ **Use management commands:**
```bash
python manage.py seed           # Initial setup
python manage.py sync_old_data  # One-time historical data migration
python manage.py sync           # Regular data sync (future)
python manage.py cohort_stats   # View cohort statistics
```

⚠️ **Use standalone scripts:**
- Only for one-off debugging tasks
- When you need quick inspection without logging
- For development/experimentation

## 🗑️ Cleanup

After successful deployment and verification, you may archive the `dev/` folder since those scripts are one-time use only.
