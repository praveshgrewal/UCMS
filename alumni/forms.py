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

    # In fields ko alag se define karna sabse zaroori hai
    academic_association = forms.ChoiceField(
        choices=ACADEMIC_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    joining_year_ug = forms.ChoiceField(
        choices=[], # Choices __init__ mein set honge
        required=False, # Shuruaat mein optional, clean() mein check hoga
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    joining_year_pg = forms.ChoiceField(
        choices=[], # Choices __init__ mein set honge
        required=False, # Shuruaat mein optional, clean() mein check hoga
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
        # Widgets se joining_year fields hata diye gaye hain kyunki woh upar define ho chuke hain
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
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'alternate_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        current_year = datetime.date.today().year
        # Saal ki list (ulta order mein)
        years = [(str(y), str(y)) for y in range(current_year, 1949, -1)]
        year_choices = [('', 'Select Year')] + years

        # Dono fields ke liye choices set karein
        self.fields['joining_year_ug'].choices = year_choices
        self.fields['joining_year_pg'].choices = year_choices

    def clean(self):
        cleaned_data = super().clean()
        assoc = cleaned_data.get('academic_association')
        ug_year = cleaned_data.get('joining_year_ug')
        pg_year = cleaned_data.get('joining_year_pg')

        # ### START: YAHAN BADLAV KIYA GAYA HAI ###
        # Agar saal select nahi kiya gaya hai, to uski value None set kar dein
        if not ug_year:
            cleaned_data['joining_year_ug'] = None
        if not pg_year:
            cleaned_data['joining_year_pg'] = None
        # ### END: BADLAV YAHAN KHATAM HUA ###

        if assoc == 'UG' and not ug_year:
            self.add_error('joining_year_ug', 'Please select the joining year for UG.')
        
        if assoc == 'PG' and not pg_year:
            self.add_error('joining_year_pg', 'Please select the joining year for PG.')

        if assoc == 'UG_PG':
            if not ug_year:
                self.add_error('joining_year_ug', 'Please select the joining year for UG.')
            if not pg_year:
                self.add_error('joining_year_pg', 'Please select the joining year for PG.')

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
