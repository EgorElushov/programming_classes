from django.urls import path

from . import views

urlpatterns = [
    path("welcome", views.unloginpage, name="welcome"),
    path("", views.home_page, name="homepage"),
]