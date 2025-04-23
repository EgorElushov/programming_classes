from django import forms
from .models import Submission


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['code']
        widgets = {
            'code': forms.Textarea(
                attrs={'class': 'code-editor', 'rows': 15, 'placeholder': 'Напиши свой код здесь...'}
            ),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code or len(code.strip()) == 0:
            raise forms.ValidationError("Code cannot be empty")
        return code
