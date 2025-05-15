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


class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField(help_text="Входные данные для тестирования", null=True, blank=True)
    expected_output = models.TextField(help_text="Ожидаемый вывод")
    is_sample = models.BooleanField(default=False, help_text="Является ли этот тест образцом")
    order = models.IntegerField(default=0, help_text="Порядок выполнения тестов")
    points = models.IntegerField(default=1, help_text="Баллы за прохождение теста")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"TestCase {self.id} for Problem {self.problem.title}"


class TestResult(models.Model):
    RESULT_CHOICES = [
        ('AC', 'Accepted'),
        ('WA', 'Wrong Answer'),
        ('TLE', 'Time Limit Exceeded'),
        ('MLE', 'Memory Limit Exceeded'),
        ('RE', 'Runtime Error'),
        ('CE', 'Compilation Error'),
        ('SE', 'System Error'),
    ]

    submission = models.ForeignKey('submission.Submission', on_delete=models.CASCADE, related_name='test_results')
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    result = models.CharField(max_length=3, choices=RESULT_CHOICES)
    execution_time = models.IntegerField(null=True, blank=True, help_text="Время выполнения в миллисекундах")
    memory_used = models.IntegerField(null=True, blank=True, help_text="Использованная память в килобайтах")
    output = models.TextField(blank=True, help_text="Фактический вывод программы")
    error_message = models.TextField(blank=True, help_text="Сообщение об ошибке, если есть")

    class Meta:
        unique_together = ('submission', 'test_case')

    def __str__(self):
        return f"{self.get_result_display()} for Submission {self.submission.id}, Test {self.test_case.id}"
