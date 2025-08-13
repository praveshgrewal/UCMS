# models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

# यह आपका प्रोडक्शन-रेडी, सख्त मॉडल है, जिसमें सिर्फ एक सुधार है।

class Alumni(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # Personal Information
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    photo = models.ImageField(upload_to='alumni_photos/', null=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True) # ईमेल यूनिक होना चाहिए
    
    # --- समाधान यहाँ है ---
    # Academic Information
    # academic_association की लंबाई बढ़ा दी गई है ताकि लंबा टेक्स्ट सेव हो सके
    academic_association = models.CharField(max_length=100) 
    
    joining_year_ug = models.IntegerField(null=True, blank=True)
    joining_year_pg = models.IntegerField(null=True, blank=True)
    specialty = models.CharField(max_length=200)
    
    # Location
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    
    # Professional Information
    current_work_association = models.CharField(max_length=200)
    current_designation = models.CharField(max_length=200)
    associated_hospital = models.CharField(max_length=200)
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    contact_number = models.CharField(validators=[phone_regex], max_length=17, unique=True) # कॉन्टैक्ट नंबर यूनिक होना चाहिए
    alternate_contact = models.CharField(validators=[phone_regex], max_length=17, null=True, blank=True)
    
    # Registration Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Alumni"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

# ... (बाकी मॉडल वैसे ही रहेंगे) ...
