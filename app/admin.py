from django.contrib import admin
from .models import (
    Student, Course, Cohort, Registration, Enrollment,
    Assignment, Submission, Attendance, Certificate, SyncLog
)


# Customize admin site headers
admin.site.site_header = 'D4WEE Administration'
admin.site.site_title = 'D4WEE Admin'
admin.site.index_title = 'Welcome to D4WEE Administration'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'is_pilot_student', 'has_account', 'city', 'created_at']
    search_fields = ['full_name', 'given_name', 'family_name', 'email', 'google_id', 'unique_id']
    list_filter = ['is_pilot_student', 'city', 'created_at']
    readonly_fields = ['google_id', 'created_at', 'updated_at']
    
    def has_account(self, obj):
        return obj.user is not None
    has_account.short_description = 'Django Account'
    has_account.boolean = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'section', 'course_state', 'is_visible', 'created_at']
    list_filter = ['course_state', 'is_visible']
    search_fields = ['name', 'section', 'google_id']
    list_editable = ['is_visible']
    readonly_fields = ['google_id', 'created_at', 'updated_at']


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'status', 'is_open_for_registration', 'max_students']
    list_filter = ['status', 'is_open_for_registration']
    search_fields = ['name']
    list_editable = ['is_open_for_registration']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['student', 'cohort', 'status', 'requested_date']
    list_filter = ['status', 'cohort', 'requested_date']
    search_fields = ['student__full_name', 'student__email', 'cohort__name']
    list_editable = ['status']
    date_hierarchy = 'requested_date'
    readonly_fields = ['created_at', 'updated_at', 'requested_date', 'approved_date']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'cohort', 'status', 'enrolled_date']
    list_filter = ['status', 'cohort', 'course']
    search_fields = ['student__full_name', 'student__email', 'course__name']
    readonly_fields = ['created_at', 'updated_at', 'enrolled_date']
    date_hierarchy = 'enrolled_date'


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'assignment_type', 'work_type', 'max_points', 'due_date']
    list_filter = ['course', 'assignment_type', 'work_type']
    search_fields = ['title', 'google_id']
    date_hierarchy = 'due_date'
    readonly_fields = ['google_id', 'created_at', 'updated_at']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'assignment', 'state', 'assigned_grade', 'late']
    list_filter = ['state', 'late', 'assignment__course']
    search_fields = ['enrollment__student__full_name', 'assignment__title']
    readonly_fields = ['google_id', 'created_at', 'updated_at']
    
    def student_name(self, obj):
        return obj.enrollment.student.full_name
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'enrollment__student__full_name'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'cohort', 'date', 'hours_spent']
    list_filter = ['cohort', 'date']
    search_fields = ['student__full_name', 'student__email']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'certificate_type', 'course', 'issued_date', 'completion_percentage']
    list_filter = ['certificate_type', 'issued_date']
    search_fields = ['registration__student__full_name', 'course__name']
    date_hierarchy = 'issued_date'
    readonly_fields = ['created_at', 'updated_at']
    
    def student_name(self, obj):
        return obj.registration.student.full_name
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'registration__student__full_name'


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['cohort', 'status', 'started_at', 'completed_at', 'courses_synced', 'students_synced']
    list_filter = ['status', 'cohort', 'started_at']
    readonly_fields = ['started_at', 'completed_at', 'courses_synced', 'students_synced', 'assignments_synced', 'submissions_synced', 'errors']
    date_hierarchy = 'started_at'


