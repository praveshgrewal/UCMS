from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.conf import settings
from django.db import IntegrityError

import json
from .models import Alumni, AdminUser, OTPVerification
from .forms import (
    AlumniLoginForm, OTPVerificationForm, AlumniRegistrationForm,
    AdminLoginForm, AlumniFilterForm
)
from .utils import send_sms_otp, send_email_otp, verify_otp, check_existing_alumni
from django.utils import timezone
import logging

from django.urls import reverse

logger = logging.getLogger(__name__)

# keep these helpers at top of alumni/views.py
def is_admin(user):
    return user.is_superuser or user.is_staff or AdminUser.objects.filter(user=user).exists()

def is_super_admin(user):
    return user.is_superuser or AdminUser.objects.filter(user=user, is_super_admin=True).exists()

def login_view(request):
    if request.method == 'POST':
        form = AlumniLoginForm(request.POST)
        if form.is_valid():
            contact = form.cleaned_data['contact']
            existing_alumni = check_existing_alumni(contact)
            if existing_alumni:
                if '@' in contact:
                    send_email_otp(contact)
                else:
                    send_sms_otp(contact)
                request.session['login_contact'] = contact
                request.session['alumni_id'] = existing_alumni.id
                return redirect('alumni:verify_otp')
            else:
                messages.error(request, 'Alumni not found. Please register first.')
                return redirect('alumni:register')
    else:
        form = AlumniLoginForm()
    return render(request, 'alumni/login.html', {'form': form})

def verify_otp_view(request):
    """
    Login OTP verification (separate from registration).
    Avoids OneToOne clashes by not re-linking a User already owned by another Alumni.
    Always passes an auth backend to login() so the session persists.
    """
    contact = request.session.get('login_contact')
    if not contact:
        messages.error(request, 'Your session expired. Please log in again.')
        return redirect('alumni:login')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Please enter the 6-digit OTP.')
            return render(request, 'alumni/verify_otp.html', {'form': form, 'contact': contact})

        otp = (form.cleaned_data.get('otp') or '').strip()

        try:
            # 1) Check OTP
            if not verify_otp(contact, otp):
                messages.error(request, 'Invalid or expired OTP. Please try again.')
                return render(request, 'alumni/verify_otp.html', {'form': form, 'contact': contact})

            # 2) Resolve the Alumni row
            alumni = None
            alumni_id = request.session.get('alumni_id')
            if alumni_id:
                alumni = Alumni.objects.filter(id=alumni_id).first()

            if alumni is None:
                qs = Alumni.objects.filter(Q(email__iexact=contact) | Q(contact_number=contact))
                # Prefer a row already linked to a user (avoids re-link attempts)
                alumni = qs.filter(user__isnull=False).order_by('-created_at').first() or qs.order_by('-created_at').first()

            if alumni is None:
                messages.error(request, 'We could not find your profile. Please register first.')
                return redirect('alumni:register')

            # 3) Pick or create the User
            user = alumni.user
            if not user:
                # If another alumni with same contact is already linked, reuse that user
                conflict_alumni = Alumni.objects.filter(
                    user__isnull=False
                ).filter(
                    Q(email__iexact=contact) | Q(contact_number=contact)
                ).exclude(pk=alumni.pk).first()
                if conflict_alumni:
                    user = conflict_alumni.user

            if not user:
                # Try by likely usernames
                user = User.objects.filter(username=contact).first()
                if not user and alumni.email:
                    user = User.objects.filter(username=alumni.email).first()
                if not user and alumni.contact_number:
                    user = User.objects.filter(username=alumni.contact_number).first()

            if not user:
                # Create new user
                base_username = contact or alumni.email or alumni.contact_number or (alumni.name or "user").replace(" ", "").lower()
                username = base_username
                i = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{i}"
                    i += 1

                user = User(
                    username=username,
                    email=(contact if "@" in contact else (alumni.email or "")),
                    first_name=(alumni.name.split()[0] if alumni.name else "")
                )
                user.set_unusable_password()
                user.save()

            # 4) Link Alumni → User only if no other Alumni owns this user
            try:
                if alumni.user_id != user.id:
                    if Alumni.objects.filter(user=user).exclude(pk=alumni.pk).exists():
                        # Someone else already owns this user; don't relink.
                        logger.warning("User %s already linked to another Alumni. Skipping relink.", user.id)
                    else:
                        alumni.user = user
                        alumni.save(update_fields=['user'])
            except IntegrityError:
                # Safety: if the race condition still happens, skip relink and continue.
                logger.warning("IntegrityError linking user %s to alumni %s; proceeding with login.", user.id, alumni.id)

            # 5) Login with explicit backend so the session sticks
            backend = settings.AUTHENTICATION_BACKENDS[0]  # e.g. 'django.contrib.auth.backends.ModelBackend'
            login(request, user, backend=backend)

            # Optional: align session alumni_id with the actually-linked row
            linked_row = Alumni.objects.filter(user=user).first()
            if linked_row:
                request.session['alumni_id'] = linked_row.id

            # 6) Clean session + redirect
            request.session.pop('login_contact', None)
            logger.info("OTP login OK for alumni_id=%s user_id=%s", (linked_row or alumni).id, user.id)
            return redirect('alumni:directory')

        except Exception:
            logger.exception("[verify_otp_view] unexpected error during OTP login")
            messages.error(request, 'Something went wrong while verifying your OTP. Please try again.')
            return render(request, 'alumni/verify_otp.html', {'form': form, 'contact': contact})

    # GET → show form
    form = OTPVerificationForm()
    return render(request, 'alumni/verify_otp.html', {'form': form, 'contact': contact})

@login_required
def directory_view(request):
    alumni_list = Alumni.objects.filter(status='approved').order_by('name')
    return render(request, 'alumni/directory.html', {'alumni_list': alumni_list})
    
# (Other views such as profile_view, admin panel views, etc. remain unchanged)





def register_view(request):
    """
    POST: validate/save and send OTPs.
         - If an APPROVED profile with same email/phone exists, create a NEW pending row
           from the submitted data so admins can review it.
         - Otherwise create/update a pending/rejected row as before.
    GET : render the form.
    Always return JSON for POST so the frontend can parse it.
    """
    if request.method != 'POST':
        form = AlumniRegistrationForm()
        return render(request, 'alumni/register.html', {'form': form})

    try:
        email = (request.POST.get('email') or '').strip()
        phone = (request.POST.get('contact_number') or '').strip()

        existing = None
        if email or phone:
            existing = (
                Alumni.objects
                .filter(Q(email__iexact=email) | Q(contact_number=phone))
                .order_by('-created_at')
                .first()
            )

        # ---------- CASE A: An APPROVED profile exists for this email/phone ----------
        # Create a NEW pending record from submitted data so it appears in admin review.
        if existing and existing.status == 'approved':
            form = AlumniRegistrationForm(request.POST, request.FILES)
            if not form.is_valid():
                logger.info("[register_view] form invalid (approved duplicate): %s", dict(form.errors.items()))
                return JsonResponse({'success': False, 'errors': dict(form.errors.items())}, status=200)

            new_alumni = form.save(commit=False)
            new_alumni.status = 'pending'
            new_alumni.is_verified = False
            new_alumni.save()
            logger.info("[register_view] created NEW pending (dup) id=%s email=%s phone=%s",
                        new_alumni.id, new_alumni.email, new_alumni.contact_number)

            sms_ok = False
            email_ok = False
            try:
                if new_alumni.contact_number:
                    send_sms_otp(new_alumni.contact_number)
                    sms_ok = True
            except Exception:
                logger.exception("[register_view] SMS error (approved duplicate new row)")

            try:
                if new_alumni.email:
                    send_email_otp(new_alumni.email)
                    email_ok = True
            except Exception:
                logger.exception("[register_view] Email error (approved duplicate new row)")

            request.session['pending_registration_id'] = new_alumni.id

            return JsonResponse({
                'success': True,
                'message': 'OTP sent. Proceed to verification.',
                'contact_number': new_alumni.contact_number or '',
                'email': new_alumni.email or '',
                'sms_sent': sms_ok,
                'email_sent': email_ok,
                'pending_id': new_alumni.id,   # <- helps you confirm in UI/logs
            }, status=200)

        # ---------- CASE B: New / Pending / Rejected ----------
        # If there's a pending/rejected record, update it; otherwise create new.
        instance = existing if (existing and existing.status in ['pending', 'rejected']) else None
        form = AlumniRegistrationForm(request.POST, request.FILES, instance=instance)

        if not form.is_valid():
            logger.info("[register_view] form invalid: %s", dict(form.errors.items()))
            return JsonResponse({'success': False, 'errors': dict(form.errors.items())}, status=200)

        alumni = form.save(commit=False)
        alumni.status = 'pending'
        alumni.is_verified = False
        alumni.save()
        logger.info("[register_view] saved pending alumni id=%s email=%s phone=%s",
                    alumni.id, alumni.email, alumni.contact_number)

        sms_ok = False
        email_ok = False

        try:
            if alumni.contact_number:
                send_sms_otp(alumni.contact_number)
                sms_ok = True
        except Exception:
            logger.exception("[register_view] SMS error")

        try:
            if alumni.email:
                send_email_otp(alumni.email)
                email_ok = True
        except Exception:
            logger.exception("[register_view] Email error")

        request.session['pending_registration_id'] = alumni.id

        return JsonResponse({
            'success': True,
            'message': 'OTP sent. Proceed to verification.',
            'contact_number': alumni.contact_number or '',
            'email': alumni.email or '',
            'sms_sent': sms_ok,
            'email_sent': email_ok,
            'pending_id': alumni.id,     # <- helps you confirm in UI/logs
        }, status=200)

    except Exception:
        logger.exception("[register_view] unexpected error")
        # Return JSON so the frontend won’t crash on res.json()
        return JsonResponse({'success': False, 'message': 'server_error'}, status=500)







@csrf_exempt
def resend_otp_view(request):
    """
    JSON endpoint to resend phone/email OTP during Step 2.
    Body: {"contact":"...", "type":"phone"|"email"}
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON.'}, status=400)

    contact = (data.get('contact') or '').strip()
    otp_type = (data.get('type') or '').strip().lower()

    if not contact or otp_type not in {'phone', 'email'}:
        return JsonResponse({'success': False, 'message': 'Invalid request data.'}, status=400)

    try:
        if otp_type == 'phone':
            print(f"resend_otp_view: resending SMS OTP to {contact}")
            send_sms_otp(contact)
        else:
            print(f"resend_otp_view: resending Email OTP to {contact}")
            send_email_otp(contact)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error resending OTP: {e}'}, status=500)

    return JsonResponse({'success': True, 'message': f'{otp_type.capitalize()} OTP resent successfully.'})



# In your views.py, replace the verify_registration_otp_view with this:

def verify_registration_otp_view(request):
    def _is_ajax(req):
        return req.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in req.headers.get('Accept','')

    if request.method != 'POST':
        # If someone GETs this URL, just go back to register
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
        return redirect('alumni:register')

    phone_otp = (request.POST.get('phoneOtp') or '').strip()
    email_otp = (request.POST.get('emailOtp') or '').strip()
    reg_id = request.session.get('pending_registration_id')

    try:
        alumni = Alumni.objects.get(id=reg_id)
    except Alumni.DoesNotExist:
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': 'Session expired. Please register again.'}, status=400)
        messages.error(request, "Session expired. Please register again.")
        return redirect('alumni:register')

    require_phone = bool(alumni.contact_number)
    require_email = bool(alumni.email)

    phone_valid = not require_phone
    email_valid = not require_email

    from django.utils import timezone
    if require_phone:
        try:
            OTPVerification.objects.get(
                contact=alumni.contact_number,
                otp=phone_otp,
                expires_at__gt=timezone.now(),
                is_verified=False,
            )
            phone_valid = True
        except OTPVerification.DoesNotExist:
            phone_valid = False

    if require_email:
        try:
            OTPVerification.objects.get(
                contact=alumni.email,
                otp=email_otp,
                expires_at__gt=timezone.now(),
                is_verified=False,
            )
            email_valid = True
        except OTPVerification.DoesNotExist:
            email_valid = False

    if phone_valid and email_valid:
        # Mark OTPs as used
        if require_phone and phone_otp:
            OTPVerification.objects.filter(
                contact=alumni.contact_number, otp=phone_otp
            ).update(is_verified=True)
        if require_email and email_otp:
            OTPVerification.objects.filter(
                contact=alumni.email, otp=email_otp
            ).update(is_verified=True)

        alumni.is_verified = True
        alumni.save(update_fields=['is_verified'])

        # --- AJAX path: stay on register.html and show Step 3
        if _is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Verification complete.'})

        # --- Non-AJAX fallback (old behavior)
        messages.success(
            request,
            "The information provided will be verified within 72 hours, you can come back later to Log-In."
        )
        return redirect('alumni:login')

    # Invalid/expired OTP(s)
    if _is_ajax(request):
        return JsonResponse({'success': False, 'message': 'Invalid or expired OTP(s).'}, status=400)

    messages.error(request, "Invalid or expired OTP(s). Please try again.")
    return render(request, 'alumni/register.html', {
        'form': AlumniRegistrationForm(instance=alumni),
        'step': 2,
        'contact': alumni.contact_number,
        'email': alumni.email
    })


@login_required
def profile_view(request):
    """
    Show *my* profile. If the current User isn't linked to an Alumni yet,
    try to find a matching Alumni by username/email/phone and link it.
    """
    try:
        alumni = Alumni.objects.get(user=request.user)
        return render(request, 'alumni/profile.html', {'alumni': alumni})
    except Alumni.DoesNotExist:
        # Try to find & (safely) link a matching alumni record
        guesses = Alumni.objects.filter(
            Q(email__iexact=request.user.email) |
            Q(email__iexact=request.user.username) |
            Q(contact_number=request.user.username)
        ).order_by('-created_at')

        match = guesses.first()
        if match:
            try:
                # Only link if no other Alumni owns this user
                if not Alumni.objects.filter(user=request.user).exclude(pk=match.pk).exists():
                    match.user = request.user
                    match.save(update_fields=['user'])
            except IntegrityError:
                pass
            return render(request, 'alumni/profile.html', {'alumni': match})

        messages.error(request, 'Profile not found')
        return redirect('alumni:directory')


@login_required
def profile_view(request):
    """View alumni profile"""
    try:
        alumni = Alumni.objects.get(user=request.user)
        return render(request, 'alumni/profile.html', {'alumni': alumni})
    except Alumni.DoesNotExist:
        messages.error(request, 'Profile not found')
        return redirect('alumni:directory')

@login_required
def edit_profile_view(request):
    """Edit alumni profile"""
    try:
        alumni = Alumni.objects.get(user=request.user)
    except Alumni.DoesNotExist:
        messages.error(request, 'Profile not found')
        return redirect('alumni:directory')
    
    if request.method == 'POST':
        form = AlumniRegistrationForm(request.POST, request.FILES, instance=alumni)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('alumni:profile')
    else:
        form = AlumniRegistrationForm(instance=alumni)
    
    return render(request, 'alumni/edit_profile.html', {
        'form': form,
        'alumni': alumni
    })

def admin_login_view(request):
    """Custom admin login view for staff or superusers"""
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user and user.is_active and user.is_staff:
                login(request, user)
                return redirect('alumni:admin_panel')  # or any dashboard
            else:
                messages.error(request, 'Invalid admin credentials')
    else:
        form = AdminLoginForm()
    
    return render(request, 'alumni/admin_login.html', {'form': form})


@login_required
def admin_panel_view(request):
    """
    Show only the LATEST pending request per (email, phone),
    so duplicate cards don’t appear.
    """
    if not is_admin(request.user):
        messages.error(request, 'Access denied')
        return redirect('alumni:login')

    pending_qs = Alumni.objects.filter(status='pending').order_by('-created_at', '-id')

    seen = set()
    unique_pending = []
    for a in pending_qs:
        key = ((a.email or '').strip().lower(), (a.contact_number or '').strip())
        if key not in seen:
            seen.add(key)
            unique_pending.append(a)

    approved_alumni = Alumni.objects.filter(status='approved').order_by('-created_at')

    return render(request, 'alumni/admin_panel.html', {
        'pending_requests': unique_pending,
        'approved_alumni': approved_alumni,
        'can_take_actions': is_admin(request.user),  # admins can act (see admin_action_view)
    })



@login_required
def admin_review_view(request, alumni_id):
    if not is_admin(request.user):
        messages.error(request, 'Access denied')
        return redirect('alumni:login')
    alumni = get_object_or_404(Alumni, id=alumni_id)
    return render(request, 'alumni/admin_review.html', {
        'alumni': alumni,
        'can_take_actions': is_admin(request.user),
    })



@login_required
def admin_action_view(request, alumni_id, action):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('alumni:admin_panel')

    if not is_admin(request.user):
        messages.error(request, 'Access denied')
        return redirect('alumni:admin_panel')

    alumni = get_object_or_404(Alumni, id=alumni_id)

    if action == 'approve':
        alumni.status = 'approved'
        alumni.is_verified = True
        alumni.save()
        messages.success(request, f'Alumni {alumni.name} approved successfully')

    elif action == 'reject':
        alumni.status = 'rejected'
        alumni.save()
        messages.success(request, f'Alumni {alumni.name} rejected')

    elif action == 'delete':
        alumni.delete()
        messages.success(request, 'Alumni record deleted')

    else:
        messages.error(request, 'Invalid action')

    return redirect('alumni:admin_panel')


@login_required
def admin_search_view(request):
    """
    Handles the live search AJAX request from the admin dashboard
    and returns a JSON response.
    """
    # Start with all approved alumni
    alumni_queryset = Alumni.objects.filter(status='approved')

    # Get search parameters from the request
    name = request.GET.get('name', '')
    joining_year = request.GET.get('joining_year', '')
    work_association = request.GET.get('work_association', '')
    specialization = request.GET.get('specialization', '')
    location = request.GET.get('location', '')
    designation = request.GET.get('designation', '')

    # Apply filters if parameters are provided
    if name:
        alumni_queryset = alumni_queryset.filter(name__icontains=name)
    
    if joining_year:
        # Check both UG and PG joining years
        alumni_queryset = alumni_queryset.filter(
            Q(joining_year_ug=joining_year) | Q(joining_year_pg=joining_year)
        )
        
    if work_association:
        alumni_queryset = alumni_queryset.filter(current_work_association__icontains=work_association)
        
    if specialization:
        alumni_queryset = alumni_queryset.filter(specialty__icontains=specialization)
        
    if location:
        # Search across city, state, and country
        alumni_queryset = alumni_queryset.filter(
            Q(city__icontains=location) | Q(state__icontains=location) | Q(country__icontains=location)
        )
        
    if designation:
        alumni_queryset = alumni_queryset.filter(current_designation__icontains=designation)

    # Prepare the data for JSON response
    # This format matches what your JavaScript expects
    alumni_data = []
    for alumni in alumni_queryset:
        alumni_data.append({
            'id': alumni.id,
            'name': alumni.name,
            'photo_url': alumni.safe_photo_url,  # CHANGED
            'academic_association': alumni.academic_association,
            'joining_year_ug': alumni.joining_year_ug,
            'joining_year_pg': alumni.joining_year_pg,
            'specialty': alumni.specialty or 'N/A',
            'city': alumni.city,
            'country': alumni.country,
            'current_designation': alumni.current_designation or 'N/A',
            'current_work_association': alumni.current_work_association or 'N/A',
        })

    return JsonResponse({'alumni': alumni_data})




@login_required
def alumni_detail_page_view(request, alumni_id):
    """
    Renders a full, dedicated page for a single alumni profile.
    """
    alumnus = get_object_or_404(Alumni.objects.select_related('user'), id=alumni_id, status='approved')
    
    context = {
        'alumnus': alumnus
    }
    return render(request, 'alumni/alumni_detail_page.html', context)
    
@login_required
def get_alumni_details_view(request, alumni_id):
    """
    Fetch alumni details and return as JSON for the directory modal view.
    """
    alumnus = get_object_or_404(Alumni.objects.select_related('user'), id=alumni_id)
    
    data = {
        'id': alumnus.id,
        'name': alumnus.name,
        'photo_url': alumnus.safe_photo_url,  # CHANGED
        'joining_year_ug': alumnus.joining_year_ug,
        'joining_year_pg': alumnus.joining_year_pg if alumnus.joining_year_pg else 'N/A',
        'academic_association': alumnus.academic_association,
        'specialty': alumnus.specialty or 'N/A',
        'current_designation': alumnus.current_designation or 'N/A',
        'current_work_association': alumnus.current_work_association or 'N/A',
        'city': alumnus.city,
        'country': alumnus.country,
        'email': alumnus.email,
        'contact_number': alumnus.contact_number,
        'about': getattr(alumnus, 'about_me', 'No biography provided.'),
        'linkedin_url': getattr(alumnus, 'linkedin_url', ''),
        'twitter_url': getattr(alumnus, 'twitter_url', ''),
    }
    return JsonResponse(data)











@login_required
def admin_edit_alumni_view(request, alumni_id):
    if not is_admin(request.user):
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('alumni:admin_panel')

    alumnus = get_object_or_404(Alumni, id=alumni_id)

    if request.method == 'POST':
        form = AlumniRegistrationForm(request.POST, request.FILES, instance=alumnus)
        if form.is_valid():
            form.save()
            messages.success(request, f"Profile for {alumnus.name} has been updated successfully.")
            return redirect('alumni:admin_panel')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AlumniRegistrationForm(instance=alumnus)

    return render(request, 'alumni/admin_edit_alumni.html', {'form': form, 'alumnus': alumnus})



def logout_view(request):
    """Logout user"""
    logout(request)
    return redirect('alumni:login')

def admin_logout_view(request):
    """Logout admin"""
    logout(request)
    return redirect('alumni:admin_login')
