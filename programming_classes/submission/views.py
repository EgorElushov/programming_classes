from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q, Count
from django.utils import timezone

from .models import Submission
from problem.models import Problem
from competition.models import Competition
from .forms import SubmissionForm


class SubmissionListView(LoginRequiredMixin, ListView):
    model = Submission
    template_name = 'submissions/submission_list.html'
    context_object_name = 'submissions'
    paginate_by = 20

    def get_queryset(self):
        queryset = Submission.objects.all()

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        else:
            user_id = self.request.GET.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)

        problem_id = self.request.GET.get('problem_id')
        if problem_id:
            queryset = queryset.filter(problem_id=problem_id)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(submitted_at__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(submitted_at__lte=date_to)

        sort_by = self.request.GET.get('sort_by', 'submitted_at')
        sort_direction = self.request.GET.get('sort_direction', 'desc')

        if sort_direction == 'asc':
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by(f'-{sort_by}')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['problems'] = Problem.objects.all()
        context['status_choices'] = Submission.STATUS_CHOICES

        context['total_submissions'] = Submission.objects.filter(user=self.request.user).count()
        context['accepted_submissions'] = Submission.objects.filter(user=self.request.user, status='accepted').count()

        context['active_filters'] = {
            'problem_id': self.request.GET.get('problem_id', ''),
            'status': self.request.GET.get('status', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'sort_by': self.request.GET.get('sort_by', 'submitted_at'),
            'sort_direction': self.request.GET.get('sort_direction', 'desc'),
        }

        return context


class SubmissionDetailView(LoginRequiredMixin, DetailView):
    model = Submission
    template_name = 'submissions/submission_detail.html'
    context_object_name = 'submission'
    pk_url_kwarg = 'submission_id'

    def get_object(self):
        submission = super().get_object()

        if not (self.request.user == submission.user or self.request.user.is_staff):
            problem = submission.problem
            competition = problem.competition
            if self.request.user != competition.user:
                raise HttpResponseForbidden("У вас нет разрешения на просмотр этого решения")

        return submission

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = self.get_object()

        context['problem'] = submission.problem
        context['submission'] = submission

        context['is_owner'] = self.request.user == submission.user

        context['can_manage'] = self.request.user.is_staff or self.request.user == submission.problem.competition.user

        return context


@login_required
def create_submission(request, problem_id):
    problem = get_object_or_404(Problem, problem_id=problem_id)

    competition = problem.competition
    today = timezone.now().date()
    is_active = competition.start_date <= today <= competition.end_date

    if not is_active and not request.user.is_staff:
        messages.error(request, "Контест закрыт. Посылки не принимаются.")
        return redirect('problem-detail', problem_id=problem_id)

    if request.method == 'POST':
        form = SubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            submission.problem = problem
            submission.status = 'pending'
            submission.save()

            messages.success(request, "Ваша посылка была получена и в настоящее время обрабатывается.")

            return redirect('submission-detail', submission_id=submission.submission_id)
    else:
        form = SubmissionForm()

    return render(
        request,
        'submissions/submission_form.html',
        {
            'form': form,
            'problem': problem,
            'competition': competition,
        },
    )


@login_required
def update_submission_status(request, submission_id):
    """View function for updating a submission's status (admin/staff only)"""
    submission = get_object_or_404(Submission, submission_id=submission_id)

    # Check if user has permission to update this submission
    if not (request.user.is_staff or request.user == submission.problem.competition.user):
        return HttpResponseForbidden("У вас нет прав на обновление этого статуса отправки")

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Submission.STATUS_CHOICES):
            submission.status = new_status
            submission.save()

            messages.success(request, f"Статус обновлен для {new_status}")
        else:
            messages.error(request, "Некорректное значение")

    return redirect('submission-detail', submission_id=submission_id)


@login_required
def user_submissions(request, user_id=None):
    if user_id is None:
        user_id = request.user.id

    if int(user_id) != request.user.id and not request.user.is_staff:
        return HttpResponseForbidden("У вас нет прав на просмотр посылок этого пользователя")

    from accounts.models import Account

    user = get_object_or_404(Account, id=user_id)

    submissions = Submission.objects.filter(user=user).order_by('-submitted_at')

    stats = {
        'total': submissions.count(),
        'accepted': submissions.filter(status='accepted').count(),
        'rejected': submissions.filter(status='rejected').count(),
        'pending': submissions.filter(status='pending').count(),
    }

    if stats['total'] > 0:
        stats['acceptance_rate'] = (stats['accepted'] / stats['total']) * 100
    else:
        stats['acceptance_rate'] = 0

    solved_problems = Problem.objects.filter(submissions__user=user, submissions__status='accepted').distinct()

    return render(
        request,
        'submissions/user_submissions.html',
        {
            'user': user,
            'submissions': submissions,
            'stats': stats,
            'solved_problems': solved_problems,
            'is_own_profile': (int(user_id) == request.user.id),
        },
    )


@login_required
def problem_submissions(request, problem_id):
    problem = get_object_or_404(Problem, problem_id=problem_id)

    is_admin = request.user.is_staff or request.user == problem.competition.user

    if is_admin:
        submissions = Submission.objects.filter(problem=problem).order_by('-submitted_at')
    else:
        submissions = Submission.objects.filter(problem=problem, user=request.user).order_by('-submitted_at')

    stats = {
        'total': Submission.objects.filter(problem=problem).count(),
        'accepted': Submission.objects.filter(problem=problem, status='accepted').count(),
    }

    if stats['total'] > 0:
        stats['acceptance_rate'] = (stats['accepted'] / stats['total']) * 100
    else:
        stats['acceptance_rate'] = 0

    return render(
        request,
        'submissions/problem_submissions.html',
        {
            'problem': problem,
            'submissions': submissions,
            'stats': stats,
            'is_admin': is_admin,
            'competition': problem.competition,
        },
    )


@login_required
def competition_submissions(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)

    is_admin = request.user.is_staff or request.user == competition.user

    if is_admin:
        problems = Problem.objects.filter(competition=competition)

        submissions = Submission.objects.filter(problem__in=problems).order_by('-submitted_at')

        problem_stats = []
        for problem in problems:
            problem_submissions = Submission.objects.filter(problem=problem)
            total = problem_submissions.count()
            accepted = problem_submissions.filter(status='accepted').count()

            if total > 0:
                acceptance_rate = (accepted / total) * 100
            else:
                acceptance_rate = 0

            problem_stats.append(
                {
                    'problem': problem,
                    'total': total,
                    'accepted': accepted,
                    'acceptance_rate': acceptance_rate,
                }
            )

        user_stats = (
            Submission.objects.filter(problem__in=problems)
            .values('user__id', 'user__username')
            .annotate(
                total_submissions=Count('submission_id'),
                accepted_submissions=Count('submission_id', filter=Q(status='accepted')),
            )
            .order_by('-accepted_submissions')
        )

        context = {
            'competition': competition,
            'submissions': submissions,
            'problems': problems,
            'problem_stats': problem_stats,
            'user_stats': user_stats,
            'is_admin': is_admin,
            'today': timezone.now().date(),
        }
    else:
        problems = Problem.objects.filter(competition=competition)
        submissions = Submission.objects.filter(problem__in=problems, user=request.user).order_by('-submitted_at')

        context = {
            'competition': competition,
            'submissions': submissions,
            'is_admin': is_admin,
            'problems': problems,
            'today': timezone.now().date(),
        }

    return render(request, 'submissions/competition_submissions.html', context)


@login_required
def submission_statistics(request):
    if not request.user.is_staff:
        return redirect('user-submissions')

    total_submissions = Submission.objects.count()

    status_stats = Submission.objects.values('status').annotate(count=Count('submission_id')).order_by('status')

    from django.db.models.functions import TruncDate

    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    daily_submissions = (
        Submission.objects.filter(submitted_at__gte=thirty_days_ago)
        .annotate(day=TruncDate('submitted_at'))
        .values('day')
        .annotate(count=Count('submission_id'))
        .order_by('day')
    )

    top_problems = Problem.objects.annotate(submission_count=Count('submissions')).order_by('-submission_count')[:10]

    most_active_users = (
        Submission.objects.values('user__id', 'user__username')
        .annotate(submission_count=Count('submission_id'))
        .order_by('-submission_count')[:10]
    )

    return render(
        request,
        'submissions/submission_statistics.html',
        {
            'total_submissions': total_submissions,
            'status_stats': status_stats,
            'daily_submissions': daily_submissions,
            'top_problems': top_problems,
            'most_active_users': most_active_users,
        },
    )


@login_required
def submit_solution_api(request, problem_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        problem = Problem.objects.get(problem_id=problem_id)

        # Check if competition is active
        competition = problem.competition
        today = timezone.now().date()
        is_active = competition.start_date <= today <= competition.end_date

        if not is_active and not request.user.is_staff:
            return JsonResponse({'error': 'Этот контест неактивен'}, status=403)

        # Get code from request
        import json

        data = json.loads(request.body)
        code = data.get('code')

        if not code:
            return JsonResponse({'error': 'Code is required'}, status=400)

        # Create submission
        submission = Submission.objects.create(user=request.user, problem=problem, code=code, status='pending')

        # Return the submission ID so the client can check status
        return JsonResponse(
            {
                'success': True,
                'submission_id': submission.submission_id,
                'message': 'Решение получено',
            }
        )

    except Problem.DoesNotExist:
        return JsonResponse({'error': 'Задача не найдена'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Некорректный JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def check_submission_status_api(request, submission_id):
    try:
        submission = Submission.objects.get(submission_id=submission_id)

        # Check if user has access to this submission
        if not (
            request.user == submission.user
            or request.user.is_staff
            or request.user == submission.problem.competition.user
        ):
            return JsonResponse({'error': 'У вас нет прав для просмотра этой посылки'}, status=403)

        return JsonResponse(
            {
                'submission_id': submission.submission_id,
                'problem_id': submission.problem.problem_id,
                'problem_title': submission.problem.title,
                'status': submission.status,
                'submitted_at': submission.submitted_at.isoformat(),
            }
        )

    except Submission.DoesNotExist:
        return JsonResponse({'error': 'Посылка не найдена'}, status=404)


@login_required
def update_submission_status_api(request, submission_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        submission = Submission.objects.get(submission_id=submission_id)

        if not (request.user.is_staff or request.user == submission.problem.competition.user):
            return JsonResponse({'error': 'У вас нет прав для изменения статуса посылки'}, status=403)

        import json

        data = json.loads(request.body)
        new_status = data.get('status')

        if not new_status or new_status not in dict(Submission.STATUS_CHOICES):
            return JsonResponse({'error': 'Некорректный статус'}, status=400)

        # Update status
        submission.status = new_status
        submission.save()

        return JsonResponse(
            {
                'success': True,
                'submission_id': submission.submission_id,
                'new_status': new_status,
                'message': 'Статус посылки обновлен',
            }
        )

    except Submission.DoesNotExist:
        return JsonResponse({'error': 'Посылка не найдена'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Некорректный JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def bulk_grading(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to access this page")

    if request.method == 'POST':
        # Get list of submission IDs and new status
        submission_ids = request.POST.getlist('submission_ids')
        new_status = request.POST.get('status')

        if not submission_ids:
            messages.error(request, "No submissions selected")
            return redirect('submission-list')

        if not new_status or new_status not in dict(Submission.STATUS_CHOICES):
            messages.error(request, "Invalid status value")
            return redirect('submission-list')

        # Update all selected submissions
        count = Submission.objects.filter(submission_id__in=submission_ids).update(status=new_status)

        messages.success(request, f"{count} submissions updated to status: {new_status}")
        return redirect('submission-list')

    # Get pending submissions
    pending_submissions = Submission.objects.filter(status='pending').order_by('-submitted_at')

    return render(
        request,
        'submissions/bulk_grading.html',
        {
            'submissions': pending_submissions,
            'status_choices': Submission.STATUS_CHOICES,
        },
    )


@login_required
def automated_grader_webhook(request):
    """Webhook endpoint for automated grading systems"""
    if not request.method == 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    # Check for API key authentication
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != settings.GRADER_API_KEY:
        return JsonResponse({'error': 'Invalid or missing API key'}, status=403)

    try:
        import json

        data = json.loads(request.body)

        submission_id = data.get('submission_id')
        new_status = data.get('status')

        if not submission_id or not new_status:
            return JsonResponse({'error': 'submission_id and status are required fields'}, status=400)

        if new_status not in dict(Submission.STATUS_CHOICES):
            return JsonResponse({'error': 'Invalid status value'}, status=400)

        # Update the submission
        try:
            submission = Submission.objects.get(submission_id=submission_id)
            submission.status = new_status
            submission.save()

            return JsonResponse(
                {'success': True, 'message': f'Submission {submission_id} updated to status: {new_status}'}
            )

        except Submission.DoesNotExist:
            return JsonResponse({'error': 'Submission not found'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def submission_leaderboard(request, competition_id):
    """View the leaderboard of users based on submission status"""
    competition = get_object_or_404(Competition, id=competition_id)

    # Get problems for this competition
    problems = Problem.objects.filter(competition=competition)

    # Get all users who submitted solutions to these problems
    from django.db.models import F, Window, Max
    from django.db.models.functions import Rank

    # Aggregate data - count accepted submissions per user
    leaderboard = (
        Submission.objects.filter(problem__in=problems, status='accepted')
        .values('user__id', 'user__username')
        .annotate(
            solved_count=Count('problem', distinct=True),
            total_submissions=Count('submission_id'),
            efficiency=F('solved_count') * 100.0 / F('total_submissions'),
            last_accepted=Max('submitted_at'),
        )
        .order_by('-solved_count', 'last_accepted')
    )

    # Add rank
    rank = 1
    last_solved = None
    leaderboard_with_rank = []

    for entry in leaderboard:
        if last_solved is not None and entry['solved_count'] < last_solved:
            rank += 1

        entry['rank'] = rank
        last_solved = entry['solved_count']
        leaderboard_with_rank.append(entry)

    return render(
        request,
        'submissions/leaderboard.html',
        {
            'competition': competition,
            'leaderboard': leaderboard_with_rank,
            'problem_count': problems.count(),
        },
    )
