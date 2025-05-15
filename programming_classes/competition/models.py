from django.db import models
from accounts.models import Account


class Competition(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    partisipants = models.ManyToManyField(Account, related_name='competitions')

    def __str__(self):
        return self.title
