from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip middleware for authentication views and static files
        if view_func.__module__ in ['django.contrib.auth.views', 'django.contrib.admin.sites', 'django.views.static']:
            return None

        # Check if it's an instructor-only view
        instructor_only = getattr(view_func, 'instructor_only', False)

        if instructor_only and request.user.is_authenticated:
            try:
                if request.user.role.role_type != 'instructor':
                    messages.error(request, "You must be an instructor to access this page.")
                    return redirect(reverse('home'))
            except:
                # If role doesn't exist
                messages.error(request, "Your account is not properly configured.")
                return redirect(reverse('home'))

        return None
