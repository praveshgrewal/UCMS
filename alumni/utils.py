import random
import string
import pandas as pd
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.conf import settings
from .models import OTPVerification
import os
import requests
import mailtrap as mt
import re

# -------------------------------
# NORMALIZERS (added)
# -------------------------------
def normalize_academic_association(raw: str) -> str:
    """
    Map verbose survey text to your allowed choices:
    'UG', 'PG', 'UG_PG' (fits max_length=10).
    """
    s = (raw or "").strip().upper().replace("&", "AND")
    if "BOTH" in s or "UG AND PG" in s:
        return "UG_PG"
    if "UG" in s and "PG" not in s:
        return "UG"
    if "PG" in s and "UG" not in s:
        return "PG"
    return "UG"  # safe default


def _truncate(s, n):
    """Trim strings to column max_length to avoid DB DataError."""
    s = (s or "").strip()
    return s if len(s) <= n else s[:n]


# -------------------------------
# OTP GENERATION
# -------------------------------
def generate_otp():
    """Generate a 6-digit numeric OTP."""
    return ''.join(random.choices(string.digits, k=6))


# -------------------------------
# INTERNAL: PHONE NORMALIZER (added)
# -------------------------------
def _normalize_msisdn(contact: str) -> str:
    """
    Normalize to Indian MSISDN for 2Factor: digits only.
    Returns 91XXXXXXXXXX (12 digits) when possible.
    """
    digits = re.sub(r"\D", "", str(contact or ""))
    if len(digits) == 10:
        return "91" + digits
    if digits.startswith("91") and len(digits) == 12:
        return digits
    # Fall back to digits as-is (provider may reject; we still log/send)
    return digits


# -------------------------------
# SEND SMS OTP  (UPDATED)
# -------------------------------
def send_sms_otp(contact):
    """Send OTP via SMS and save it in DB."""
    print(f"Attempting to send OTP to: {contact}")
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=getattr(settings, "OTP_EXPIRY_MINUTES", 5))

    # Keep only one live OTP per contact
    OTPVerification.objects.filter(contact=contact).delete()

    OTPVerification.objects.create(
        contact=contact,
        otp=otp,
        expires_at=expires_at,
        is_verified=False
    )

    print(f"Generated OTP: {otp}, Expiry Time: {expires_at}")

    # --- FIX: ensure digits-only MSISDN for 2Factor (no '+') ---
    phone = _normalize_msisdn(contact)
    print(f"Sending OTP to phone number (normalized): {phone}")

    api_key = settings.TWO_FACTOR_API_KEY

    # Optional: support DLT template if provided via settings.TWO_FACTOR_TEMPLATE
    template = getattr(settings, "TWO_FACTOR_TEMPLATE", "").strip()
    if template:
        url = f"https://2factor.in/API/V1/{api_key}/SMS/{phone}/{otp}/{template}"
    else:
        url = f"https://2factor.in/API/V1/{api_key}/SMS/{phone}/{otp}"

    try:
        res = requests.get(url, timeout=8)
        try:
            payload = res.json()
        except Exception:
            payload = {"raw": res.text}

        print("SMS OTP Response:", payload)

        # 2Factor typically returns {"Status": "Success", "Details": "..."}
        status_val = str(payload.get("Status") or payload.get("status") or "").lower()
        if res.status_code == 200 and status_val == "success":
            print(f"OTP sent successfully to {phone}")
        else:
            # Keep the OTP in DB (user can try email or resend); surface clear logs
            print(f"Failed to send OTP to {phone}, HTTP={res.status_code}, Status={status_val}, Payload={payload}")
    except Exception as e:
        print("SMS OTP Error:", e)

    return otp


# -------------------------------
# SEND EMAIL OTP  (MINOR SAFE GUARD)
# -------------------------------
def send_email_otp(email):
    """Send OTP via email using Mailtrap and save it in DB."""
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=getattr(settings, "OTP_EXPIRY_MINUTES", 5))

    # Remove old OTPs for this email
    OTPVerification.objects.filter(contact=email).delete()

    # Save OTP in DB
    OTPVerification.objects.create(
        contact=email,
        otp=otp,
        expires_at=expires_at,
        is_verified=False
    )

    # Log OTP being generated and saved
    print(f"Generated OTP for {email}: {otp}")

    # HTML email content
    otp_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background-color: #f4f4f4;
          margin: 0;
          padding: 0;
        }}
        .container {{
          background-color: #ffffff;
          max-width: 480px;
          margin: 30px auto;
          padding: 30px;
          border-radius: 10px;
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
        }}
        .title {{
          font-size: 20px;
          font-weight: 600;
          color: #2c3e50;
          text-align: center;
        }}
        .otp-code {{
          font-size: 32px;
          font-weight: bold;
          color: #e74c3c;
          text-align: center;
          margin: 20px 0;
        }}
        .note {{
          font-size: 14px;
          color: #7f8c8d;
          text-align: center;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="title">UCMS Alumni Portal OTP Verification</div>
        <p class="otp-code">{otp}</p>
        <p class="note">This OTP is valid for 5 minutes. Please do not share it with anyone.</p>
      </div>
    </body>
    </html>
    """

    # Prepare Mailtrap client and email
    client = mt.MailtrapClient(token=settings.MAILTRAP_API_KEY)

    sender_email = getattr(settings, "DEFAULT_FROM_EMAIL", "hello@demomailtrap.co")
    if sender_email.endswith("demomailtrap.co"):
        # Helpful warning so you know if you’re on Sandbox (captured, not delivered)
        print("⚠️  Mailtrap warning: DEFAULT_FROM_EMAIL looks like a sandbox sender "
              "(demomailtrap.co). Emails may be captured and not delivered in production.")

    mail = mt.Mail(
        sender=mt.Address(
            email=sender_email,
            name="UCMS Alumni Portal"
        ),
        to=[mt.Address(email=email)],
        subject="Your OTP - UCMS Alumni Portal",
        text=f"Your OTP for UCMS Alumni Portal is {otp}. It is valid for 5 minutes.",
        html=otp_html,
        category="OTP Verification"
    )

    try:
        response = client.send(mail)
        print("✅ Email OTP sent (Mailtrap API call executed):", response)
        try:
            print(f"Message ID(s): {response.get('message_ids')}")
        except Exception:
            pass
    except Exception as e:
        print("❌ Error sending Email OTP:", e)
        print(f"Error details: {e}")

    return otp


# -------------------------------
# VERIFY OTP (LOCAL DB)
# -------------------------------
def verify_otp(contact, otp):
    """Verify OTP from local database."""
    try:
        otp_record = OTPVerification.objects.get(
            contact=contact,
            otp=otp,
            is_verified=False
        )

        # Check if OTP is still valid
        if otp_record.expires_at > timezone.now():
            otp_record.is_verified = True
            otp_record.save()
            print(f"OTP verified for {contact}")
            return True
        else:
            print(f"OTP expired for {contact}")
            return False

    except OTPVerification.DoesNotExist:
        print(f"No valid OTP found for {contact}")
        return False


# -------------------------------
# CHECK IF ALUMNI EXISTS
# -------------------------------
def check_existing_alumni(contact):
    """Check if alumni exists in database."""
    from .models import Alumni

    return Alumni.objects.filter(
        models.Q(email=contact) | models.Q(contact_number=contact),
        status='approved'
    ).first()


# -------------------------------
# IMPORT ALUMNI FROM EXCEL
# -------------------------------
def import_alumni_from_excel():
    """Import alumni data from Excel file."""
    try:
        excel_path = os.path.join(settings.BASE_DIR, 'attached_assets', 'alumni_list_1754148285179.xlsx')
        if not os.path.exists(excel_path):
            print(f"Excel file not found at {excel_path}")
            return 0

        df = pd.read_excel(excel_path)
        from .models import Alumni
        imported_count = 0

        for index, row in df.iterrows():
            try:
                name = str(row.get('Your Name ', '')).strip()
                email = str(row.get('Email Address', '')).strip()
                contact_number = str(row.get('Your Contact Number (WhatsApp)', '')).strip()
                alternate_contact = str(row.get('Your Contact Number (Alternate)', '')).strip()

                if not name or (not email and not contact_number):
                    continue

                if email.lower() in ['nan', '']:
                    email = ''
                if contact_number.lower() in ['nan', '']:
                    contact_number = ''

                if not email and not contact_number:
                    continue

                # --- improved duplicate check: ignore blanks ---
                dup_q = models.Q()
                if email:
                    dup_q |= models.Q(email__iexact=email)
                if contact_number:
                    dup_q |= models.Q(contact_number=contact_number)
                if dup_q and Alumni.objects.filter(dup_q).exists():
                    continue

                # Build dict
                alumni_data = {
                    'name': name,
                    'email': email,
                    'contact_number': contact_number,
                    'alternate_contact': '' if alternate_contact.lower() == 'nan' else alternate_contact,
                    'academic_association': str(row.get('Please Specify Your Academic Association With UCMS ', '')).strip(),
                    'joining_year_ug': 2000,
                    'joining_year_pg': None,
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

                # --- normalize + trim to model limits BEFORE save (added) ---
                alumni_data['academic_association'] = normalize_academic_association(
                    alumni_data.get('academic_association', '')
                )
                alumni_data['specialty'] = _truncate(alumni_data.get('specialty'), 200)
                alumni_data['country'] = _truncate(alumni_data.get('country'), 100)
                alumni_data['state'] = _truncate(alumni_data.get('state'), 100)
                alumni_data['city'] = _truncate(alumni_data.get('city'), 100)
                alumni_data['current_designation'] = _truncate(alumni_data.get('current_designation'), 200)
                alumni_data['current_work_association'] = _truncate(alumni_data.get('current_work_association'), 200)
                alumni_data['associated_hospital'] = _truncate(alumni_data.get('associated_hospital'), 200)

                try:
                    jy_ug = str(row.get('Joining Year (UG) ', '')).strip()
                    jy_pg = str(row.get('Joining Year (PG) (Select N/A if Not Applicable)', '')).strip()

                    alumni_data['joining_year_ug'] = int(jy_ug) if jy_ug.isdigit() else 2000
                    alumni_data['joining_year_pg'] = int(jy_pg) if jy_pg.isdigit() else None
                except:
                    pass

                # --- create with a defensive retry (added) ---
                try:
                    Alumni.objects.create(**alumni_data)
                    imported_count += 1
                except Exception as e:
                    # retry: lower-case email and re-apply trims (paranoid)
                    alumni_data['email'] = alumni_data.get('email', '').lower()
                    alumni_data['specialty'] = _truncate(alumni_data.get('specialty'), 200)
                    alumni_data['country'] = _truncate(alumni_data.get('country'), 100)
                    alumni_data['state'] = _truncate(alumni_data.get('state'), 100)
                    alumni_data['city'] = _truncate(alumni_data.get('city'), 100)
                    alumni_data['current_designation'] = _truncate(alumni_data.get('current_designation'), 200)
                    alumni_data['current_work_association'] = _truncate(alumni_data.get('current_work_association'), 200)
                    alumni_data['associated_hospital'] = _truncate(alumni_data.get('associated_hospital'), 200)

                    try:
                        Alumni.objects.create(**alumni_data)
                        imported_count += 1
                    except Exception as e2:
                        print(f"Row {index} failed: {e2}")
                        continue

            except Exception as e:
                print(f"Error importing row {index}: {e}")
                continue

        print(f"Successfully imported {imported_count} alumni from Excel")
        return imported_count

    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return 0


# -------------------------------
# HELPER: COUNTRY & STATE LISTS
# -------------------------------
def get_countries():
    return [
        'Afghanistan', 'Albania', 'Algeria', 'Argentina', 'Australia', 'Austria',
        'Bangladesh', 'Belgium', 'Brazil', 'Canada', 'China', 'Denmark',
        'Egypt', 'France', 'Germany', 'India', 'Indonesia', 'Iran',
        'Italy', 'Japan', 'Malaysia', 'Netherlands', 'Pakistan', 'Russia',
        'Saudi Arabia', 'Singapore', 'South Africa', 'Spain', 'Switzerland',
        'Thailand', 'Turkey', 'United Kingdom', 'United States', 'Other'
    ]


def get_indian_states():
    return [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand',
        'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur',
        'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
        'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
        'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi', 'Other'
    ]
