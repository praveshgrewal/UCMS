"""
WSGI config for ucms_alumni project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ucms_alumni.settings')

application = get_wsgi_application()
