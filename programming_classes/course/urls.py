from django.urls import path
from . import views

urlpatterns = [
    path('courses/', views.CourseListView.as_view(), name='course-list'),
    path('courses/create/', views.CourseCreateView.as_view(), name='course-create'),
    path('courses/<int:course_id>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('courses/<int:course_id>/update/', views.CourseUpdateView.as_view(), name='course-update'),
    path('courses/<int:course_id>/delete/', views.CourseDeleteView.as_view(), name='course-delete'),

    path('courses/<int:course_id>/enroll/', views.enroll_course, name='enroll-course'),
    path('courses/<int:course_id>/unenroll/', views.unenroll_course, name='unenroll-course'),
    path('courses/<int:course_id>/enrollments/', views.course_enrollments, name='course-enrollments'),
    path('enrollments/<int:enrollment_id>/<str:action>/', views.manage_enrollment, name='manage-enrollment'),
    path('courses/<int:course_id>/add-students/', views.add_students_to_course, name='add-students'),
    
    path('my-courses/', views.my_courses, name='my-courses'),
    
    path('courses/<int:course_id>/statistics/', views.course_statistics, name='course-statistics'),
    
    path('courses/<int:course_id>/materials/', views.course_materials, name='course-materials'),
    
    path('api/courses/', views.course_list_api, name='api-course-list'),
    path('api/courses/<int:course_id>/', views.course_detail_api, name='api-course-detail'),
    path('api/courses/create/', views.create_course_api, name='api-create-course'),
    path('api/courses/<int:course_id>/enroll/', views.enroll_course_api, name='api-enroll-course'),
    path('api/courses/<int:course_id>/unenroll/', views.unenroll_course_api, name='api-unenroll-course'),
]