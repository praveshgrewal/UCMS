# forms.py
from django import forms
from .models import Alumni
import datetime

class AlumniLoginForm(forms.Form):
    contact = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Phone / Email','required': True})
    )

class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Enter OTP','required': True,'maxlength': '6'})
    )

class AlumniRegistrationForm(forms.ModelForm):
    ACADEMIC_CHOICES = [
        ('UG', 'UG'),
        ('PG', 'PG'),
        ('UG_PG', 'UG and PG'),
    ]

    # IMPORTANT: use ChoiceField so posted value matches model choices
    academic_association = forms.ChoiceField(
        choices=ACADEMIC_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'required': True})
    )

    declaration = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Alumni
        fields = [
            'photo', 'name', 'academic_association', 'joining_year_ug',
            'joining_year_pg', 'specialty', 'country', 'state', 'city',
            'current_work_association', 'current_designation', 'associated_hospital',
            'contact_number', 'alternate_contact', 'email'
        ]
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            # academic_association widget is defined above
            'joining_year_ug': forms.Select(attrs={'class': 'form-select'}),
            'joining_year_pg': forms.Select(attrs={'class': 'form-select'}),
            'specialty': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'current_work_association': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'current_designation': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'associated_hospital': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'alternate_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # year choices: 1950..current year
        current_year = datetime.datetime.now().year
        years = [('', 'Select Year')] + [(y, y) for y in range(1950, current_year + 1)]
        self.fields['joining_year_ug'].choices = years
        self.fields['joining_year_pg'].choices = years

        # Start with UG required; we'll enforce proper required-ness in clean()
        self.fields['joining_year_ug'].required = False
        self.fields['joining_year_pg'].required = False

    def clean(self):
        cleaned = super().clean()
        assoc = cleaned.get('academic_association')
        ug = cleaned.get('joining_year_ug')
        pg = cleaned.get('joining_year_pg')

        if assoc == 'UG':
            if not ug:
                self.add_error('joining_year_ug', 'UG year is required.')
            cleaned['joining_year_pg'] = None  # drop PG
        elif assoc == 'PG':
            if not pg:
                self.add_error('joining_year_pg', 'PG year is required.')
            cleaned['joining_year_ug'] = None  # UG can be blank
        elif assoc == 'UG_PG':
            if not ug:
                self.add_error('joining_year_ug', 'UG year is required.')
            if not pg:
                self.add_error('joining_year_pg', 'PG year is required.')
        return cleaned

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Username','required': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control','placeholder': 'Password','required': True})
    )

class AlumniFilterForm(forms.Form):
    name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Search by name'}))
    joining_year = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control','placeholder': 'Joining Year'}))
    work_association = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Work Association'}))
    specialization = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Specialization'}))
    location = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Location'}))
    designation = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Designation'}))
