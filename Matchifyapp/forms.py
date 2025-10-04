# forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django_recaptcha.fields import ReCaptchaField, ReCaptchaV2Checkbox

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    passwordrepeat = forms.CharField(widget=forms.PasswordInput, label="Repeat Password")
    captcha = ReCaptchaField()

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password', 'passwordrepeat']


class EditProfileForm(forms.Form):
    bio = forms.CharField(widget=forms.Textarea(attrs={'rows':4, 'class':'w-full p-2 rounded bg-gray-800 text-gray-200'}), required=False, label='About')