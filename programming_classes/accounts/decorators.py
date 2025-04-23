from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def instructor_required(view_func):
    view_func.instructor_only = True

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role.role_type == 'instructor':
            return view_func(request, *args, **kwargs)

        messages.error(request, "Вы должны быть преподавателем, чтобы получить доступ к этой странице.")
        return redirect(reverse('home'))

    return _wrapped_view
