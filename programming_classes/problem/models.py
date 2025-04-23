from django.db import models
from competition.models import Competition


class Problem(models.Model):
    problem_id = models.AutoField(primary_key=True)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    difficulty = models.CharField(max_length=50)

    def __str__(self):
        return self.title
