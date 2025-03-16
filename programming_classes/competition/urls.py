from django.urls import path
from . import views

urlpatterns = [
    path('competitions/', views.CompetitionListView.as_view(), name='competition-list'),
    path('competitions/create/', views.CompetitionCreateView.as_view(), name='competition-create'),
    path('competitions/<int:pk>/', views.CompetitionDetailView.as_view(), name='competition-detail'),
    path('competitions/<int:pk>/update/', views.CompetitionUpdateView.as_view(), name='competition-update'),
    path('competitions/<int:pk>/delete/', views.CompetitionDeleteView.as_view(), name='competition-delete'),
    path('competitions/<int:pk>/manage/', views.competition_management, name='competition-management'),
    path('competitions/<int:pk>/statistics/', views.competition_statistics, name='competition-statistics'),
    
    path('import/codeforces/', views.codeforces_import, name='codeforces-import'),
    path('import/yandex/', views.yandex_contest_import, name='yandex-import'),
]
