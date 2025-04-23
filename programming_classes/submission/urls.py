from django.urls import path
from . import views

urlpatterns = [
    path('submissions/', views.SubmissionListView.as_view(), name='submission-list'),
    path('submissions/<int:submission_id>/', views.SubmissionDetailView.as_view(), name='submission-detail'),
    path('problems/<int:problem_id>/submit/', views.create_submission, name='create-submission'),
    path(
        'submissions/<int:submission_id>/update-status/',
        views.update_submission_status,
        name='update-submission-status',
    ),
    path('my-submissions/', views.user_submissions, name='user-submissions'),
    path('users/<int:user_id>/submissions/', views.user_submissions, name='user-submissions-specific'),
    path('problems/<int:problem_id>/submissions/', views.problem_submissions, name='problem-submissions'),
    path(
        'competitions/<int:competition_id>/submissions/', views.competition_submissions, name='competition-submissions'
    ),
    path('competitions/<int:competition_id>/leaderboard/', views.submission_leaderboard, name='submission-leaderboard'),
    path('submissions/statistics/', views.submission_statistics, name='submission-statistics'),
    path('submissions/bulk-grading/', views.bulk_grading, name='bulk-grading'),
    path('api/problems/<int:problem_id>/submit/', views.submit_solution_api, name='api-submit-solution'),
    path(
        'api/submissions/<int:submission_id>/status/',
        views.check_submission_status_api,
        name='api-check-submission-status',
    ),
    path(
        'api/submissions/<int:submission_id>/update-status/',
        views.update_submission_status_api,
        name='api-update-submission-status',
    ),
    path('api/webhook/grader/', views.automated_grader_webhook, name='api-grader-webhook'),
]
