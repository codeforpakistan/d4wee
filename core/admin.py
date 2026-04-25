from django.contrib import admin
from .models import (
    Cohort, Course, Student, Assignment, Submission, 
    StudentMetrics, SyncLog, CohortEnrollment, Certificate
)


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active', 'is_closed', 'data_archived', 'course_count', 'enrollment_count']
    list_filter = ['is_active', 'is_closed', 'data_archived', 'start_date']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'is_closed', 'data_archived']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']
    
    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = 'Courses'
    
    def enrollment_count(self, obj):
        return obj.enrollments.count()
    enrollment_count.short_description = 'Enrollments'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'cohort', 'section', 'course_state', 'created_at']
    list_filter = ['cohort', 'course_state']
    search_fields = ['name', 'section', 'google_id']
    date_hierarchy = 'created_at'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'course', 'created_at']
    list_filter = ['course']
    search_fields = ['full_name', 'email', 'google_id']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'work_type', 'max_points', 'due_date']
    list_filter = ['course', 'work_type', 'state']
    search_fields = ['title', 'topic']
    date_hierarchy = 'due_date'


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'state', 'assigned_grade', 'late']
    list_filter = ['state', 'late', 'assignment__course']
    search_fields = ['student__full_name', 'assignment__title']


@admin.register(StudentMetrics)
class StudentMetricsAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'completion_rate', 'average_score', 'category']
    list_filter = ['category', 'course']
    search_fields = ['student__full_name']


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'started_at', 'completed_at', 'courses_synced', 'students_synced']
    list_filter = ['status', 'started_at']
    readonly_fields = ['started_at', 'completed_at', 'courses_synced', 'students_synced', 'assignments_synced', 'submissions_synced', 'errors']


@admin.register(CohortEnrollment)
class CohortEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'student_email', 'cohort', 'status', 'enrollment_date', 'completion_date']
    list_filter = ['cohort', 'status', 'enrollment_date']
    search_fields = ['student_name', 'student_email', 'student_google_id']
    list_editable = ['status']
    date_hierarchy = 'enrollment_date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'cohort', 'course', 'certificate_type', 'issued_date', 'completion_percentage', 'average_grade']
    list_filter = ['cohort', 'certificate_type', 'issued_date']
    search_fields = ['student_name', 'student_email', 'student_google_id']
    date_hierarchy = 'issued_date'
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Student Information', {
            'fields': ['student_google_id', 'student_name', 'student_email']
        }),
        ('Certificate Details', {
            'fields': ['cohort', 'course', 'certificate_type', 'issued_date']
        }),
        ('Performance Metrics', {
            'fields': ['completion_percentage', 'average_grade']
        }),
        ('Certificate Files', {
            'fields': ['certificate_url', 'certificate_file']
        }),
        ('Additional Information', {
            'fields': ['notes', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
