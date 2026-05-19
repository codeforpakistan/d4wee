from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Student, Course, Cohort, Registration, Enrollment,
    Assignment, Submission, Attendance, Certificate, SyncLog
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'city', 'created_at']
    search_fields = ['full_name', 'email', 'google_id', 'unique_id']
    list_filter = ['city', 'created_at']
    readonly_fields = ['user', 'google_id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('User Account', {
            'fields': ['user', 'google_id']
        }),
        ('Personal Information', {
            'fields': ['full_name', 'email', 'profile_photo', 'city', 'unique_id']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'status', 'is_visible', 'has_classroom']
    list_filter = ['status', 'is_visible']
    search_fields = ['code', 'name', 'google_id']
    list_editable = ['is_visible']
    readonly_fields = ['google_id', 'created_at', 'updated_at']
    
    def has_classroom(self, obj):
        return '✓' if obj.has_classroom_integration else '✗'
    has_classroom.short_description = 'Google Classroom'
    
    fieldsets = [
        ('Course Information', {
            'fields': ['code', 'name', 'description']
        }),
        ('Status', {
            'fields': ['status', 'is_visible']
        }),
        ('Google Classroom', {
            'fields': ['google_id'],
            'description': 'Linked Google Classroom course ID'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'status', 'is_open_for_registration', 'max_students', 'total_weeks']
    list_filter = ['status', 'is_open_for_registration', 'start_date']
    search_fields = ['name', 'description']
    list_editable = ['is_open_for_registration']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at', 'total_weeks_display']
    
    def total_weeks_display(self, obj):
        return obj.total_weeks
    total_weeks_display.short_description = 'Total Weeks'
    
    fieldsets = [
        ('Cohort Information', {
            'fields': ['name', 'description']
        }),
        ('Schedule', {
            'fields': ['start_date', 'end_date', 'total_weeks_display']
        }),
        ('Status & Registration', {
            'fields': ['status', 'is_open_for_registration', 'max_students']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['student', 'cohort', 'status', 'requested_date', 'completion_date', 'certificate_eligible']
    list_filter = ['status', 'cohort', 'requested_date']
    search_fields = ['student__full_name', 'student__email', 'cohort__name']
    list_editable = ['status']
    date_hierarchy = 'requested_date'
    readonly_fields = ['created_at', 'updated_at', 'requested_date', 'approved_date', 'metrics_display']
    actions = ['approve_registrations', 'decline_registrations']
    
    def certificate_eligible(self, obj):
        return '✓' if obj.certificate_eligible else '✗'
    certificate_eligible.short_description = 'Certificate Eligible'
    certificate_eligible.boolean = True
    
    def metrics_display(self, obj):
        if obj.status != 'ACTIVE' and obj.status != 'COMPLETED':
            return 'N/A - Registration not active'
        
        return format_html(
            '<strong>Attendance:</strong> {:.0%}<br>'
            '<strong>Completion:</strong> {:.0%}<br>'
            '<strong>Average Score:</strong> {:.0%}<br>'
            '<strong>Courses:</strong> {} enrolled, {} completed<br>'
            '<strong>Certificate Eligible:</strong> {}<br>'
            '<strong>Notes:</strong> {}',
            obj.session_attendance_rate or 0,
            obj.overall_completion_rate or 0,
            obj.overall_average_score or 0,
            obj.courses_enrolled_count,
            obj.courses_completed_count,
            '✓' if obj.certificate_eligible else '✗',
            obj.eligibility_notes or 'N/A'
        )
    metrics_display.short_description = 'Performance Metrics'
    
    def approve_registrations(self, request, queryset):
        for registration in queryset.filter(status='PENDING'):
            registration.approve()
        self.message_user(request, f'{queryset.count()} registrations approved.')
    approve_registrations.short_description = 'Approve selected registrations'
    
    def decline_registrations(self, request, queryset):
        for registration in queryset.filter(status='PENDING'):
            registration.decline()
        self.message_user(request, f'{queryset.count()} registrations declined.')
    decline_registrations.short_description = 'Decline selected registrations'
    
    fieldsets = [
        ('Registration Information', {
            'fields': ['student', 'cohort', 'status']
        }),
        ('Dates', {
            'fields': ['requested_date', 'approved_date', 'completion_date']
        }),
        ('Performance Metrics', {
            'fields': ['metrics_display'],
            'description': 'Calculated metrics based on student performance'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'cohort', 'status', 'category', 'completion_rate_display', 'overall_average']
    list_filter = ['status', 'cohort', 'course']
    search_fields = ['student__full_name', 'student__email', 'course__name']
    readonly_fields = ['created_at', 'updated_at', 'metrics_display']
    
    def completion_rate_display(self, obj):
        return f'{obj.completion_rate:.0%}' if obj.completion_rate else 'N/A'
    completion_rate_display.short_description = 'Completion'
    
    def overall_average(self, obj):
        return f'{obj.overall_average_score:.0%}' if obj.overall_average_score else 'N/A'
    overall_average.short_description = 'Avg Score'
    
    def metrics_display(self, obj):
        return format_html(
            '<h3>Assessment Scores</h3>'
            '<strong>Pre-Test:</strong> {} ({})<br>'
            '<strong>Post-Test:</strong> {} ({})<br>'
            '<strong>Improvement:</strong> {}<br><br>'
            '<h3>Assignments</h3>'
            '<strong>Total:</strong> {}<br>'
            '<strong>Completed:</strong> {} ({:.0%})<br>'
            '<strong>Missing:</strong> {}<br>'
            '<strong>Late:</strong> {}<br>'
            '<strong>Average Score:</strong> {}<br><br>'
            '<h3>Quizzes</h3>'
            '<strong>Total:</strong> {}<br>'
            '<strong>Completed:</strong> {}<br>'
            '<strong>Average Score:</strong> {}<br><br>'
            '<h3>Overall</h3>'
            '<strong>Completion Rate:</strong> {:.0%}<br>'
            '<strong>On-Time Rate:</strong> {:.0%}<br>'
            '<strong>Overall Average:</strong> {}<br>'
            '<strong>Category:</strong> <span style="color: {};">{}</span>',
            f'{obj.pre_test_score:.0%}' if obj.pre_test_score else 'N/A',
            'Attempted' if obj.pre_test_attempted else 'Not attempted',
            f'{obj.post_test_score:.0%}' if obj.post_test_score else 'N/A',
            'Attempted' if obj.post_test_attempted else 'Not attempted',
            f'{obj.improvement_rate:.0%}' if obj.improvement_rate else 'N/A',
            obj.total_assignments,
            obj.completed_assignments,
            obj.assignment_completion_rate or 0,
            obj.missing_assignments_count,
            obj.late_assignments_count,
            f'{obj.assignment_average_score:.0%}' if obj.assignment_average_score else 'N/A',
            obj.total_quizzes,
            obj.completed_quizzes,
            f'{obj.quiz_average_score:.0%}' if obj.quiz_average_score else 'N/A',
            obj.completion_rate or 0,
            obj.on_time_rate or 0,
            f'{obj.overall_average_score:.0%}' if obj.overall_average_score else 'N/A',
            'green' if obj.category == 'PRAISE' else 'orange' if obj.category == 'PUSH' else 'red',
            obj.category
        )
    metrics_display.short_description = 'Detailed Metrics'
    
    fieldsets = [
        ('Enrollment Information', {
            'fields': ['student', 'course', 'cohort', 'registration', 'status']
        }),
        ('Performance Metrics', {
            'fields': ['metrics_display'],
            'description': 'All metrics are calculated on-the-fly from submissions and assignments'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'assignment_type', 'work_type', 'max_points', 'due_date']
    list_filter = ['course', 'assignment_type', 'work_type']
    search_fields = ['title', 'google_id']
    date_hierarchy = 'due_date'
    readonly_fields = ['google_id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Assignment Information', {
            'fields': ['title', 'description', 'course']
        }),
        ('Type & Classification', {
            'fields': ['assignment_type', 'work_type']
        }),
        ('Grading', {
            'fields': ['max_points', 'due_date']
        }),
        ('Google Classroom', {
            'fields': ['google_id'],
            'description': 'Linked Google Classroom assignment ID'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'assignment', 'state', 'assigned_grade', 'grade_percentage_display', 'late']
    list_filter = ['state', 'late', 'assignment__course', 'assignment__assignment_type']
    search_fields = ['enrollment__student__full_name', 'assignment__title', 'google_id']
    readonly_fields = ['google_id', 'grade_percentage_display', 'created_at', 'updated_at']
    
    def grade_percentage_display(self, obj):
        if obj.grade_percentage is not None:
            return f'{obj.grade_percentage:.0%}'
        return 'N/A'
    grade_percentage_display.short_description = 'Grade %'
    
    fieldsets = [
        ('Submission Information', {
            'fields': ['enrollment', 'assignment', 'state', 'late']
        }),
        ('Grading', {
            'fields': ['assigned_grade', 'draft_grade', 'grade_percentage_display']
        }),
        ('Google Classroom', {
            'fields': ['google_id'],
            'description': 'Linked Google Classroom submission ID'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'cohort', 'week_number', 'date', 'hours_spent']
    list_filter = ['cohort', 'week_number', 'date']
    search_fields = ['student__full_name', 'student__email']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Attendance Information', {
            'fields': ['student', 'cohort', 'week_number', 'date']
        }),
        ('Learning Time', {
            'fields': ['hours_spent'],
            'description': 'How many hours did the student spend learning this week?'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['registration', 'certificate_type', 'course', 'issued_date', 'completion_percentage']
    list_filter = ['certificate_type', 'issued_date']
    search_fields = ['registration__student__full_name', 'course__name']
    date_hierarchy = 'issued_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Certificate Information', {
            'fields': ['registration', 'certificate_type', 'course', 'issued_date']
        }),
        ('Performance', {
            'fields': ['completion_percentage']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['cohort', 'status', 'started_at', 'completed_at', 'courses_synced', 'students_synced', 'assignments_synced', 'submissions_synced']
    list_filter = ['status', 'cohort', 'started_at']
    readonly_fields = ['started_at', 'completed_at', 'courses_synced', 'students_synced', 'assignments_synced', 'submissions_synced', 'errors']
    date_hierarchy = 'started_at'
    
    fieldsets = [
        ('Sync Information', {
            'fields': ['cohort', 'status']
        }),
        ('Timing', {
            'fields': ['started_at', 'completed_at']
        }),
        ('Sync Counts', {
            'fields': ['courses_synced', 'students_synced', 'assignments_synced', 'submissions_synced']
        }),
        ('Errors', {
            'fields': ['errors'],
            'classes': ['collapse']
        }),
    ]

