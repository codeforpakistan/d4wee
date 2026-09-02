from django.urls import path

from app.views import (
    attendances,
    certificates,
    cohorts,
    console,
    dashboard,
    profile,
    registrations,
    reports,
    students,
    views,
)

urlpatterns = [
    path('', views.index, name='home'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),

    path('dashboard/', dashboard.index, name='dashboard'),
    path('console/', console.index, name='console'),
    path('profile/', profile.profile, name='profile'),
    path('courses/', views.list_courses, name='courses'),
    path('courses/<int:google_id>', views.detail_courses, name='course'),

    # Cohorts
    path('cohorts/', cohorts.cohort_list, name='cohort_list'),
    path('cohort/<int:cohort_id>/', cohorts.cohort_detail, name='cohort_detail'),

    # Courses
    # path('courses/', courses.course_list, name='course_list'),
    # path('courses/<str:google_id>/', courses.course_detail, name='course_detail'),
    
    path('students/', students.students_list, name='student_list'),
    path('students/<str:google_id>/', students.student_detail, name='student_detail'),

    path('registrations/', registrations.registration_list, name='registration_list'),
    path('registrations/<str:status>/', registrations.registration_detail, name='registration_detail'),
    path('registrations/create/<int:cohort_id>/', registrations.registration_create, name='registration_create'),
    path('registrations/<int:registration_id>/approve/', registrations.approve_registration, name='approve_registration'),
    path('registrations/<int:registration_id>/reject/', registrations.reject_registration, name='reject_registration'),

    # Student attendance
    path('attendances/', attendances.attendance_weekly, name='attendance_weekly'),
    path('attendance/', attendances.attendance_list, name='attendance_list'),
    
    path('issues/', views.issues, name='issues'),
    # path('reports/', reports.index, name='reports'),
    path('reports/grades/', reports.student_grades, name='grades'),
    path('reports/download/', reports.download_grades, name='download'),
    
    # Student registration
    
    # Student enrollment
    path('enroll/<int:course_id>/', views.enroll_in_course, name='enroll_in_course'),
    # path('unenroll/<int:enrollment_id>/', views.unenroll_from_course, name='unenroll_from_course'),  # Disabled: students cannot unenroll
    
    
    
    # Certificates
    path('certificates/', certificates.certificate_list, name='certificate_list'),
    path('certificates/<str:student_google_id>/<str:course_google_id>/', views.view_certificate, name='view_certificate'),
    
    # Staff: Issue certificates
    path('enrollment/<int:enrollment_id>/issue-certificate/', views.issue_certificate, name='issue_certificate'),
    path('certificate/<int:certificate_id>/delete/', views.delete_certificate, name='delete_certificate'),
    

]
