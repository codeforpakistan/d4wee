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
    path('issues/attendance-emails/', views.attendance_mismatches, name='issues_attendance_emails'),
    
    # Student self-registration
    path('register/', views.available_cohorts, name='available_cohorts'),
    path('register/<int:cohort_id>/', views.register_for_cohort, name='register_for_cohort'),
    
    # Student cohorts and enrollment
    path('my-cohorts/', views.my_cohorts, name='my_cohorts'),
    path('enroll/<int:course_id>/', views.enroll_in_course, name='enroll_in_course'),
    
    # Student attendance
    path('attend/', views.mark_attendance, name='mark_attendance'),
]
