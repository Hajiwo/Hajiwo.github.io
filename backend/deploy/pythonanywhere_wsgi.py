"""Copy into the WSGI configuration opened from PythonAnywhere's Web tab."""
import os
import sys

# Replace YOUR_USERNAME and the checkout path before use.
project = '/home/YOUR_USERNAME/Hajiwo.github.io/backend'
if project not in sys.path:
    sys.path.insert(0, project)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
