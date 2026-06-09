from django.db import models


class Attendance(models.Model):
    """Weekly attendance tracking - one record per student per week"""
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='attendance')
    cohort = models.ForeignKey('Cohort', on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField(help_text="Date of attendance submission")
    hours_spent = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="How many hours did you spend learning this week?",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def week_number(self):
        """Calculate ISO week number from date"""
        return self.date.isocalendar()[1]
    
    def __str__(self):
        return f"{self.student.full_name} - {self.cohort.name} - Week {self.week_number}"
    
    class Meta:
        ordering = ['-date', 'student__full_name']
        unique_together = ['student', 'cohort', 'date']
        indexes = [
            models.Index(fields=['student', 'cohort', 'date']),
        ]
        verbose_name_plural = 'Attendance'


class Certificate(models.Model):
    """Issued certificates"""
    CERTIFICATE_TYPE_CHOICES = [
        ('COURSE', 'Course Completion'),
        ('COHORT', 'Cohort Completion'),
    ]
    
    registration = models.ForeignKey('Registration', on_delete=models.CASCADE, related_name='certificates')
    certificate_type = models.CharField(max_length=20, choices=CERTIFICATE_TYPE_CHOICES, default='COHORT')
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='certificates',
                               help_text="Specific course (for course certificates)")
    issued_date = models.DateField()
    completion_percentage = models.FloatField(help_text="Overall completion percentage")
    average_grade = models.FloatField(null=True, blank=True, help_text="Average grade")
    certificate_url = models.URLField(blank=True, help_text="URL to certificate file")
    certificate_file = models.FileField(upload_to='', null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        course_name = f" - {self.course.name}" if self.course else ""
        return f"{self.registration.student.full_name} - {self.registration.cohort.name}{course_name}"
    
    @classmethod
    def issue_all_eligible(cls, cohort=None, certificate_type='COURSE', user=None):
        """
        Issue certificates for all eligible students (model-heavy approach)
        
        Args:
            cohort: Optional Cohort instance to filter by
            certificate_type: 'COURSE' or 'COHORT'
            user: User issuing the certificates (for notes)
        
        Returns:
            dict with 'issued', 'skipped', 'errors' counts and lists
        """
        from datetime import date
        from .relationship import Enrollment
        
        results = {
            'issued': [],
            'skipped': [],
            'errors': [],
        }
        
        # Get all enrollments to check
        enrollments_query = Enrollment.objects.select_related(
            'student', 'course', 'cohort', 'registration'
        ).prefetch_related(
            'course__assignments',
            'submissions',
            'registration__certificates'
        )
        
        if cohort:
            enrollments_query = enrollments_query.filter(cohort=cohort)
        
        # Check each enrollment for eligibility
        for enrollment in enrollments_query:
            try:
                # Check if eligible
                if not enrollment.certificate_eligible:
                    results['skipped'].append({
                        'enrollment': enrollment,
                        'reason': enrollment.certificate_eligibility_notes
                    })
                    continue
                
                # Check if certificate already exists
                existing_cert = cls.objects.filter(
                    registration=enrollment.registration,
                    certificate_type=certificate_type,
                    course=enrollment.course
                ).first()
                
                if existing_cert:
                    results['skipped'].append({
                        'enrollment': enrollment,
                        'reason': 'Certificate already exists'
                    })
                    continue
                
                # Create certificate
                cert = cls.objects.create(
                    registration=enrollment.registration,
                    certificate_type=certificate_type,
                    course=enrollment.course,
                    issued_date=date.today(),
                    completion_percentage=enrollment.completion_rate or 0,
                    average_grade=enrollment.overall_average_score,
                    notes=f"Bulk issued by {user.username if user else 'system'}"
                )
                
                # Generate and save certificate file
                try:
                    from app.services import generate_certificate
                    certificate_file = generate_certificate(cert)
                    cert.certificate_file.save(certificate_file.name, certificate_file, save=True)
                except Exception as e:
                    # Certificate created but file generation failed
                    cert.notes += f" | File generation error: {str(e)}"
                    cert.save()
                
                results['issued'].append(cert)
                
            except Exception as e:
                results['errors'].append({
                    'enrollment': enrollment,
                    'error': str(e)
                })
        
        return results
    
    class Meta:
        ordering = ['-issued_date']
        unique_together = ['registration', 'certificate_type', 'course']


class SyncLog(models.Model):
    """Track data synchronization from Google Classroom"""
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default='IN_PROGRESS')
    cohort = models.ForeignKey('Cohort', on_delete=models.SET_NULL, null=True, blank=True,
                               help_text="Cohort being synced")
    courses_synced = models.IntegerField(default=0)
    students_synced = models.IntegerField(default=0)
    assignments_synced = models.IntegerField(default=0)
    submissions_synced = models.IntegerField(default=0)
    errors = models.TextField(blank=True)
    
    def __str__(self):
        cohort_name = f" ({self.cohort.name})" if self.cohort else ""
        return f"Sync {self.id} - {self.status} - {self.started_at.strftime('%Y-%m-%d %H:%M')}{cohort_name}"
    
    class Meta:
        ordering = ['-started_at']
