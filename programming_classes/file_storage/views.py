from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse, FileResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.core.files.storage import default_storage
from django.conf import settings

import os, re
import mimetypes
from wsgiref.util import FileWrapper

from .models import CourseMaterial
from course.models import Course, Enrollment
from .forms import CourseMaterialForm


class CourseMaterialListView(LoginRequiredMixin, ListView):
    model = CourseMaterial
    template_name = 'file_storage/material_list.html'
    context_object_name = 'materials'
    paginate_by = 20

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')

        if course_id:
            course = get_object_or_404(Course, course_id=course_id)

            is_enrolled = Enrollment.objects.filter(user=self.request.user, course=course).exists()
            is_creator = self.request.user == course.created_by

            if not (is_enrolled or is_creator or self.request.user.is_staff):
                return CourseMaterial.objects.none()

            queryset = CourseMaterial.objects.filter(course=course)
        else:
            if self.request.user.is_staff:
                queryset = CourseMaterial.objects.all()
            else:
                enrolled_courses = Course.objects.filter(enrollments__user=self.request.user)
                created_courses = Course.objects.filter(created_by=self.request.user)

                queryset = CourseMaterial.objects.filter(
                    Q(course__in=enrolled_courses) | Q(course__in=created_courses)
                ).distinct()

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))

        file_type = self.request.GET.get('file_type')
        if file_type:
            queryset = queryset.filter(file_type=file_type)

        sort_by = self.request.GET.get('sort_by', 'upload_date')
        sort_direction = self.request.GET.get('sort_direction', 'desc')

        if sort_direction == 'asc':
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by(f'-{sort_by}')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs.get('course_id')

        if course_id:
            context['course'] = get_object_or_404(Course, course_id=course_id)
            context['is_course_creator'] = self.request.user == context['course'].created_by

        context['file_types'] = CourseMaterial.FILE_TYPES

        return context


class CourseMaterialDetailView(LoginRequiredMixin, DetailView):
    model = CourseMaterial
    template_name = 'file_storage/material_detail.html'
    context_object_name = 'material'

    def get_object(self):
        material = super().get_object()
        course = material.course

        is_enrolled = Enrollment.objects.filter(user=self.request.user, course=course).exists()
        is_creator = self.request.user == course.created_by

        if not (is_enrolled or is_creator or self.request.user.is_staff):
            raise HttpResponseForbidden("У вас нет разрешения на доступ к этому материалу")

        return material

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        material = self.get_object()

        context['course'] = material.course
        context['is_course_creator'] = self.request.user == material.course.created_by
        context['is_material_uploader'] = self.request.user == material.uploaded_by
        context['can_edit'] = (
            self.request.user == material.uploaded_by
            or self.request.user == material.course.created_by
            or self.request.user.is_staff
        )

        return context


@login_required
def download_material(request, pk):
    material = get_object_or_404(CourseMaterial, pk=pk)
    course = material.course

    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    is_creator = request.user == course.created_by

    if not (is_enrolled or is_creator or request.user.is_staff):
        return HttpResponseForbidden("У вас нет разрешения на загрузку этого материала")

    file_path = material.file.path

    if not os.path.exists(file_path):
        messages.error(request, "Файл не найден на сервере.")
        return redirect('material-detail', pk=pk)

    file_wrapper = FileWrapper(open(file_path, 'rb'))
    file_mimetype = mimetypes.guess_type(file_path)[0]

    response = FileResponse(file_wrapper, content_type=file_mimetype)
    response['Content-Length'] = os.path.getsize(file_path)
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'

    return response


'''
ДОПИСАТЬ
'''


class CourseMaterialCreateView(LoginRequiredMixin, CreateView):
    model = CourseMaterial
    form_class = CourseMaterialForm
    template_name = 'file_storage/material_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, course_id=self.kwargs.get('course_id'))

        if not (request.user == self.course.created_by or request.user.is_staff):
            return HttpResponseForbidden("У вас нет разрешения на добавление материалов в этот курс")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.course = self.course
        form.instance.uploaded_by = self.request.user

        file = self.request.FILES.get('file')
        if file:
            ext = os.path.splitext(file.name)[1][1:].lower()

            if ext in ['pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx']:
                form.instance.file_type = 'document'
            elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv']:
                form.instance.file_type = 'video'
            elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']:
                form.instance.file_type = 'image'
            elif ext in ['mp3', 'wav', 'ogg', 'flac']:
                form.instance.file_type = 'audio'
            elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
                form.instance.file_type = 'archive'
            else:
                form.instance.file_type = 'other'

        messages.success(self.request, "Материал успешно загружен!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('course-materials', kwargs={'course_id': self.course.course_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context


'''
ДОПИСАТЬ
'''


class CourseMaterialUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CourseMaterial
    fields = ['title', 'description']
    template_name = 'file_storage/material_update_form.html'

    def test_func(self):
        material = self.get_object()
        return (
            self.request.user == material.uploaded_by
            or self.request.user == material.course.created_by
            or self.request.user.is_staff
        )

    def form_valid(self, form):
        messages.success(self.request, "Материал успешно загружен!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('material-detail', kwargs={'pk': self.object.pk})


class CourseMaterialDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CourseMaterial
    template_name = 'file_storage/material_confirm_delete.html'

    def test_func(self):
        material = self.get_object()
        return (
            self.request.user == material.uploaded_by
            or self.request.user == material.course.created_by
            or self.request.user.is_staff
        )

    def delete(self, request, *args, **kwargs):
        material = self.get_object()
        course_id = material.course.course_id

        messages.success(request, "Материал успешно удален!")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('course-materials', kwargs={'course_id': self.object.course.course_id})


@login_required
def bulk_upload_materials(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)

    if not (request.user == course.created_by or request.user.is_staff):
        return HttpResponseForbidden("У вас нет разрешения на загрузку материалов для этого курса")

    if request.method == 'POST':
        files = request.FILES.getlist('files')

        if not files:
            messages.error(request, "Нет выбранных файлов.")
            return redirect('bulk-upload-materials', course_id=course_id)

        count = 0
        for file in files:
            title = os.path.splitext(file.name)[0]
            ext = os.path.splitext(file.name)[1][1:].lower()

            if ext in ['pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx']:
                file_type = 'document'
            elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv']:
                file_type = 'video'
            elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']:
                file_type = 'image'
            elif ext in ['mp3', 'wav', 'ogg', 'flac']:
                file_type = 'audio'
            elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
                file_type = 'archive'
            else:
                file_type = 'other'

            material = CourseMaterial(
                title=title, file=file, file_type=file_type, course=course, uploaded_by=request.user
            )
            material.save()
            count += 1

        messages.success(request, f"{count} материалов успешно загружены!")
        return redirect('course-materials', course_id=course_id)

    return render(request, 'file_storage/bulk_upload.html', {'course': course})


@login_required
def material_preview(request, pk):
    material = get_object_or_404(CourseMaterial, pk=pk)
    course = material.course

    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    is_creator = request.user == course.created_by

    if not (is_enrolled or is_creator or request.user.is_staff):
        return HttpResponseForbidden("У вас нет разрешения на предварительный просмотр этого материала")

    file_path = material.file.path

    if not os.path.exists(file_path):
        messages.error(request, "Файл не найден на сервере.")
        return redirect('material-detail', pk=pk)

    file_ext = os.path.splitext(file_path)[1][1:].lower()

    if material.file_type == 'document' and file_ext in ['pdf']:
        file_wrapper = FileWrapper(open(file_path, 'rb'))
        response = FileResponse(file_wrapper, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        return response

    elif material.file_type == 'image':
        file_wrapper = FileWrapper(open(file_path, 'rb'))
        file_mimetype = mimetypes.guess_type(file_path)[0]
        response = FileResponse(file_wrapper, content_type=file_mimetype)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        return response

    elif material.file_type == 'video':
        return render(request, 'file_storage/video_preview.html', {'material': material})

    elif material.file_type == 'audio':
        return render(request, 'file_storage/audio_preview.html', {'material': material})

    else:
        messages.info(request, "Предварительный просмотр недоступен для этого типа файлов. Вместо этого загружаем.")
        return redirect('download-material', pk=pk)


@login_required
def course_materials_api(request, course_id):
    """API endpoint to get materials for a course"""
    try:
        course = Course.objects.get(course_id=course_id)

        is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
        is_creator = request.user == course.created_by

        if not (is_enrolled or is_creator or request.user.is_staff):
            return JsonResponse({'error': 'У вас нет разрешения на доступ к этим материалам'}, status=403)

        materials = CourseMaterial.objects.filter(course=course).order_by('-upload_date')

        materials_data = [
            {
                'id': material.id,
                'title': material.title,
                'description': material.description,
                'file_type': material.file_type,
                'upload_date': material.upload_date.isoformat(),
                'uploaded_by': material.uploaded_by.username,
                'file_url': request.build_absolute_uri(reverse('download-material', kwargs={'pk': material.pk})),
                'file_size': material.file_size(),
                'file_extension': material.file_extension(),
            }
            for material in materials
        ]

        return JsonResponse({'materials': materials_data})

    except Course.DoesNotExist:
        return JsonResponse({'error': 'Курс не найден'}, status=404)


@login_required
def upload_material_api(request, course_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Только POST запросы разрешены'}, status=405)

    try:
        course = Course.objects.get(course_id=course_id)

        if not (request.user == course.created_by or request.user.is_staff):
            return JsonResponse({'error': 'У вас нет разрешения на загрузку материалов для этого курса'}, status=403)

        file = request.FILES.get('file')
        title = request.POST.get('title')
        description = request.POST.get('description', '')

        if not file:
            return JsonResponse({'error': 'Файл не предоставлен'}, status=400)

        if not title:
            title = os.path.splitext(file.name)[0]

        ext = os.path.splitext(file.name)[1][1:].lower()

        if ext in ['pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx']:
            file_type = 'document'
        elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv']:
            file_type = 'video'
        elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']:
            file_type = 'image'
        elif ext in ['mp3', 'wav', 'ogg', 'flac']:
            file_type = 'audio'
        elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
            file_type = 'archive'
        else:
            file_type = 'other'

        material = CourseMaterial(
            title=title,
            description=description,
            file=file,
            file_type=file_type,
            course=course,
            uploaded_by=request.user,
        )
        material.save()

        return JsonResponse(
            {
                'success': True,
                'message': 'Материал успешно загружен',
                'material': {
                    'id': material.id,
                    'title': material.title,
                    'file_type': material.file_type,
                    'upload_date': material.upload_date.isoformat(),
                },
            }
        )

    except Course.DoesNotExist:
        return JsonResponse({'error': 'Курс не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def delete_material_api(request, pk):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Только DELETE запросы разрешены'}, status=405)

    try:
        material = CourseMaterial.objects.get(pk=pk)

        if not (
            request.user == material.uploaded_by or request.user == material.course.created_by or request.user.is_staff
        ):
            return JsonResponse({'error': 'У вас нет разрешения на удаление этого материала'}, status=403)

        course_id = material.course.course_id
        material.delete()

        return JsonResponse({'success': True, 'message': 'Материал успешно удален', 'course_id': course_id})

    except CourseMaterial.DoesNotExist:
        return JsonResponse({'error': 'Материал не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def material_statistics(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)

    if not (request.user == course.created_by or request.user.is_staff):
        return HttpResponseForbidden("У вас нет разрешения на просмотр статистики по этому курсу")

    materials = CourseMaterial.objects.filter(course=course)

    file_type_counts = materials.values('file_type').annotate(count=Count('id')).order_by('file_type')

    total_size = sum(material.file_size() for material in materials)

    materials_by_uploader = materials.values('uploaded_by__username').annotate(count=Count('id')).order_by('-count')

    recent_uploads = materials.order_by('-upload_date')[:10]

    return render(
        request,
        'file_storage/material_statistics.html',
        {
            'course': course,
            'total_materials': materials.count(),
            'file_type_counts': file_type_counts,
            'total_size': total_size,
            'materials_by_uploader': materials_by_uploader,
            'recent_uploads': recent_uploads,
        },
    )


@login_required
def serve_material(request, pk):
    material = get_object_or_404(CourseMaterial, pk=pk)
    course = material.course

    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    is_creator = request.user == course.created_by

    if not (is_enrolled or is_creator or request.user.is_staff):
        return HttpResponseForbidden("У вас нет разрешения на доступ к этому материалу")

    file_path = material.file.path

    if not os.path.exists(file_path):
        return HttpResponse("Файл не найден", status=404)

    content_type = mimetypes.guess_type(file_path)[0]

    response = FileResponse(open(file_path, 'rb'), content_type=content_type)

    range_header = request.META.get('HTTP_RANGE', '').strip()
    if range_header:
        file_size = os.path.getsize(file_path)

        range_match = re.match(r'bytes=(?P<start>\d+)-(?P<end>\d*)', range_header)
        if range_match:
            start = int(range_match.group('start'))
            end = int(range_match.group('end')) if range_match.group('end') else file_size - 1

            if start >= file_size:
                return HttpResponse(status=416)

            end = min(end, file_size - 1)
            length = end - start + 1

            response = FileResponse(
                RangeFileWrapper(open(file_path, 'rb'), start, length), content_type=content_type, status=206
            )
            response['Content-Length'] = str(length)
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'

        else:
            response['Content-Length'] = str(os.path.getsize(file_path))

    response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'

    return response


class RangeFileWrapper:
    def __init__(self, fileobj, start, length):
        self.fileobj = fileobj
        self.start = start
        self.remaining = length

    def __iter__(self):
        self.fileobj.seek(self.start)
        return self

    def __next__(self):
        if self.remaining <= 0:
            raise StopIteration

        chunk_size = min(8192, self.remaining)
        data = self.fileobj.read(chunk_size)

        if not data:
            raise StopIteration

        self.remaining -= len(data)
        return data
