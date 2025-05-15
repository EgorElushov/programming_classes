from django import forms
from .models import Problem, TestCase
from competition.models import Competition


class ProblemForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['title', 'description', 'difficulty', 'competition']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # Allow passing a competition to restrict the form
        competition = kwargs.pop('competition', None)
        super().__init__(*args, **kwargs)

        # If competition is provided, use it as the only option
        if competition:
            self.fields['competition'].initial = competition
            self.fields['competition'].widget = forms.HiddenInput()
            self.fields['competition'].queryset = Competition.objects.filter(pk=competition.pk)
        else:
            # Otherwise, show all available competitions
            self.fields['competition'].queryset = Competition.objects.all()

        # Define difficulty choices
        self.fields['difficulty'].widget = forms.Select(
            choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard'), ('Expert', 'Expert')]
        )

class TestCaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['input_data', 'expected_output', 'is_sample', 'order', 'points']
        widgets = {
            'input_data': forms.Textarea(attrs={'rows': 5, 'required': False}),
            'expected_output': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поле необязательным
        self.fields['input_data'].required = False

