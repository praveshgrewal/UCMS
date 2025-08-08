from django.contrib import admin
from .models import Alumni, OTPVerification, AdminUser

admin.site.site_header = "UCMS Alumni Portal Administration"
admin.site.site_title = "UCMS Admin"
admin.site.index_title = "Welcome to the Admin Dashboard"

@admin.register(Alumni)
class AlumniAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'joining_year_ug', 'specialty', 'status', 'created_at']
    list_filter = ['status', 'joining_year_ug', 'specialty', 'country']
    search_fields = ['name', 'email', 'contact_number']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['contact', 'otp', 'is_verified', 'created_at', 'expires_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['contact']

@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_super_admin', 'created_at']
    list_filter = ['is_super_admin', 'created_at']
