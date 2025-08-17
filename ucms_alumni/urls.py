"""ucms_alumni URL Configuration"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as django_static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('alumni.urls')),

    # serve media in production too (small sites) 👇
    re_path(r'^media/(?P<path>.*)$',
            django_static_serve,
            {'document_root': settings.MEDIA_ROOT}),
]

# Optional: still serve static/media when DEBUG=True (local dev)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
