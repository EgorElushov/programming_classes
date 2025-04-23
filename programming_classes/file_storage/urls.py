from django.urls import path
from . import views

urlpatterns = [
    path('materials/', views.CourseMaterialListView.as_view(), name='material-list'),
    path('materials/<int:pk>/', views.CourseMaterialDetailView.as_view(), name='material-detail'),
    path('materials/<int:pk>/download/', views.download_material, name='download-material'),
    path('materials/<int:pk>/preview/', views.material_preview, name='material-preview'),
    path('materials/<int:pk>/update/', views.CourseMaterialUpdateView.as_view(), name='material-update'),
    path('materials/<int:pk>/delete/', views.CourseMaterialDeleteView.as_view(), name='material-delete'),
    path('materials/<int:pk>/serve/', views.serve_material, name='serve-material'),
    path('courses/<int:course_id>/materials/', views.CourseMaterialListView.as_view(), name='course-material-list'),
    path('courses/<int:course_id>/materials/upload/', views.CourseMaterialCreateView.as_view(), name='upload-material'),
    path('courses/<int:course_id>/materials/bulk-upload/', views.bulk_upload_materials, name='bulk-upload-materials'),
    path('courses/<int:course_id>/materials/statistics/', views.material_statistics, name='material-statistics'),
    path('api/courses/<int:course_id>/materials/', views.course_materials_api, name='api-course-materials'),
    path('api/courses/<int:course_id>/materials/upload/', views.upload_material_api, name='api-upload-material'),
    path('api/materials/<int:pk>/delete/', views.delete_material_api, name='api-delete-material'),
]
