from django.urls import path
from . import views

app_name = 'alumni'

urlpatterns = [
    # Public URLs
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('send-otp/', views.send_otp_view, name='send_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-registration-otp/', views.verify_registration_otp_view, name='verify_registration_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'), # New path


    
    # Alumni URLs
    path('directory/', views.directory_view, name='directory'),
    path('profile/', views.profile_view, name='profile'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('admin-search/', views.admin_search_view, name='admin_search'),


       # URL for the dedicated alumni profile page
    path('alumni-profile/<int:alumni_id>/', views.alumni_detail_page_view, name='alumni_detail_page'),
    
    # URL for fetching data for the modal (optional)
    path('get-alumni-details/<int:alumni_id>/', views.get_alumni_details_view, name='get_alumni_details'),
    
    
    # Admin URLs
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('admin-review/<int:alumni_id>/', views.admin_review_view, name='admin_review'),
    path('admin-action/<int:alumni_id>/<str:action>/', views.admin_action_view, name='admin_action'),
    path('admin-logout/', views.admin_logout_view, name='admin_logout'),
    path('admin-edit/<int:alumni_id>/', views.admin_edit_alumni_view, name='admin_edit_alumni'),
    path('admin-search/', views.admin_alumni_search_view, name='admin_alumni_search'),

]
