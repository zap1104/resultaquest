from django import forms

from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'title',
            'description',
            'syllabus_text',
            'modules_text',
            'activities_text',
            'assignments_text',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. Technopreneurship',
                'autofocus': True,
            }),
            'description': forms.TextInput(attrs={
                'placeholder': 'One line about this course (optional)',
            }),
            'syllabus_text': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Paste your syllabus here...',
            }),
            'modules_text': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Paste your modules / topics here...',
            }),
            'activities_text': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Paste your class activities here...',
            }),
            'assignments_text': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Paste your assignments here...',
            }),
        }
