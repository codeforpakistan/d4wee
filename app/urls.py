from django.urls import path
from app.views import views, courses, cohorts, students, registrations, profile, attendances

urlpatterns = [
    path('', views.index, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', profile.profile, name='profile'),
    
    path('cohorts/', cohorts.cohort_list, name='cohort_list'),
    path('cohort/<int:cohort_id>/', cohorts.cohort_detail, name='cohort_detail'),
    
    path('courses/', courses.course_list, name='course_list'),
    path('course/<int:course_id>/', courses.course_detail, name='course_detail'),
    
    path('students/', students.students_list, name='student_list'),
    path('student/<str:google_id>/', students.student_detail, name='student_detail'),

    path('registrations/', registrations.registration_list, name='registration_list'),
    path('registrations/<str:status>/', registrations.registration_detail, name='registration_detail'),
    path('registrations/create/<int:cohort_id>/', registrations.registration_create, name='registration_create'),
    path('registrations/<int:registration_id>/approve/', registrations.approve_registration, name='approve_registration'),
    path('registrations/<int:registration_id>/reject/', registrations.reject_registration, name='reject_registration'),

    # Student attendance
    path('attendances/', attendances.attendance_weekly, name='attendance_weekly'),
    
    path('attendance/', attendances.attendance_list, name='attendance_list'),
   
    
    path('issues/', views.issues, name='issues'),
    path('reports/', views.reports, name='reports'),
    
    # Student registration
    
    # Student enrollment
    path('enroll/<int:course_id>/', views.enroll_in_course, name='enroll_in_course'),
    # path('unenroll/<int:enrollment_id>/', views.unenroll_from_course, name='unenroll_from_course'),  # Disabled: students cannot unenroll
    
    
    
    # Certificates
    path('certificates/<str:student_google_id>/<str:course_google_id>/', views.view_certificate, name='view_certificate'),
    path('test-certificate/', views.test_certificate, name='test_certificate'),
    
    # Staff: Issue certificates
    path('enrollment/<int:enrollment_id>/issue-certificate/', views.issue_certificate, name='issue_certificate'),
    path('certificate/<int:certificate_id>/delete/', views.delete_certificate, name='delete_certificate'),
    

]
