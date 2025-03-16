from django.urls import path
from . import views

urlpatterns = [
    path('problems/', views.ProblemListView.as_view(), name='problem-list'),
    path('problems/<int:problem_id>/', views.ProblemDetailView.as_view(), name='problem-detail'),
    path('problems/create/', views.ProblemCreateView.as_view(), name='problem-create'),
    path('problems/<int:problem_id>/update/', views.ProblemUpdateView.as_view(), name='problem-update'),
    path('problems/<int:problem_id>/delete/', views.ProblemDeleteView.as_view(), name='problem-delete'),
    
    path('competitions/<int:pk>/problems/', views.competition_problems, name='competition-problems'),
    path('competitions/<int:competition_id>/problems/create/', views.ProblemCreateView.as_view(), name='competition-problem-create'),
    path('competitions/<int:competition_id>/problems/upload/', views.bulk_problem_upload, name='bulk-problem-upload'),
    path('competitions/<int:competition_id>/problems/batch/', views.problem_batch_operations, name='problem-batch-operations'),
    
    path('api/competitions/<int:competition_id>/problems/export/', views.export_problems_api, name='export-problems-api'),
    path('api/competitions/<int:competition_id>/problems/import/', views.import_problems_api, name='import-problems-api'),
]
