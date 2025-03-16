from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q, Count
from django.utils import timezone

from .models import Course, Enrollment
from accounts.models import Account
from file_storage.models import CourseMaterial
from .forms import CourseForm, EnrollmentForm

class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Course.objects.all()
        
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        creator_id = self.request.GET.get('creator')
        if creator_id:
            queryset = queryset.filter(created_by_id=creator_id)
            
        sort_by = self.request.GET.get('sort_by', 'title')
        sort_direction = self.request.GET.get('sort_direction', 'asc')
        
        if sort_direction == 'desc':
            sort_by = f'-{sort_by}'
            
        return queryset.order_by(sort_by)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            enrolled_course_ids = Enrollment.objects.filter(
                user=self.request.user
            ).values_list('course_id', flat=True)
            
            context['enrolled_courses'] = enrolled_course_ids
            
        context['search_query'] = self.request.GET.get('search', '')
        context['sort_by'] = self.request.GET.get('sort_by', 'title')
        context['sort_direction'] = self.request.GET.get('sort_direction', 'asc')
        
        return context

class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    pk_url_kwarg = 'course_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        
        if self.request.user.is_authenticated:
            try:
                enrollment = Enrollment.objects.get(
                    user=self.request.user,
                    course=course
                )
                context['is_enrolled'] = True
                context['enrollment'] = enrollment
            except Enrollment.DoesNotExist:
                context['is_enrolled'] = False
            
            context['is_creator'] = (self.request.user == course.created_by)
            
        context['enrollment_count'] = Enrollment.objects.filter(course=course).count()
        context['recent_enrollments'] = Enrollment.objects.filter(
            course=course
        ).order_by('-enrolled_at')[:5]
        
        context['materials_count'] = CourseMaterial.objects.filter(course=course).count()
        
        return context

class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Course created successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('course-detail', kwargs={'course_id': self.object.course_id})

class CourseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    pk_url_kwarg = 'course_id'
    
    def test_func(self):
        course = self.get_object()
        return self.request.user == course.created_by or self.request.user.is_staff
    
    def form_valid(self, form):
        messages.success(self.request, "Course updated successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('course-detail', kwargs={'course_id': self.object.course_id})

class CourseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    pk_url_kwarg = 'course_id'
    success_url = reverse_lazy('course-list')
    
    def test_func(self):
        course = self.get_object()
        return self.request.user == course.created_by or self.request.user.is_staff
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Course deleted successfully!")
        return super().delete(request, *args, **kwargs)

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, "You are already enrolled in this course.")
        return redirect('course-detail', course_id=course_id)
    
    Enrollment.objects.create(user=request.user, course=course)
    messages.success(request, f"You have successfully enrolled in {course.title}!")
    
    return redirect('course-detail', course_id=course_id)

@login_required
def unenroll_course(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    
    try:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
        enrollment.delete()
        messages.success(request, f"You have been unenrolled from {course.title}.")
    except Enrollment.DoesNotExist:
        messages.error(request, "You are not enrolled in this course.")
    
    return redirect('course-detail', course_id=course_id)

@login_required
def my_courses(request):
    created_courses = Course.objects.filter(created_by=request.user)
    
    enrolled_courses = Course.objects.filter(
        enrollments__user=request.user
    ).exclude(
        created_by=request.user
    )
    
    return render(request, 'courses/my_courses.html', {
        'created_courses': created_courses,
        'enrolled_courses': enrolled_courses
    })

@login_required
def course_enrollments(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    
    if not (request.user == course.created_by or request.user.is_staff):
        return HttpResponseForbidden("You don't have permission to view enrollments for this course")
    
    enrollments = Enrollment.objects.filter(course=course).order_by('-enrolled_at')
    
    return render(request, 'courses/course_enrollments.html', {
        'course': course,
        'enrollments': enrollments,
        'enrollment_count': enrollments.count()
    })

@login_required
def manage_enrollment(request, enrollment_id, action):
    enrollment = get_object_or_404(Enrollment, enrollment_id=enrollment_id)
    course = enrollment.course
    
    if not (request.user == course.created_by or request.user.is_staff):
        return HttpResponseForbidden("You don't have permission to manage enrollments for this course")
    
    if action == 'remove':
        user = enrollment.user
        enrollment.delete()
        messages.success(request, f"{user.username} has been removed from {course.title}.")
    
    return redirect('course-enrollments', course_id=course.course_id)

@login_required
def add_students_to_course(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    
    if not (request.user == course.created_by or request.user.is_staff):
        return HttpResponseForbidden("You don't have permission to add students to this course")
    
    if request.method == 'POST':
        student_identifiers = request.POST.get('students', '').split(',')
        student_identifiers = [s.strip() for s in student_identifiers if s.strip()]
        
        if not student_identifiers:
            messages.error(request, "No students specified.")
            return redirect('course-enrollments', course_id=course_id)
        
        enrolled_count = 0
        already_enrolled_count = 0
        not_found_count = 0
        
        for identifier in student_identifiers:
            user = None
            try:
                if identifier.isdigit():
                    user = Account.objects.get(id=identifier)
                else:
                    user = Account.objects.get(username=identifier)
                    
                if Enrollment.objects.filter(user=user, course=course).exists():
                    already_enrolled_count += 1
                else:
                    Enrollment.objects.create(user=user, course=course)
                    enrolled_count += 1
                    
            except Account.DoesNotExist:
                not_found_count += 1
        
        if enrolled_count > 0:
            messages.success(request, f"{enrolled_count} student(s) successfully enrolled.")
        if already_enrolled_count > 0:
            messages.info(request, f"{already_enrolled_count} student(s) were already enrolled.")
        if not_found_count > 0:
            messages.error(request, f"{not_found_count} student(s) could not be found.")
        
        return redirect('course-enrollments', course_id=course_id)
    
    return render(request, 'courses/add_students.html', {
        'course': course
    })

@login_required
def course_statistics(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    
    if not (request.user == course.created_by or request.user.is_staff):
        return HttpResponseForbidden("You don't have permission to view statistics for this course")
    
    enrollments = Enrollment.objects.filter(course=course)
    total_enrollments = enrollments.count()
    
    from django.db.models.functions import TruncMonth
    
    enrollment_trend = Enrollment.objects.filter(
        course=course
    ).annotate(
        month=TruncMonth('enrolled_at')
    ).values('month').annotate(
        count=Count('enrollment_id')
    ).order_by('month')
    
    materials = CourseMaterial.objects.filter(course=course)
    material_count = materials.count()
    
    material_types = materials.values('file_type').annotate(
        count=Count('id')
    ).order_by('file_type')
    
    return render(request, 'courses/course_statistics.html', {
        'course': course,
        'total_enrollments': total_enrollments,
        'enrollment_trend': enrollment_trend,
        'material_count': material_count,
        'material_types': material_types
    })

@login_required
def course_materials(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    is_creator = (request.user == course.created_by)
    
    if not (is_enrolled or is_creator or request.user.is_staff):
        return HttpResponseForbidden("You must be enrolled in this course to view materials")
    
    materials = CourseMaterial.objects.filter(course=course).order_by('title')
    
    return render(request, 'courses/course_materials.html', {
        'course': course,
        'materials': materials,
        'is_creator': is_creator
    })

@login_required
def course_list_api(request):
    search = request.GET.get('search', '')
    
    courses = Course.objects.all()
    
    if search:
        courses = courses.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search)
        )
    
    courses_data = [
        {
            'course_id': course.course_id,
            'title': course.title,
            'description': course.description,
            'created_by': {
                'id': course.created_by.id,
                'username': course.created_by.username
            },
            'enrollment_count': course.enrollments.count(),
            'material_count': CourseMaterial.objects.filter(course=course).count()
        }
        for course in courses
    ]
    
    return JsonResponse({'courses': courses_data})

@login_required
def course_detail_api(request, course_id):
    try:
        course = Course.objects.get(course_id=course_id)
        
        is_enrolled = False
        if request.user.is_authenticated:
            is_enrolled = Enrollment.objects.filter(
                user=request.user,
                course=course
            ).exists()
        
        materials = CourseMaterial.objects.filter(course=course)
        
        course_data = {
            'course_id': course.course_id,
            'title': course.title,
            'description': course.description,
            'created_by': {
                'id': course.created_by.id,
                'username': course.created_by.username
            },
            'enrollment_count': course.enrollments.count(),
            'is_enrolled': is_enrolled,
            'is_creator': (request.user == course.created_by),
            'materials': [
                {
                    'id': material.id,
                    'title': material.title,
                    'file_type': material.file_type,
                    'upload_date': material.upload_date.isoformat()
                }
                for material in materials
            ]
        }
        
        return JsonResponse(course_data)
        
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)

@login_required
def enroll_course_api(request, course_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        course = Course.objects.get(course_id=course_id)
        
        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return JsonResponse({'error': 'Already enrolled in this course'}, status=400)
        
        enrollment = Enrollment.objects.create(user=request.user, course=course)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully enrolled in {course.title}',
            'enrollment_id': enrollment.enrollment_id,
            'enrolled_at': enrollment.enrolled_at.isoformat()
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)

@login_required
def unenroll_course_api(request, course_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        course = Course.objects.get(course_id=course_id)
        
        try:
            enrollment = Enrollment.objects.get(user=request.user, course=course)
            enrollment.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully unenrolled from {course.title}'
            })
            
        except Enrollment.DoesNotExist:
            return JsonResponse({'error': 'Not enrolled in this course'}, status=400)
        
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)

@login_required
def create_course_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        
        title = data.get('title')
        description = data.get('description', '')
        
        if not title:
            return JsonResponse({'error': 'Title is required'}, status=400)
        
        course = Course.objects.create(
            title=title,
            description=description,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Course created successfully',
            'course_id': course.course_id,
            'title': course.title
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
