from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q

from .models import Problem
from competition.models import Competition
from .forms import ProblemForm, TestCaseForm
from problem.models import TestCase
from checker.consts import PROGRAMMING_LANGUAGES


class ProblemListView(ListView):
    model = Problem
    template_name = 'problems/problem_list.html'
    context_object_name = 'problems'
    paginate_by = 20

    def get_queryset(self):
        queryset = Problem.objects.all()

        competition_id = self.request.GET.get('competition')
        if competition_id:
            queryset = queryset.filter(competition_id=competition_id)

        difficulty = self.request.GET.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))

        sort_by = self.request.GET.get('sort_by', 'title')
        sort_direction = self.request.GET.get('sort_direction', 'asc')

        if sort_direction == 'desc':
            sort_by = f'-{sort_by}'

        return queryset.order_by(sort_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['competitions'] = Competition.objects.all()
        context['difficulties'] = Problem.objects.values_list('difficulty', flat=True).distinct()

        context['active_filters'] = {
            'competition': self.request.GET.get('competition', ''),
            'difficulty': self.request.GET.get('difficulty', ''),
            'search': self.request.GET.get('search', ''),
            'sort_by': self.request.GET.get('sort_by', 'title'),
            'sort_direction': self.request.GET.get('sort_direction', 'asc'),
        }

        return context


class ProblemDetailView(DetailView):
    model = Problem
    template_name = 'problems/problem_detail.html'
    context_object_name = 'problem'
    pk_url_kwarg = 'problem_id'

    def post(self, request, *args, **kwargs):
        problem = self.get_object()

        if request.user.is_authenticated:
            if request.POST.get('action') == 'solve':
                problem.solve(request.user)
                messages.success(request, 'Рeшение задачи успешно добавлено')
            elif request.POST.get('action') == 'unsolve':
                problem.unsolve(request.user)
                messages.success(request, 'Решение задачи успешно удалено')

        return redirect(reverse('problem_detail', kwargs={'problem_id': problem.pk}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        problem = self.get_object()

        context['competition'] = problem.competition
        context['programming_languages'] = PROGRAMMING_LANGUAGES

        if self.request.user.is_authenticated:
            context['can_edit'] = self.request.user == problem.competition.user or self.request.user.is_staff

        return context


class ProblemCreateView(LoginRequiredMixin, CreateView):
    model = Problem
    form_class = ProblemForm
    template_name = 'problems/problem_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.competition_id = self.kwargs.get('competition_id') or request.GET.get('competition_id')

        if self.competition_id:
            self.competition = get_object_or_404(Competition, pk=self.competition_id)

            if not (request.user == self.competition.user or request.user.is_staff):
                return HttpResponseForbidden("У вас нет разрешения добавлять задачи в этот контест")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if hasattr(self, 'competition'):
            kwargs['competition'] = self.competition
        return kwargs

    def form_valid(self, form):
        if hasattr(self, 'competition'):
            form.instance.competition = self.competition

        messages.success(self.request, "Задача успешно создана!")
        return super().form_valid(form)

    def get_success_url(self):
        if hasattr(self, 'competition_id') and self.competition_id:
            return reverse('problem-detail', kwargs={'problem_id': self.competition_id})
        return reverse('problem-detail', kwargs={'problem_id': self.object.problem_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, 'competition'):
            context['competition'] = self.competition
        return context


class ProblemUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Problem
    form_class = ProblemForm
    template_name = 'problems/problem_form.html'
    pk_url_kwarg = 'problem_id'

    def test_func(self):
        problem = self.get_object()
        return self.request.user == problem.competition.user or self.request.user.is_staff

    def form_valid(self, form):
        messages.success(self.request, "Задача успешно обновлена!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('problem-detail', kwargs={'problem_id': self.object.problem_id})


class ProblemDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Problem
    template_name = 'problems/problem_confirm_delete.html'
    pk_url_kwarg = 'problem_id'

    def test_func(self):
        problem = self.get_object()
        return self.request.user == problem.competition.user or self.request.user.is_staff

    def get_success_url(self):
        messages.success(self.request, "Задча успешно удалена!")
        return reverse('competition-problems', kwargs={'pk': self.object.competition.id})


@login_required
def competition_problems(request, pk):
    competition = get_object_or_404(Competition, pk=pk)
    problems = Problem.objects.filter(competition=competition).order_by('title')

    can_manage = request.user == competition.user or request.user.is_staff

    '''
    ДОПИСАТЬ
    '''
    return render(
        request,
        'problems/competition_problems.html',
        {'competition': competition, 'problems': problems, 'can_manage': can_manage},
    )


@login_required
def bulk_problem_upload(request, competition_id):
    competition = get_object_or_404(Competition, pk=competition_id)

    if not (request.user == competition.user or request.user.is_staff):
        return HttpResponseForbidden("У вас нет разрешения добавлять задачи в это соревнование")

    if request.method == 'POST':
        if 'problem_file' in request.FILES:
            try:
                file = request.FILES['problem_file']

                problems_created = 0

                for line in file:
                    try:
                        line_str = line.decode('utf-8').strip()
                        if line_str:
                            parts = line_str.split('|')
                            if len(parts) >= 3:
                                title, description, difficulty = parts[0], parts[1], parts[2]
                                Problem.objects.create(
                                    competition=competition, title=title, description=description, difficulty=difficulty
                                )
                                problems_created += 1
                    except Exception as e:
                        print(f"Error processing line: {e}")

                messages.success(request, f"{problems_created} задачи были успешно импортированы")
                return redirect('competition-problems', pk=competition_id)

            except Exception as e:
                messages.error(request, f"Error processing file: {e}")
        else:
            messages.error(request, "No file uploaded")
    '''
    ДОПИСАТЬ
    '''
    return render(request, 'problems/bulk_problem_upload.html', {'competition': competition})


@login_required
def problem_batch_operations(request, competition_id):
    competition = get_object_or_404(Competition, pk=competition_id)

    # Check permissions
    if not (request.user == competition.user or request.user.is_staff):
        return HttpResponseForbidden("У вас нет прав на изменение задач в этом соревновании")

    if request.method == 'POST':
        operation = request.POST.get('operation')
        problem_ids = request.POST.getlist('problem_ids')

        if not problem_ids:
            messages.error(request, "Никаких задач не выбрано")
            return redirect('competition-problems', pk=competition_id)

        problems = Problem.objects.filter(problem_id__in=problem_ids, competition=competition)

        if operation == 'delete':
            count = problems.count()
            problems.delete()
            messages.success(request, f"{count} задач были успешно удалены")

        elif operation == 'change_difficulty':
            new_difficulty = request.POST.get('new_difficulty')
            if new_difficulty:
                problems.update(difficulty=new_difficulty)
                messages.success(request, f"Сложность обновлена для {problems.count()} задач")
            else:
                messages.error(request, "Новый уровень сложности не указан")

        return redirect('competition-problems', pk=competition_id)

    '''
    ДОПИСАТЬ
    '''
    return render(
        request,
        'problems/problem_batch_operations.html',
        {
            'competition': competition,
            'problems': Problem.objects.filter(competition=competition),
            'difficulties': Problem.objects.values_list('difficulty', flat=True).distinct(),
        },
    )


@login_required
def export_problems_api(request, competition_id):
    competition = get_object_or_404(Competition, pk=competition_id)

    if not (request.user == competition.user or request.user.is_staff):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)

    problems = Problem.objects.filter(competition=competition)

    problems_data = [
        {'problem_id': p.problem_id, 'title': p.title, 'description': p.description, 'difficulty': p.difficulty}
        for p in problems
    ]

    return JsonResponse({'competition': {'id': competition.id, 'title': competition.title}, 'problems': problems_data})


@login_required
def import_problems_api(request, competition_id):
    competition = get_object_or_404(Competition, pk=competition_id)

    # Check permissions
    if not (request.user == competition.user or request.user.is_staff):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)

    if request.method == 'POST':
        try:
            import json

            data = json.loads(request.body)
            problems_data = data.get('problems', [])

            created_count = 0
            for p_data in problems_data:
                Problem.objects.create(
                    competition=competition,
                    title=p_data.get('title', 'Untitled'),
                    description=p_data.get('description', ''),
                    difficulty=p_data.get('difficulty', 'Medium'),
                )
                created_count += 1

            return JsonResponse({'success': True, 'message': f'{created_count} задач успешно импортированы'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Некорректный JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Только POST метод'}, status=405)


@login_required
def manage_test_cases(request, problem_id):
    problem = get_object_or_404(Problem, problem_id=problem_id)

    # Проверяем права доступа
    if not (request.user == problem.competition.user or request.user.is_staff):
        return HttpResponseForbidden("У вас нет прав для управления тестами")

    # Получаем все тестовые случаи
    test_cases = TestCase.objects.filter(problem=problem).order_by('order')

    if request.method == 'POST':
        form = TestCaseForm(request.POST)
        if form.is_valid():
            test_case = form.save(commit=False)
            test_case.problem = problem
            test_case.save()
            messages.success(request, "Тестовый случай создан успешно")
            return redirect('manage-test-cases', problem_id=problem_id)
    else:
        form = TestCaseForm()

    return render(
        request,
        'problems/manage_test_cases.html',
        {
            'problem': problem,
            'test_cases': test_cases,
            'form': form,
        },
    )


@login_required
def edit_test_case(request, test_id):
    test_case = get_object_or_404(TestCase, id=test_id)
    problem = test_case.problem

    # Проверяем права доступа
    if not (request.user == problem.competition.user or request.user.is_staff):
        return HttpResponseForbidden("У вас нет прав для редактирования тестов")

    if request.method == 'POST':
        form = TestCaseForm(request.POST, instance=test_case)
        if form.is_valid():
            form.save()
            messages.success(request, "Тестовый случай обновлен успешно")
            return redirect('manage-test-cases', problem_id=problem.problem_id)
    else:
        form = TestCaseForm(instance=test_case)

    return render(request, 'problem/edit_test_case.html', {'form': form, 'test_case': test_case, 'problem': problem})


@login_required
def delete_test_case(request, test_id):
    test_case = get_object_or_404(TestCase, id=test_id)
    problem = test_case.problem

    # Проверяем права доступа
    if not (request.user == problem.competition.user or request.user.is_staff):
        return HttpResponseForbidden("У вас нет прав для удаления тестов")

    if request.method == 'POST':
        problem_id = problem.problem_id
        test_case.delete()
        messages.success(request, "Тестовый случай удален успешно")
        return redirect('manage-test-cases', problem_id=problem_id)

    return redirect('manage-test-cases', problem_id=problem.problem_id)
