from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy

from .models import Competition
from .forms import CompetitionForm
from problem.models import Problem
from submission.models import Submission


class CompetitionListView(ListView):
    model = Competition
    template_name = 'contests/competition_list.html'
    context_object_name = 'competitions'
    paginate_by = 10

    def get_queryset(self):
        queryset = Competition.objects.all()

        status_filter = self.request.GET.get('status')
        today = timezone.now().date()

        if status_filter == 'active':
            queryset = queryset.filter(start_date__lte=today, end_date__gte=today)
        elif status_filter == 'upcoming':
            queryset = queryset.filter(start_date__gt=today)
        elif status_filter == 'past':
            queryset = queryset.filter(end_date__lt=today)

        return queryset.order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        context['active_count'] = Competition.objects.filter(start_date__lte=today, end_date__gte=today).count()

        context['upcoming_count'] = Competition.objects.filter(start_date__gt=today).count()
        context['today'] = today

        return context


class CompetitionDetailView(DetailView):
    model = Competition
    template_name = 'contests/competition_detail.html'
    context_object_name = 'competition'
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
            
        competition = self.get_object()
        today = timezone.now().date()
        is_active = competition.start_date <= today <= competition.end_date
        
        if not is_active:
            messages.error(request, "Невозможно присоединиться к неактивному соревнованию.")
            return redirect('competition-detail', pk=competition.pk)
            
        if request.user in competition.partisipants.all():
            messages.info(request, "Вы уже участвуете в этом соревновании.")
        else:
            competition.partisipants.add(request.user)
            messages.success(request, "Вы успешно присоединились к соревнованию!")
            
        return redirect('competition-detail', pk=competition.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        competition = self.get_object()
        
        context['problems'] = Problem.objects.filter(competition=competition)
        
        today = timezone.now().date()
        context['today'] = today
        
        context['is_active'] = competition.start_date <= today <= competition.end_date
        
        participants = competition.partisipants.all().order_by('email')
        
        standings = []
        for participant in participants:
            score = 0
            
            standings.append({
                'user': participant,
                'score': score
            })
        
        standings = sorted(standings, key=lambda x: x['score'], reverse=True)
        context['standings'] = standings
        
        # Проверка, является ли пользователь участником и добавление данных участия
        if self.request.user.is_authenticated:
            context['is_participant'] = self.request.user in participants
            
            # Проверка прав на редактирование
            context['can_edit'] = (self.request.user == competition.user or 
                                 self.request.user.is_staff)
            
            # Инициализация participation как None
            context['participation'] = None
            
            # Поиск текущего пользователя в таблице лидеров
            for i, entry in enumerate(standings):
                if entry['user'] == self.request.user:
                    participation = {
                        'user': self.request.user,
                        'score': entry['score'],
                        'rank': i + 1
                    }
                    context['participation'] = participation
                    break
        
        return context


class CompetitionCreateView(LoginRequiredMixin, CreateView):
    model = Competition
    form_class = CompetitionForm
    template_name = 'contests/competition_form.html'
    success_url = reverse_lazy('competition-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Контест успешно создан!")
        return super().form_valid(form)


class CompetitionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Competition
    form_class = CompetitionForm
    template_name = 'contests/competition_form.html'

    def test_func(self):
        competition = self.get_object()
        return self.request.user == competition.user or self.request.user.is_staff

    def get_success_url(self):
        return reverse_lazy('competition-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Контест успешно обновлен!")
        return super().form_valid(form)


class CompetitionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Competition
    success_url = reverse_lazy('competition-list')
    template_name = 'contests/competition_confirm_delete.html'

    def test_func(self):
        competition = self.get_object()
        return self.request.user == competition.user or self.request.user.is_staff

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Контест успешно удален!")
        return super().delete(request, *args, **kwargs)


@login_required
def competition_management(request, pk):
    competition = get_object_or_404(Competition, pk=pk)

    if not (request.user == competition.user or request.user.is_staff):
        return HttpResponseForbidden("У вас нет прав для управления контестом")

    if request.method == 'POST':
        form = CompetitionForm(request.POST, instance=competition)
        if form.is_valid():
            form.save()
            messages.success(request, "Контест успешно обновлен")
            return redirect('competition-management', pk=competition.pk)
    else:
        form = CompetitionForm(instance=competition)

    today = timezone.now().date()
    if competition.start_date <= today <= competition.end_date:
        status = "active"
    elif competition.start_date > today:
        status = "upcoming"
    else:
        status = "past"

    return render(
        request, 'contests/competition_management.html', {'competition': competition, 'form': form, 'status': status}
    )
    '''
    ДОПИСАТЬ
    '''


@login_required
def codeforces_import(request):
    if request.method == 'POST':
        messages.success(request, "Задача успешно импортирована из Codeforces")
        return redirect('competition-list')

    return render(request, 'contests/codeforces_import.html')


@login_required
def yandex_contest_import(request):
    if request.method == 'POST':
        '''пока заглушка'''
        messages.success(request, "Задача успешно импортирована из Yandex.Contest")
        return redirect('competition-list')

    return render(request, 'contests/yandex_import.html')


def competition_statistics(request, pk):
    '''
    ДОПИСАТЬ
    '''
    competition = get_object_or_404(Competition, pk=pk)

    stats = {
        'total_participants': 45,
        'submissions': 230,
        'successful_submissions': 120,
        'average_score': 75.5,
    }

    return render(request, 'contests/competition_statistics.html', {'competition': competition, 'stats': stats})
