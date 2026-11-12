from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email']
        labels = {'first_name': 'სახელი', 'last_name': 'გვარი'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ['first_name', 'last_name']:
            self.fields[name].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label='ელ-ფოსტა')
    password = forms.CharField(label='პაროლი', widget=forms.PasswordInput)
