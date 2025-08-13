import random
import string
import pandas as pd
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.conf import settings
from .models import OTPVerification, Alumni  # Alumni को यहाँ इम्पोर्ट करें
import os
import requests
import mailtrap as mt


# -------------------------------
# OTP Functions (No changes needed here)
# -------------------------------
def generate_otp():
    """Generate a 6-digit numeric OTP."""
    return ''.join(random.choices(string.digits, k=6))

def send_sms_otp(contact):
    """Send OTP via SMS and save it in DB."""
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=getattr(settings, "OTP_EXPIRY_MINUTES", 5))
    OTPVerification.objects.filter(contact=contact).delete()
    OTPVerification.objects.create(contact=contact, otp=otp, expires_at=expires_at, is_verified=False)
    
    api_key = settings.TWO_FACTOR_API_KEY
    phone = f"+91{contact}" if not contact.startswith("+91") else contact
    url = f"https://2factor.in/API/V1/{api_key}/SMS/{phone}/{otp}"
    try:
        res = requests.get(url, timeout=5)
        print("SMS OTP Response:", res.json())
    except Exception as e:
        print("SMS OTP Error:", e)
    return otp

def send_email_otp(email):
    """Send OTP via email using Mailtrap and save it in DB."""
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=getattr(settings, "OTP_EXPIRY_MINUTES", 5))
    OTPVerification.objects.filter(contact=email).delete()
    OTPVerification.objects.create(contact=email, otp=otp, expires_at=expires_at, is_verified=False)
    
    otp_html = f"""
    <!DOCTYPE html>
    <html>
    <body>
      <div style="font-family: sans-serif; max-width: 480px; margin: 30px auto; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);">
        <h2 style="text-align: center; color: #2c3e50;">UCMS Alumni Portal OTP</h2>
        <p style="font-size: 32px; font-weight: bold; color: #e74c3c; text-align: center; margin: 20px 0;">{otp}</p>
        <p style="text-align: center; color: #7f8c8d;">This OTP is valid for 5 minutes.</p>
      </div>
    </body>
    </html>
    """
    
    client = mt.MailtrapClient(token=settings.MAILTRAP_API_KEY)
    mail = mt.Mail(
        sender=mt.Address(email=getattr(settings, "DEFAULT_FROM_EMAIL", "hello@demomailtrap.co"), name="UCMS Alumni Portal"),
        to=[mt.Address(email=email)],
        subject="Your OTP - UCMS Alumni Portal",
        text=f"Your OTP for UCMS Alumni Portal is {otp}.",
        html=otp_html,
        category="OTP Verification"
    )
    try:
        response = client.send(mail)
        print("✅ Email OTP sent successfully:", response)
    except Exception as e:
        print("❌ Error sending Email OTP:", e)
    return otp

def verify_otp(contact, otp):
    """Verify OTP from local database."""
    try:
        otp_record = OTPVerification.objects.get(contact=contact, otp=otp, is_verified=False)
        if otp_record.expires_at > timezone.now():
            otp_record.is_verified = True
            otp_record.save()
            return True
        return False
    except OTPVerification.DoesNotExist:
        return False

def check_existing_alumni(contact):
    """Check if alumni exists in database."""
    return Alumni.objects.filter(
        models.Q(email=contact) | models.Q(contact_number=contact),
        status='approved'
    ).first()


# -------------------------------
# IMPORT ALUMNI FROM EXCEL (UPDATED AND ROBUST)
# -------------------------------
def import_alumni_from_excel():
    """
    Excel फ़ाइल से सभी एलुमनाई डेटा को इम्पोर्ट करता है।
    यह फंक्शन गलत या खाली डेटा को संभालने के लिए डिज़ाइन किया गया है ताकि कोई एरर न आए।
    """
    try:
        excel_path = os.path.join(settings.BASE_DIR, 'attached_assets', 'alumni_list_1754148285179.xlsx')
        if not os.path.exists(excel_path):
            print(f"❌ Excel file not found at {excel_path}")
            return 0

        # Excel फ़ाइल को पढ़ते समय खाली सेल्स को 'nan' की जगह खाली स्ट्रिंग ('') मानें
        df = pd.read_excel(excel_path).fillna('')
        imported_count = 0

        for index, row in df.iterrows():
            try:
                # हर वैल्यू को सुरक्षित रूप से स्ट्रिंग में बदलें
                email = str(row.get('Email Address', '')).strip()
                contact_number = str(row.get('Your Contact Number (WhatsApp)', '')).strip()

                # अगर ईमेल और कॉन्टैक्ट नंबर दोनों खाली हैं, तो इस पंक्ति को छोड़ दें
                if not email and not contact_number:
                    print(f"⏩ Skipping row {index+2}: Both email and contact are empty.")
                    continue

                # अगर रिकॉर्ड पहले से मौजूद है, तो उसे भी छोड़ दें
                # नोट: अगर आप चाहें तो मौजूदा रिकॉर्ड को अपडेट भी कर सकते हैं
                if email and Alumni.objects.filter(email=email).exists():
                    print(f"⏩ Skipping row {index+2}: Email '{email}' already exists.")
                    continue
                if contact_number and Alumni.objects.filter(contact_number=contact_number).exists():
                    print(f"⏩ Skipping row {index+2}: Contact '{contact_number}' already exists.")
                    continue

                # सभी डेटा को एक डिक्शनरी में इकट्ठा करें, और सुनिश्चित करें कि सब स्ट्रिंग है
                alumni_data = {
                    'name': str(row.get('Your Name ', '')).strip(),
                    'email': email,
                    'contact_number': contact_number,
                    'alternate_contact': str(row.get('Your Contact Number (Alternate)', '')).strip(),
                    'academic_association': str(row.get('Please Specify Your Academic Association With UCMS ', '')).strip(),
                    'joining_year_ug': str(row.get('Joining Year (UG) ', '')).strip(),
                    'joining_year_pg': str(row.get('Joining Year (PG) (Select N/A if Not Applicable)', '')).strip(),
                    'specialty': str(row.get('Specialty', '')).strip(),
                    'country': str(row.get('Which Country Are You Currently Working In? ', '')).strip(),
                    'state': str(row.get('Which State/UT Are You Currently Working In (If in India)? \n(Select N/A if Outside India)', '')).strip(),
                    'city': str(row.get('Which City Are You Currently Working In? \n(If in India)', '')).strip(),
                    'current_designation': str(row.get('What is Your Current Designation?', '')).strip(),
                    'current_work_association': str(row.get('Please Specify Your Current Work Association', '')).strip(),
                    'associated_hospital': str(row.get('Name of the Associated Hospital/College/Institute\n(Please Mention Full Name)', '')).strip(),
                    'status': 'approved',
                    'is_verified': True
                }
                
                # डेटाबेस में नया एलुमनाई ऑब्जेक्ट बनाएं
                Alumni.objects.create(**alumni_data)
                imported_count += 1

            except Exception as e:
                # अगर किसी पंक्ति में कोई अप्रत्याशित एरर आती है, तो उसे प्रिंट करें और आगे बढ़ें
                print(f"❌ Error importing row {index + 2}: {e}")
                continue

        print(f"✅ Successfully imported {imported_count} new alumni from Excel.")
        return imported_count

    except Exception as e:
        print(f"❌ Critical Error reading Excel file: {e}")
        return 0

# ... (Helper functions get_countries, get_indian_states can remain as they are) ...
def get_countries():
    return [ 'India', 'United States', 'United Kingdom', 'Canada', 'Australia', 'Other' ]

def get_indian_states():
    return [ 'Delhi', 'Uttar Pradesh', 'Haryana', 'Maharashtra', 'Karnataka', 'Other' ]
