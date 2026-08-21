# Import all models to make them available
from .assignment import Assignment
from .submission import Submission
from .enrollment import Enrollment
from .course import Course
from .cohort import Cohort
from .registration import Registration
from .attendance import Attendance
from .certificate import Certificate
from .synclog import SyncLog
from .student import Student
from .views import AttendanceWeekly, StudentGrades

# Export all models
__all__ = [
    'Student',
    'Course',
    'Cohort',
    'Registration',
    'Enrollment',
    'Assignment',
    'Submission',
    'Attendance',
    'AttendanceWeekly',
    'Certificate',
    'StudentGrades',
    'SyncLog',
]
