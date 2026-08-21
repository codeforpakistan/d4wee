from django.urls import path

from app.views import (
    attendances,
    certificates,
    cohorts,
    courses,
    profile,
    registrations,
    students,
    views,
)

urlpatterns = [
    path('', views.index, name='home'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', profile.profile, name='profile'),
    path('courses/', views.list_courses, name='courses'),
    path('courses/<int:google_id>', views.detail_courses, name='course'),

    # Cohorts
    path('dashboard/cohorts/', cohorts.cohort_list, name='cohort_list'),
    path('dashboard/cohort/<int:cohort_id>/', cohorts.cohort_detail, name='cohort_detail'),

    # Courses
    path('dashboard/courses/', courses.course_list, name='course_list'),
    path('dashboard/courses/<str:google_id>/', courses.course_detail, name='course_detail'),
    
    path('dashboard/students/', students.students_list, name='student_list'),
    path('dashboard/students/<str:google_id>/', students.student_detail, name='student_detail'),

    path('dashboard/registrations/', registrations.registration_list, name='registration_list'),
    path('dashboard/registrations/<str:status>/', registrations.registration_detail, name='registration_detail'),
    path('dashboard/registrations/create/<int:cohort_id>/', registrations.registration_create, name='registration_create'),
    path('dashboard/registrations/<int:registration_id>/approve/', registrations.approve_registration, name='approve_registration'),
    path('dashboard/registrations/<int:registration_id>/reject/', registrations.reject_registration, name='reject_registration'),

    # Student attendance
    path('dashboard/attendances/', attendances.attendance_weekly, name='attendance_weekly'),
    path('dashboard/attendance/', attendances.attendance_list, name='attendance_list'),
    
    path('dashboard/issues/', views.issues, name='issues'),
    path('dashboard/reports/', views.reports, name='reports'),
    path('dashboard/reports/grades/', views.student_grades, name='grades'),
    
    # Student registration
    
    # Student enrollment
    path('dashboard/enroll/<int:course_id>/', views.enroll_in_course, name='enroll_in_course'),
    # path('unenroll/<int:enrollment_id>/', views.unenroll_from_course, name='unenroll_from_course'),  # Disabled: students cannot unenroll
    
    
    
    # Certificates
    path('dashboard/certificates/', certificates.certificate_list, name='certificate_list'),
    path('dashboard/certificates/<str:student_google_id>/<str:course_google_id>/', views.view_certificate, name='view_certificate'),
    
    # Staff: Issue certificates
    path('dashboard/enrollment/<int:enrollment_id>/issue-certificate/', views.issue_certificate, name='issue_certificate'),
    path('dashboard/certificate/<int:certificate_id>/delete/', views.delete_certificate, name='delete_certificate'),
    

]
