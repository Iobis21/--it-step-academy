from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'personal_id', 'phone', 'email']
        labels = {'first_name': 'სახელი', 'last_name': 'გვარი', 'phone': 'მობილურის ნომერი'}
        widgets = {
            'personal_id': forms.TextInput(attrs={'placeholder': '11 ციფრი', 'inputmode': 'numeric', 'maxlength': 11}),
            'phone': forms.TextInput(attrs={'placeholder': '5XXXXXXXX', 'inputmode': 'tel', 'maxlength': 9}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@mail.com'}),
        }
        error_messages = {
            'email': {'unique': 'ამ ელ-ფოსტით ანგარიში უკვე არსებობს'},
            'phone': {'unique': 'ეს მობილურის ნომერი უკვე დარეგისტრირებულია'},
            'personal_id': {'unique': 'ამ პირადი ნომრით ანგარიში უკვე არსებობს'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ['first_name', 'last_name', 'personal_id']:
            self.fields[name].required = True
        self.fields['password1'].label = 'პაროლი'
        self.fields['password2'].label = 'გაიმეორე პაროლი'
        self.fields['password1'].help_text = 'მინიმუმ 8 სიმბოლო, არ უნდა იყოს მხოლოდ ციფრები'
        self.fields['password2'].help_text = ''

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label='ელ-ფოსტა')
    password = forms.CharField(label='პაროლი', widget=forms.PasswordInput)
