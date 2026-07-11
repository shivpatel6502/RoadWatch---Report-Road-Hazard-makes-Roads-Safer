"""
RoadWatch — reports/forms.py
Phase 2: User registration, report submission, profile edit, comment forms.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import HazardReport, ReportPhoto, Profile, Comment, HazardType, SeverityLevel, ReportStatus


# ---------------------------------------------------------------------------
# Bootstrap 5 mixin — injects form-control / form-select classes automatically
# ---------------------------------------------------------------------------

class BootstrapMixin:
    """Adds Bootstrap 5 CSS classes to every widget in the form."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault('class', 'form-select rw-select')
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('class', 'form-control rw-input')
                widget.attrs.setdefault('rows', 4)
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, (forms.FileInput, forms.ClearableFileInput)):
                widget.attrs.setdefault('class', 'form-control rw-file-input')
            else:
                widget.attrs.setdefault('class', 'form-control rw-input')


# ---------------------------------------------------------------------------
# 1. User Registration Form
# ---------------------------------------------------------------------------

class UserRegistrationForm(BootstrapMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
    )
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Last name'}),
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Windsor, Toronto'}),
        help_text='Your home city for personalised hazard reports.',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Choose a username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Friendlier labels
        self.fields['password1'].widget.attrs['placeholder'] = 'Create a password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Repeat password'
        self.fields['password1'].help_text = 'At least 8 characters.'
        self.fields['password2'].help_text = ''

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


# ---------------------------------------------------------------------------
# 2. Hazard Report Submission Form
# ---------------------------------------------------------------------------

class HazardReportForm(BootstrapMixin, forms.ModelForm):
    # Up to 3 separate photo fields so we can enforce the limit cleanly
    photo1 = forms.ImageField(
        required=False,
        label='Photo 1',
        widget=forms.FileInput(attrs={'accept': 'image/*'}),
    )
    photo2 = forms.ImageField(
        required=False,
        label='Photo 2',
        widget=forms.FileInput(attrs={'accept': 'image/*'}),
    )
    photo3 = forms.ImageField(
        required=False,
        label='Photo 3',
        widget=forms.FileInput(attrs={'accept': 'image/*'}),
    )

    class Meta:
        model = HazardReport
        fields = [
            'title', 'hazard_type', 'severity',
            'city', 'street', 'latitude', 'longitude',
            'description', 'document',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Brief descriptive title of the hazard'}),
            'city': forms.TextInput(attrs={'placeholder': 'e.g. Windsor'}),
            'street': forms.TextInput(attrs={'placeholder': 'e.g. Wyandotte St E & Gladstone Ave'}),
            'latitude': forms.NumberInput(attrs={'placeholder': 'e.g. 42.3193', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'placeholder': 'e.g. -83.0289', 'step': 'any'}),
            'description': forms.Textarea(attrs={
                'placeholder': 'Describe the hazard in detail. Include size, exact location, any injuries or damage caused.',
                'rows': 5,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['document'].help_text = 'Optional: attach a PDF, image, or document (max 10 MB).'


# ---------------------------------------------------------------------------
# 3. User (User model fields) Update Form
# ---------------------------------------------------------------------------

class UserUpdateForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name':  forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email':      forms.EmailInput(attrs={'placeholder': 'Email address'}),
        }


# ---------------------------------------------------------------------------
# 4. Profile Update Form
# ---------------------------------------------------------------------------

class ProfileUpdateForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['city', 'bio', 'phone', 'avatar']
        widgets = {
            'city':  forms.TextInput(attrs={'placeholder': 'Your city'}),
            'bio':   forms.Textarea(attrs={'placeholder': 'Tell the community about yourself', 'rows': 3}),
            'phone': forms.TextInput(attrs={'placeholder': 'Optional phone number'}),
        }


# ---------------------------------------------------------------------------
# 5. Comment Form
# ---------------------------------------------------------------------------

class CommentForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'placeholder': 'Add your comment or additional details about this hazard…',
                'rows': 3,
            }),
        }
        labels = {'text': ''}
