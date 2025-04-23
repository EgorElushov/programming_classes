from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse


class Account(AbstractUser):
    def get_absolute_url(self):
        return reverse('user-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username


class Role(models.Model):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Administrator'),
    )

    user = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='role')
    role_type = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_type_display()}"
