from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('students/', views.students_list, name='students_list'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('student/<str:google_id>/', views.student_detail, name='student_detail'),
    # Admin/setup only - not linked in UI
    path('setup/', views.index, name='index'),
    path('sync/', views.sync_classroom_data, name='sync_classroom_data'),
    path('debug-auth/', views.debug_auth, name='debug_auth'),
]
