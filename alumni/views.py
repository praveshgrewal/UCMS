from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json

from .models import Alumni, AdminUser, OTPVerification
from .forms import (
    AlumniLoginForm, OTPVerificationForm, AlumniRegistrationForm,
    AdminLoginForm, AlumniFilterForm
)
from .utils import send_sms_otp, send_email_otp, verify_otp, check_existing_alumni
from .views import is_admin, is_super_admin 

from django.utils import timezone

def is_admin(user):
    # staff OR listed in AdminUser table
    return user.is_superuser or user.is_staff or AdminUser.objects.filter(user=user).exists()

def is_super_admin(user):
    # true for Django superuser OR our custom super_admin flag
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

def send_otp_view(request):
    if request.method == 'POST':
        contact = request.POST.get('contact')
        if contact:
            if '@' in contact:
                send_email_otp(contact)
            else:
                send_sms_otp(contact)
            return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def verify_otp_view(request):
    """Verify OTP and login alumni"""
    contact = request.session.get('login_contact')
    if not contact:
        return redirect('alumni:login')
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            if verify_otp(contact, otp):
                alumni_id = request.session.get('alumni_id')
                alumni = get_object_or_404(Alumni, id=alumni_id)
                
                if not alumni.user:
                    user = User.objects.create_user(
                        username=contact,
                        email=alumni.email if '@' in contact else '',
                        first_name=alumni.name.split()[0] if alumni.name else ''
                    )
                    alumni.user = user
                    alumni.save()
                
                login(request, alumni.user)
                request.session.pop('login_contact', None)
                request.session.pop('alumni_id', None)
                return redirect('alumni:directory')
            else:
                messages.error(request, 'Invalid or expired OTP')
    else:
        form = OTPVerificationForm()
    
    return render(request, 'alumni/verify_otp.html', {
        'form': form,
        'contact': contact
    })


def register_view(request):
    """
    Prevent duplicates: re-use an existing pending record for same email/phone.
    If already approved, block re-registration.
    """
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        phone = (request.POST.get('contact_number') or '').strip()

        existing = None
        if email or phone:
            existing = Alumni.objects.filter(
                Q(email__iexact=email) | Q(contact_number=phone)
            ).order_by('-created_at').first()

        if existing and existing.status == 'approved':
            return JsonResponse({
                'success': False,
                'errors': {'email': ['This email/phone is already registered. Please log in.']}
            }, status=400)

        form = AlumniRegistrationForm(
            request.POST, request.FILES,
            instance=existing if (existing and existing.status != 'approved') else None
        )

        if form.is_valid():
            alumni = form.save(commit=False)
            alumni.status = 'pending'
            alumni.save()

            if alumni.contact_number:
                send_sms_otp(alumni.contact_number)
            if alumni.email:
                send_email_otp(alumni.email)

            request.session['pending_registration_id'] = alumni.id
            return JsonResponse({
                'success': True,
                'message': 'OTP sent. Proceed to verification.',
                'contact_number': alumni.contact_number,
                'email': alumni.email
            })
        return JsonResponse({'success': False, 'errors': dict(form.errors.items())}, status=400)

    form = AlumniRegistrationForm()
    return render(request, 'alumni/register.html', {'form': form})

 


@csrf_exempt
def resend_otp_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            contact = data.get('contact')
            otp_type = data.get('type')

            if not contact or not otp_type:
                return JsonResponse({'success': False, 'message': 'Invalid request data.'}, status=400)
            
            if otp_type == 'phone':
                send_sms_otp(contact)
            elif otp_type == 'email':
                send_email_otp(contact)
            else:
                return JsonResponse({'success': False, 'message': 'Invalid OTP type.'}, status=400)

            return JsonResponse({'success': True, 'message': f'{otp_type.capitalize()} OTP resent successfully.'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON.'}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)



# In your views.py, replace the verify_registration_otp_view with this:

def verify_registration_otp_view(request):
    if request.method == 'POST':
        phone_otp = request.POST.get('phoneOtp')
        email_otp = request.POST.get('emailOtp')
        reg_id = request.session.get('pending_registration_id')

        try:
            alumni = Alumni.objects.get(id=reg_id)
        except Alumni.DoesNotExist:
            messages.error(request, "Session expired. Please register again.")
            return redirect('alumni:register')

        # Verify Phone OTP
        phone_valid = False
        try:
            phone_otp_record = OTPVerification.objects.get(
                contact=alumni.contact_number, 
                otp=phone_otp,
                expires_at__gt=timezone.now(), 
                is_verified=False
            )
            phone_valid = True
        except OTPVerification.DoesNotExist:
            pass
        
        # Verify Email OTP
        email_valid = False
        try:
            email_otp_record = OTPVerification.objects.get(
                contact=alumni.email, 
                otp=email_otp,
                expires_at__gt=timezone.now(), 
                is_verified=False
            )
            email_valid = True
        except OTPVerification.DoesNotExist:
            pass

        if phone_valid and email_valid:
            # Mark both OTPs as verified to prevent reuse
            phone_otp_record.is_verified = True
            phone_otp_record.save()
            
            email_otp_record.is_verified = True
            email_otp_record.save()

            alumni.is_verified = True
            alumni.save()
            
            messages.success(request, "The information provided will be verified within 72 hours, you can come back later to Log-In.")
            return redirect('alumni:login')

        messages.error(request, "Invalid or expired OTP(s). Please try again.")
        # Render the registration page again, but keep the user on step 2
        return render(request, 'alumni/register.html', {
            'form': AlumniRegistrationForm(instance=alumni),
            'step': 2,
            'contact': alumni.contact_number,
            'email': alumni.email
        })


@login_required
def directory_view(request):
    """Alumni directory with filters - only shows results when searched"""
    form = AlumniFilterForm(request.GET)
    alumni_list = Alumni.objects.none()
    has_search_params = any(request.GET.get(field) for field in [
        'name', 'joining_year', 'work_association', 'specialization', 'location', 'designation'
    ])

    if has_search_params and form.is_valid():
        alumni_list = Alumni.objects.filter(status='approved')
        
        if form.cleaned_data['name']:
            alumni_list = alumni_list.filter(name__icontains=form.cleaned_data['name'])
        if form.cleaned_data['joining_year']:
            alumni_list = alumni_list.filter(joining_year_ug=form.cleaned_data['joining_year'])
        if form.cleaned_data['work_association']:
            alumni_list = alumni_list.filter(current_work_association__icontains=form.cleaned_data['work_association'])
        if form.cleaned_data['specialization']:
            alumni_list = alumni_list.filter(specialty__icontains=form.cleaned_data['specialization'])
        if form.cleaned_data['location']:
            alumni_list = alumni_list.filter(
                Q(city__icontains=form.cleaned_data['location']) |
                Q(state__icontains=form.cleaned_data['location']) |
                Q(country__icontains=form.cleaned_data['location'])
            )
        if form.cleaned_data['designation']:
            alumni_list = alumni_list.filter(current_designation__icontains=form.cleaned_data['designation'])

    alumni_list_with_delay = []
    for idx, alumni in enumerate(alumni_list):
        alumni_list_with_delay.append({
            "alumni": alumni,
            "delay": (idx + 1) * 50
        })

    return render(request, 'alumni/directory.html', {
        'alumni_list': alumni_list_with_delay,
        'filter_form': form,
        'has_search_params': has_search_params
    })


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
    # Only allow POST to avoid accidental/CSRF actions
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('alumni:admin_panel')

    # Allow any admin (staff or in AdminUser) to act
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
        # If you want only super admins to delete, change guard here to: if not is_super_admin(request.user): ...
        alumni.delete()
        messages.success(request, 'Alumni record deleted')

    else:
        messages.error(request, 'Invalid action')

    return redirect('alumni:admin_panel')



@login_required
def admin_alumni_search_view(request):
    """
    Handles live search requests from the admin panel and returns JSON data.
    """
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access Denied'}, status=403)

    alumni_list = Alumni.objects.filter(status='approved')
    
    # Get search parameters from the request
    name = request.GET.get('name', '')
    joining_year = request.GET.get('joining_year', '')
    work_association = request.GET.get('work_association', '')
    specialization = request.GET.get('specialization', '')
    location = request.GET.get('location', '')
    designation = request.GET.get('designation', '')

    # Apply filters
    if name:
        alumni_list = alumni_list.filter(name__icontains=name)
    if joining_year:
        alumni_list = alumni_list.filter(Q(joining_year_ug=joining_year) | Q(joining_year_pg=joining_year))
    if work_association:
        alumni_list = alumni_list.filter(current_work_association__icontains=work_association)
    if specialization:
        alumni_list = alumni_list.filter(specialty__icontains=specialization)
    if location:
        alumni_list = alumni_list.filter(Q(city__icontains=location) | Q(country__icontains=location))
    if designation:
        alumni_list = alumni_list.filter(current_designation__icontains=designation)

    # Prepare data for JSON response
    data = []
    for alumni in alumni_list:
        data.append({
            'id': alumni.id,
            'name': alumni.name,
            'photo_url': alumni.photo.url if alumni.photo else '',
            'academic_association': alumni.academic_association,
            'joining_year_ug': alumni.joining_year_ug,
            'joining_year_pg': alumni.joining_year_pg,
            'specialty': alumni.specialty or 'N/A',
            'city': alumni.city,
            'country': alumni.country,
            'current_designation': alumni.current_designation or 'N/A',
            'current_work_association': alumni.current_work_association or 'N/A',
        })
        
    return JsonResponse({'alumni': data})






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
        'photo_url': alumnus.photo.url if alumnus.photo else '',
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
    """Admin can edit an alumni's profile."""
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('alumni:admin_login')

    alumnus = get_object_or_404(Alumni, id=alumni_id)

    if request.method == 'POST':
        # Use the same registration form to edit
        form = AlumniRegistrationForm(request.POST, request.FILES, instance=alumnus)
        if form.is_valid():
            form.save()
            messages.success(request, f"Profile for {alumnus.name} has been updated successfully.")
            return redirect('alumni:admin_panel')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # On GET request, show the form with existing data
        form = AlumniRegistrationForm(instance=alumnus)

    context = {
        'form': form,
        'alumnus': alumnus
    }
    return render(request, 'alumni/admin_edit_alumni.html', context)


def logout_view(request):
    """Logout user"""
    logout(request)
    return redirect('alumni:login')

def admin_logout_view(request):
    """Logout admin"""
    logout(request)
    return redirect('alumni:admin_login')
