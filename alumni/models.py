# models.py

from django.db import models
from django.contrib.auth.models import User

# यह मॉडल का सबसे लचीला संस्करण है। यह डेटा इम्पोर्ट या डिप्लॉयमेंट के दौरान कोई एरर नहीं देगा।

class Alumni(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    # Personal Information
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    photo = models.ImageField(upload_to='alumni_photos/', null=True, blank=True)
    
    # अब खाली नाम और किसी भी तरह का ईमेल सेव हो जाएगा
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)

    # Academic Information - कोई भी टेक्स्ट सेव होगा
    academic_association = models.CharField(max_length=255, null=True, blank=True)
    
    # साल की जगह कोई भी टेक्स्ट (जैसे "N/A" या "2014.0") सेव हो जाएगा
    joining_year_ug = models.CharField(max_length=100, null=True, blank=True)
    joining_year_pg = models.CharField(max_length=100, null=True, blank=True)
    
    specialty = models.CharField(max_length=255, null=True, blank=True)

    # Location - अब ये खाली हो सकते हैं
    country = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)

    # Professional Information - अब ये खाली हो सकते हैं
    current_work_association = models.CharField(max_length=255, null=True, blank=True)
    current_designation = models.CharField(max_length=255, null=True, blank=True)
    associated_hospital = models.CharField(max_length=255, null=True, blank=True)

    # Contact Information - फ़ोन नंबर का कोई भी फॉर्मेट चलेगा
    contact_number = models.CharField(max_length=100, null=True, blank=True)
    alternate_contact = models.CharField(max_length=100, null=True, blank=True)

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

# ... (बाकी मॉडल जैसे OTPVerification और AdminUser वैसे ही रहेंगे) ...
