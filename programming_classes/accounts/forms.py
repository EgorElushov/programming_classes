from django import forms
from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Account


class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

class RoleForm(ModelForm):
    CHOICES = [
        ('student', 'Ученик'),
        ('teacher', 'Преподаватель'),
    ]
    role = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=CHOICES,
    )

    class Meta:
        model = Account
        fields = ['role']
