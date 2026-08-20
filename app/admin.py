from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.html import format_html
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
    change_list_template = 'admin/app/student/change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-students/', self.admin_site.admin_view(self.sync_students_view), name='sync_students'),
        ]
        return custom_urls + urls
    
    def sync_students_view(self, request):
        from django.core.management import call_command
        from io import StringIO
        import re
        
        # Capture the command output
        out = StringIO()
        try:
            call_command('sync_students', '--no-color', stdout=out)
            output = out.getvalue()
            
            # Strip unicode symbols and ANSI codes
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', output)
            # Remove unicode check marks and symbols
            output = output.replace('✓', '').replace('✗', '').replace('⚠', '').replace('📚', '')
            
            # Parse for success metrics
            if 'Created:' in output or 'Updated:' in output:
                self.message_user(request, "Students synced successfully!", messages.SUCCESS)
                # Show a snippet of the output
                for line in output.split('\n'):
                    if 'Created:' in line or 'Updated:' in line or 'Errors:' in line:
                        self.message_user(request, line.strip(), messages.INFO)
            else:
                self.message_user(request, "Sync completed.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error syncing students: {str(e)}", messages.ERROR)
        
        return redirect('admin:app_student_changelist')
    
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
    change_list_template = 'admin/app/course/change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-courses/', self.admin_site.admin_view(self.sync_courses_view), name='sync_courses'),
        ]
        return custom_urls + urls
    
    def sync_courses_view(self, request):
        from django.core.management import call_command
        from io import StringIO
        import re
        
        # Capture the command output
        out = StringIO()
        try:
            call_command('sync_courses', '--update-existing', '--no-color', stdout=out)
            output = out.getvalue()
            
            # Strip unicode symbols and ANSI codes
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', output)
            # Remove unicode check marks and symbols
            output = output.replace('✓', '').replace('✗', '').replace('⚠', '').replace('📚', '')
            
            # Parse for success metrics
            if 'Created:' in output or 'Updated:' in output:
                self.message_user(request, "Courses synced successfully!", messages.SUCCESS)
                # Show a snippet of the output
                for line in output.split('\n'):
                    if 'Created:' in line or 'Updated:' in line or 'Errors:' in line:
                        self.message_user(request, line.strip(), messages.INFO)
            else:
                self.message_user(request, "Sync completed.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error syncing courses: {str(e)}", messages.ERROR)
        
        return redirect('admin:app_course_changelist')


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
    list_filter = ['status', 'registration__cohort', 'course']
    search_fields = ['registration__student__full_name', 'registration__student__email', 'course__name']
    readonly_fields = ['created_at', 'updated_at', 'enrolled_date']
    date_hierarchy = 'enrolled_date'
    actions = ['mark_as_completed']
    
    @admin.action(description='Mark selected enrollments as completed')
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            status='COMPLETED',
            completion_date=timezone.now()
        )
        self.message_user(request, f'Successfully marked {updated} enrollment(s) as completed.')



@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title_short', 'course', 'assignment_type', 'work_type', 'max_points', 'due_date']
    list_filter = ['course', 'assignment_type', 'work_type']
    search_fields = ['title', 'google_id']
    date_hierarchy = 'due_date'
    readonly_fields = ['google_id', 'created_at', 'updated_at']
    change_list_template = 'admin/app/assignment/change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-assignments/', self.admin_site.admin_view(self.sync_assignments_view), name='sync_assignments'),
        ]
        return custom_urls + urls
    
    def sync_assignments_view(self, request):
        from django.core.management import call_command
        from io import StringIO
        import re
        
        # Capture the command output
        out = StringIO()
        try:
            call_command('sync_assignments', '--no-color', stdout=out)
            output = out.getvalue()
            
            # Strip unicode symbols and ANSI codes
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', output)
            # Remove unicode check marks and symbols
            output = output.replace('✓', '').replace('✗', '').replace('⚠', '').replace('📚', '').replace('🗑️', '')
            
            # Parse for success metrics
            if 'Created:' in output or 'Updated:' in output:
                self.message_user(request, "Assignments synced successfully!", messages.SUCCESS)
                # Show a snippet of the output
                for line in output.split('\n'):
                    if 'Created:' in line or 'Updated:' in line or 'Errors:' in line:
                        self.message_user(request, line.strip(), messages.INFO)
            else:
                self.message_user(request, "Sync completed.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error syncing assignments: {str(e)}", messages.ERROR)
        
        return redirect('admin:app_assignment_changelist')
    
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
    search_fields = ['enrollment__registration__student__full_name', 'assignment__title']
    readonly_fields = ['google_id', 'created_at', 'updated_at']
    change_list_template = 'admin/app/submission/change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-submissions/', self.admin_site.admin_view(self.sync_submissions_view), name='sync_submissions'),
        ]
        return custom_urls + urls
    
    def sync_submissions_view(self, request):
        from django.core.management import call_command
        from io import StringIO
        import re
        
        # Capture the command output
        out = StringIO()
        try:
            call_command('sync_submissions', '--no-color', stdout=out)
            output = out.getvalue()
            
            # Strip unicode symbols and ANSI codes
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', output)
            # Remove unicode check marks and symbols
            output = output.replace('✓', '').replace('✗', '').replace('⚠', '').replace('📚', '')
            
            # Parse for success metrics
            if 'Created:' in output or 'Updated:' in output:
                self.message_user(request, "Submissions synced successfully!", messages.SUCCESS)
                # Show a snippet of the output
                for line in output.split('\n'):
                    if 'Created:' in line or 'Updated:' in line or 'Errors:' in line:
                        self.message_user(request, line.strip(), messages.INFO)
            else:
                self.message_user(request, "Sync completed.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error syncing submissions: {str(e)}", messages.ERROR)
        
        return redirect('admin:app_submission_changelist')
    
    def student_name(self, obj):
        return obj.enrollment.student.full_name
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'enrollment__registration__student__full_name'
    
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
    list_display = ['student_name', 'course_name', 'cohort_name', 'issued_date', 'completion_percentage', 'has_file']
    list_filter = ['issued_date', 'enrollment__registration__cohort', 'enrollment__course']
    search_fields = ['enrollment__registration__student__full_name', 'enrollment__course__name', 'enrollment__registration__cohort__name']
    date_hierarchy = 'issued_date'
    readonly_fields = ['created_at', 'updated_at']
    # actions = ['issue_certificates']
    # change_list_template = 'admin/certificate_changelist.html'
    
    def student_name(self, obj):
        return obj.enrollment.student.full_name
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'enrollment__registration__student__full_name'
    
    def course_name(self, obj):
        return obj.enrollment.course.name
    course_name.short_description = 'Course'
    course_name.admin_order_field = 'enrollment__course__name'
    
    def cohort_name(self, obj):
        return obj.enrollment.cohort.name
    cohort_name.short_description = 'Cohort'
    cohort_name.admin_order_field = 'enrollment__registration__cohort__name'
    
    def has_file(self, obj):
        return bool(obj.certificate_file or obj.certificate_url)
    has_file.short_description = 'Has File/URL'
    has_file.boolean = True
    
    def save_model(self, request, obj, form, change):
        """Mark enrollment as completed when certificate is saved"""
        from datetime import date
        super().save_model(request, obj, form, change)
        
        # Mark enrollment as completed
        if obj.enrollment.status != 'COMPLETED':
            obj.enrollment.status = 'COMPLETED'
            if not obj.enrollment.completion_date:
                obj.enrollment.completion_date = date.today()
            obj.enrollment.save()
    
    # def get_urls(self):
    #     from django.urls import path
    #     urls = super().get_urls()
    #     custom_urls = [
    #         path('issue-all/', self.admin_site.admin_view(self.issue_all_certificates_view), name='certificate-issue-all'),
    #     ]
    #     return custom_urls + urls
    
    # def issue_all_certificates_view(self, request):
    #     """Custom view to issue certificates for all eligible students"""
    #     from django.contrib import messages
    #     from django.shortcuts import redirect
        
    #     # Call the model's class method
    #     results = Certificate.issue_all_eligible(
    #         user=request.user
    #     )
        
    #     # Display results
    #     issued_count = len(results['issued'])
    #     skipped_count = len(results['skipped'])
    #     error_count = len(results['errors'])
        
    #     if issued_count > 0:
    #         messages.success(request, f'Successfully issued {issued_count} certificate(s)')
        
    #     if skipped_count > 0:
    #         messages.info(request, f'Skipped {skipped_count} enrollment(s) (not eligible or already has certificate)')
        
    #     if error_count > 0:
    #         messages.error(request, f'Failed to issue {error_count} certificate(s)')
    #         for error_info in results['errors'][:5]:  # Show first 5 errors
    #             messages.error(request, f"{error_info['enrollment']}: {error_info['error']}")
        
    #     return redirect('admin:app_certificate_changelist')


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['cohort', 'status', 'started_at', 'completed_at', 'courses_synced', 'students_synced']
    list_filter = ['status', 'cohort', 'started_at']
    readonly_fields = ['started_at', 'completed_at', 'courses_synced', 'students_synced', 'assignments_synced', 'submissions_synced', 'errors']
    date_hierarchy = 'started_at'
