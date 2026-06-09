from django.urls import path
from app import views

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('profile/', views.profile, name='profile'),
    path('courses/', views.courses, name='courses'),
    path('students/', views.students_list, name='students_list'),
    path('cohorts/', views.cohorts, name='cohorts'),
    path('cohort/<int:cohort_id>/', views.cohort_detail, name='cohort_detail'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('student/<str:google_id>/', views.student_detail, name='student_detail'),
    path('attendance/', views.attendance, name='attendance'),
    path('issues/', views.issues, name='issues'),
    path('reports/', views.reports, name='reports'),
    
    # Student registration
    path('register/<int:cohort_id>/', views.register_for_cohort, name='register_for_cohort'),
    
    # Student enrollment
    path('enroll/<int:course_id>/', views.enroll_in_course, name='enroll_in_course'),
    # path('unenroll/<int:enrollment_id>/', views.unenroll_from_course, name='unenroll_from_course'),  # Disabled: students cannot unenroll
    
    # Student attendance
    path('attend/', views.mark_attendance, name='mark_attendance'),
    
    # Certificates
    path('certificates/<str:student_google_id>/<str:course_google_id>/', views.view_certificate, name='view_certificate'),
    path('test-certificate/', views.test_certificate, name='test_certificate'),
    
    # Staff: Issue certificates
    path('enrollment/<int:enrollment_id>/issue-certificate/', views.issue_certificate, name='issue_certificate'),
    path('certificate/<int:certificate_id>/delete/', views.delete_certificate, name='delete_certificate'),
    
    # Staff: Manage registrations
    path('registrations/', views.registrations_list, name='registrations_list'),
    path('registrations/<int:registration_id>/approve/', views.approve_registration, name='approve_registration'),
    path('registrations/<int:registration_id>/reject/', views.reject_registration, name='reject_registration'),
]
