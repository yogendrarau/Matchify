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

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        # Basic validation: must end with .edu (case-insensitive)
        if not email.lower().endswith('.edu'):
            raise forms.ValidationError('You must sign up with a .edu email address.')
        return email

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password', 'passwordrepeat']


class EditProfileForm(forms.Form):
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3, 'placeholder':'Tell others about yourself'}), max_length=2000)


from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Share something with the community...',
                'class': 'w-full p-3 rounded bg-gray-900 text-white placeholder-gray-400'
            })
        }
        labels = {
            'content': ''
        }

    from django.forms import ClearableFileInput
    image = forms.FileField(required=False, widget=ClearableFileInput(attrs={'class': 'hidden', 'id': 'post-image-input'}))


class ProfileImageForm(forms.Form):
    image = forms.ImageField(required=True)

from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Write a comment...',
                'class': 'w-full p-2 rounded bg-gray-900 text-white placeholder-gray-400 text-sm'
            })
        }
        labels = {
            'content': ''
        }
