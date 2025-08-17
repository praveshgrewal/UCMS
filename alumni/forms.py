# alumni/forms.py
from django import forms
from .models import Alumni
import datetime


# Yeh form waise ka waisa hi hai
class AlumniLoginForm(forms.Form):
    contact = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone / Email',
            'required': True
        })
    )


# Yeh form waise ka waisa hi hai
class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter OTP',
            'required': True,
            'maxlength': '6'
        })
    )


# ############# START: SIRF IS FORM MEIN BADLAV KIYA GAYA HAI #############
class AlumniRegistrationForm(forms.ModelForm):
    ACADEMIC_CHOICES = [
        ('', 'Select Association'),
        ('UG', 'UG'),
        ('PG', 'PG'),
        ('UG_PG', 'UG and PG'),
    ]

    academic_association = forms.ChoiceField(
        choices=ACADEMIC_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # TypedChoiceField so values become int (or None) cleanly
    joining_year_ug = forms.TypedChoiceField(
        choices=[],                # set in __init__
        required=False,
        coerce=lambda v: int(v),   # '' won't reach coerce (handled by empty_value)
        empty_value=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    joining_year_pg = forms.TypedChoiceField(
        choices=[],                # set in __init__
        required=False,
        coerce=lambda v: int(v),
        empty_value=None,
        widget=forms.Select(attrs={'class': 'form-select'})
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
            'contact_number', 'alternate_contact', 'email', 'declaration'
        ]
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'specialty': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'current_work_association': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'current_designation': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'associated_hospital': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            # NOTE: required=False will be enforced in __init__ + clean()
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'alternate_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_year = datetime.date.today().year
        years = [(str(y), str(y)) for y in range(current_year, 1950 - 1, -1)]
        year_choices = [('', 'Select Year')] + years

        self.fields['joining_year_ug'].choices = year_choices
        self.fields['joining_year_pg'].choices = year_choices

        # At least one of email/phone is needed, not both required
        self.fields['email'].required = False
        self.fields['contact_number'].required = False

        # Also ensure browser 'required' attr isn't forcing both:
        self.fields['email'].widget.attrs.pop('required', None)
        self.fields['contact_number'].widget.attrs.pop('required', None)

    def clean(self):
        cleaned_data = super().clean()
        assoc = (cleaned_data.get('academic_association') or '').upper().strip()

        ug_year = cleaned_data.get('joining_year_ug')  # int or None (TypedChoiceField)
        pg_year = cleaned_data.get('joining_year_pg')  # int or None

        email = (cleaned_data.get('email') or '').strip()
        phone = (cleaned_data.get('contact_number') or '').strip()

        # Require at least one contact path
        if not email and not phone:
            self.add_error('email', 'Provide email or phone.')
            self.add_error('contact_number', 'Provide email or phone.')

        # Conditional requirements for years
        if assoc == 'UG':
            if not ug_year:
                self.add_error('joining_year_ug', 'Please select the joining year for UG.')
            cleaned_data['joining_year_pg'] = None  # irrelevant
        elif assoc == 'PG':
            if not pg_year:
                self.add_error('joining_year_pg', 'Please select the joining year for PG.')
            cleaned_data['joining_year_ug'] = None
        elif assoc == 'UG_PG':
            if not ug_year:
                self.add_error('joining_year_ug', 'Please select the joining year for UG.')
            if not pg_year:
                self.add_error('joining_year_pg', 'Please select the joining year for PG.')
        else:
            # No valid association selected
            self.add_error('academic_association', 'Please select your academic association.')

        # Sanity check ranges if present
        for field in ('joining_year_ug', 'joining_year_pg'):
            val = cleaned_data.get(field)
            if val is not None:
                try:
                    yr = int(val)
                    if yr < 1950 or yr > 2100:
                        self.add_error(field, 'Please enter a valid year.')
                except (TypeError, ValueError):
                    self.add_error(field, 'Please enter a valid year.')

        # Declaration already required=True; no change needed
        return cleaned_data
# ############# END: BADLAV YAHAN KHATAM HUA #############


# Yeh form waise ka waisa hi hai
class AdminLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'required': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'required': True
        })
    )


# Yeh form waise ka waisa hi hai
class AlumniFilterForm(forms.Form):
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name'})
    )
    joining_year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Joining Year'})
    )
    work_association = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Work Association'})
    )
    specialization = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specialization'})
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'})
    )
    designation = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Designation'})
    )
