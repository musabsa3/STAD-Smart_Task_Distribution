# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Project, Task, Profile, Submission




class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="First name"
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Last name"
    )
    email = forms.EmailField(
        required=True,
        label="Email address"
    )


    class Meta:
        model = User
        # نفس الحقول اللي تحبها في صفحة التسجيل
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
    
class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["task", "notes", "attachment"]

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }