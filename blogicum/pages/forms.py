from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Email адрес',
        help_text='Обязательное поле. Введите действующий email.'
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label='Имя',
        help_text='Необязательное поле.'
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        label='Фамилия',
        help_text='Необязательное поле.'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user
