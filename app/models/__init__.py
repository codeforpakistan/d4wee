# Import all models to make them available
from .user import Student
from .program import Course, Cohort
from .relationship import Registration, Enrollment
from .content import Assignment, Submission
from .tracking import Attendance, Certificate, SyncLog, AttendanceWeekly

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
    'SyncLog',
]
