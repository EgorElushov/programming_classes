from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic import CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

from .forms import RegisterForm, RoleForm, UserUpdateForm, ProfileUpdateForm
from .models import Account, Role
from course.models import Course, Enrollment


class RegisterView(CreateView):
    template_name = 'accounts/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'role_form' not in context:
            context['role_form'] = RoleForm()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.instance

        role_form = RoleForm(self.request.POST)
        if role_form.is_valid():
            role = role_form.save(commit=False)
            role.user = user
            role.save()

            login(self.request, user)
            messages.success(self.request, "Регистрация успешна! Добро пожаловать.")
            return response
        else:
            messages.error(
                self.request, "Не удалось зарегистрироваться. Пожалуйста, проверьте форму на наличие ошибок."
            )
            return self.render_to_response(self.get_context_data(form=form, role_form=role_form))

    def form_invalid(self, form):
        role_form = RoleForm(self.request.POST)
        messages.error(self.request, "Не удалось зарегистрироваться. Пожалуйста, проверьте форму на наличие ошибок.")
        return self.render_to_response(self.get_context_data(form=form, role_form=role_form))


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_form'] = context['form']
        return context

    def form_valid(self, form):
        messages.success(self.request, f"С возвращением, {form.get_user().username}!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Ошибка входа. Пожалуйста, проверьте свое имя пользователя и пароль.")
        return super().form_invalid(form)

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('home')


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('home')

    def dispatch(self, request, *args, **kwargs):
        was_authenticated = request.user.is_authenticated

        response = super().dispatch(request, *args, **kwargs)
        logout(request)

        if was_authenticated:
            messages.info(request, "Вы вышли из аккаунта.")

        return redirect(self.next_page)

    http_method_names = ['get', 'post', 'head', 'options']


@login_required
def profile(request):
    """View function for user profile page"""
    return render(request, 'accounts/profile.html')


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Account
    form_class = UserUpdateForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('profile')

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == 'POST':
            context['profile_form'] = ProfileUpdateForm(
                self.request.POST, self.request.FILES, instance=self.request.user.role
            )
        else:
            context['profile_form'] = ProfileUpdateForm(instance=self.request.user.role)
        return context

    def form_valid(self, form):
        profile_form = ProfileUpdateForm(self.request.POST, self.request.FILES, instance=self.request.user.role)

        if profile_form.is_valid():
            profile_form.save()
            messages.success(self.request, "Ваш профиль был успешно обновлен.")
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form, profile_form=profile_form))


class UserDetailView(DetailView):
    model = Account
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_profile'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        try:
            from submission.models import Submission

            context['submission_count'] = Submission.objects.filter(user=user).count()
            context['accepted_submissions'] = Submission.objects.filter(user=user, status='accepted').count()
        except ImportError:
            pass

        try:
            context['created_courses'] = Course.objects.filter(created_by=user).count()
            context['enrolled_courses'] = Enrollment.objects.filter(user=user).count()
        except ImportError:
            pass

        return context
