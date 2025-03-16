from django.db import models
from django.conf import settings
from course.models import Course
import os

def course_directory_path(instance, filename):
    return f'courses/{instance.course.course_id}/{filename}'

class CourseMaterial(models.Model):
    FILE_TYPES = [
        ('document', 'Document'),
        ('video', 'Video'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('archive', 'Archive'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=course_directory_path)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    upload_date = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        return self.title
    
    def file_size(self):
        if self.file and hasattr(self.file, 'size'):
            return self.file.size
        return 0
    
    def file_extension(self):
        return os.path.splitext(self.file.name)[1][1:] if self.file else ''
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('material-detail', kwargs={'pk': self.pk})
