# models.py

from django.db import models
from django.contrib.auth.models import User
# from django.core.validators import RegexValidator  <-- अब इसकी जरूरत नहीं

# New: canonical choices used by forms & admin
ACADEMIC_ASSOC_CHOICES = [
    ('UG', 'UG'),
    ('PG', 'PG'),
    ('UG_PG', 'UG and PG'),
]

class Alumni(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    # Personal Information
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    photo = models.ImageField(upload_to='alumni_photos/', null=True, blank=True)
    
    # बदला हुआ: अब खाली नाम और किसी भी तरह का ईमेल सेव हो जाएगा
    name = models.CharField(max_length=200, null=True, blank=True)
    email = models.CharField(max_length=254, null=True, blank=True) # EmailField से CharField में बदला

    # Academic Information
    # बदला हुआ: अब कोई भी टेक्स्ट सेव होगा, सिर्फ UG/PG नहीं
    academic_association = models.CharField(max_length=100, null=True, blank=True)
    
    # बदला हुआ: अब साल की जगह कोई भी टेक्स्ट (जैसे "N/A") सेव हो जाएगा
    joining_year_ug = models.CharField(max_length=50, null=True, blank=True)
    joining_year_pg = models.CharField(max_length=50, null=True, blank=True)
    
    specialty = models.CharField(max_length=200, null=True, blank=True)

    # Location (अब ये खाली हो सकते हैं)
    country = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)

    # Professional Information (अब ये खाली हो सकते हैं)
    current_work_association = models.CharField(max_length=200, null=True, blank=True)
    current_designation = models.CharField(max_length=200, null=True, blank=True)
    associated_hospital = models.CharField(max_length=200, null=True, blank=True)

    # Contact Information (बदला हुआ: फ़ोन नंबर का कोई भी फॉर्मेट चलेगा)
    contact_number = models.CharField(max_length=50, null=True, blank=True)
    alternate_contact = models.CharField(max_length=50, null=True, blank=True)

    # Registration Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Alumni"
        ordering = ['-created_at']

    def __str__(self):
        # अगर नाम खाली है तो एरर से बचने के लिए
        return self.name if self.name else f"Alumni ID: {self.id}"

# ... (बाकी मॉडल वैसे ही रहेंगे) ...
