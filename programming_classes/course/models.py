from django.db import models
from accounts.models import Account


class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='created_courses')

    class Meta:
        db_table = 'Courses'

        verbose_name_plural = 'Courses'

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    enrollment_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name='Enrollment Timestamp')

    class Meta:
        unique_together = ('user', 'course')
        db_table = 'enrollments'
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'

    def __str__(self):
        return f"{self.user.username} - {self.course.name}"
