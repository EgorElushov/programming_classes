from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, null=False)

    def __str__(self):
        return self.user.username
