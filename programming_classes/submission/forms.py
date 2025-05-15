from django import forms
from .models import Submission
from checker.consts import PROGRAMMING_LANGUAGES


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['programming_language', 'code']
        widgets = {
            'programming_language': forms.Select(attrs={'class': 'form-control'}),
            'code': forms.Textarea(
                attrs={'class': 'code-editor', 'rows': 15, 'placeholder': 'Напиши свой код здесь...'}
            ),
        }
    programming_language = forms.ChoiceField(choices=PROGRAMMING_LANGUAGES, required=True)

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code or len(code.strip()) == 0:
            raise forms.ValidationError("Нельзя сдать пустое решение")
        return code
