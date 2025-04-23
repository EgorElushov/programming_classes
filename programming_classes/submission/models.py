from django.db import models
from accounts.models import Account
from problem.models import Problem


class Submission(models.Model):
    """
    Django model representing the Submissions table
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    submission_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')

    code = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=False)

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Optional: Add any additional metadata
        db_table = 'submissions'
        ordering = ['-submitted_at']
        verbose_name_plural = 'Submissions'

    def __str__(self):
        """"""
