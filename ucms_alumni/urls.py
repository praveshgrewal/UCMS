"""ucms_alumni URL Configuration"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as django_static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('alumni.urls')),

    # Serve user-uploaded media in production (OK for small sites)
    re_path(r'^media/(?P<path>.*)$',
            django_static_serve,
            {'document_root': settings.MEDIA_ROOT}),
]

# Optional: local dev convenience
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
