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
    list_display = ['student', 'cohort', 'status', 'requested_date', 'approved_by_display', 'approved_date']
    list_filter = ['status', 'cohort', 'requested_date']
    search_fields = ['student__full_name', 'student__email', 'cohort__name']
    date_hierarchy = 'requested_date'
    readonly_fields = ['created_at', 'updated_at', 'requested_date', 'approved_date', 'approved_by']
    list_per_page = 50
    actions = ['approve_registrations', 'reject_registrations']
    
    fieldsets = (
        ('Registration Details', {
            'fields': ('student', 'cohort', 'status')
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approved_date', 'notes')
        }),
        ('Timestamps', {
            'fields': ('requested_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def approved_by_display(self, obj):
        """Display who approved/rejected"""
        if obj.approved_by:
            return obj.approved_by.username
        return '-'
    approved_by_display.short_description = 'Approved By'
    
    @admin.action(description='✅ Approve selected registrations')
    def approve_registrations(self, request, queryset):
        """Bulk approve registrations"""
        count = 0
        for registration in queryset.filter(status='PENDING'):
            registration.approve(request.user)
            count += 1
        self.message_user(request, f'Successfully approved {count} registration(s).')
    
    @admin.action(description='❌ Reject selected registrations')
    def reject_registrations(self, request, queryset):
        """Bulk reject registrations"""
        count = 0
        for registration in queryset.filter(status='PENDING'):
            registration.reject(request.user, reason="Rejected by admin")
            count += 1
        self.message_user(request, f'Successfully rejected {count} registration(s).')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'cohort', 'status', 'enrolled_date']
    list_filter = ['status', 'cohort', 'course']
    search_fields = ['student__full_name', 'student__email', 'course__name']
    readonly_fields = ['created_at', 'updated_at', 'enrolled_date']
    date_hierarchy = 'enrolled_date'


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title_short', 'course', 'assignment_type', 'work_type', 'max_points', 'due_date']
    list_filter = ['course', 'assignment_type', 'work_type']
    search_fields = ['title', 'google_id']
    date_hierarchy = 'due_date'
    readonly_fields = ['google_id', 'created_at', 'updated_at']
    
    def title_short(self, obj):
        return obj.title[:100]
    title_short.short_description = 'Title'
    title_short.admin_order_field = 'title'


class HasGradeFilter(admin.SimpleListFilter):
    title = 'grading status'
    parameter_name = 'has_grade'
    
    def lookups(self, request, model_admin):
        return (
            ('graded', 'Graded (has assigned grade)'),
            ('ungraded', 'Ungraded (no grade)'),
            ('non_zero', 'Non-zero grades'),
            ('zero', 'Zero grades'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'graded':
            return queryset.filter(assigned_grade__isnull=False)
        if self.value() == 'ungraded':
            return queryset.filter(assigned_grade__isnull=True)
        if self.value() == 'non_zero':
            return queryset.filter(assigned_grade__gt=0)
        if self.value() == 'zero':
            return queryset.filter(assigned_grade=0)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'assignment_title', 'state', 'assigned_grade', 'max_points', 'percentage', 'late']
    list_filter = [HasGradeFilter, 'state', 'late', 'assignment__assignment_type', 'assignment__course']
    search_fields = ['enrollment__student__full_name', 'assignment__title']
    readonly_fields = ['google_id', 'created_at', 'updated_at']
    
    def student_name(self, obj):
        return obj.enrollment.student.full_name
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'enrollment__student__full_name'
    
    def assignment_title(self, obj):
        return obj.assignment.title[:100]
    assignment_title.short_description = 'Assignment'
    assignment_title.admin_order_field = 'assignment__title'
    
    def max_points(self, obj):
        return obj.assignment.max_points
    max_points.short_description = 'Max Points'
    
    def percentage(self, obj):
        if obj.grade_percentage is not None:
            return f'{obj.grade_percentage:.1f}%'
        return '-'
    percentage.short_description = 'Grade %'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'cohort', 'date', 'hours_spent']
    list_filter = ['cohort', 'date']
    search_fields = ['student__full_name', 'student__email']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'cohort_name', 'certificate_type', 'course', 'issued_date', 'completion_percentage', 'has_file']
    list_filter = ['certificate_type', 'issued_date', 'registration__cohort']
    search_fields = ['registration__student__full_name', 'course__name', 'registration__cohort__name']
    date_hierarchy = 'issued_date'
    readonly_fields = ['created_at', 'updated_at']
    
    def student_name(self, obj):
        return obj.registration.student.full_name
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'registration__student__full_name'
    
    def cohort_name(self, obj):
        return obj.registration.cohort.name
    cohort_name.short_description = 'Cohort'
    cohort_name.admin_order_field = 'registration__cohort__name'
    
    def has_file(self, obj):
        return bool(obj.certificate_file or obj.certificate_url)
    has_file.short_description = 'Has File/URL'
    has_file.boolean = True


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['cohort', 'status', 'started_at', 'completed_at', 'courses_synced', 'students_synced']
    list_filter = ['status', 'cohort', 'started_at']
    readonly_fields = ['started_at', 'completed_at', 'courses_synced', 'students_synced', 'assignments_synced', 'submissions_synced', 'errors']
    date_hierarchy = 'started_at'


