"""Copy this file into the WSGI configuration shown in PythonAnywhere's Web tab."""
import os
import sys
from dotenv import load_dotenv

project = os.path.expanduser('~/Hajiwo.github.io/backend')
if project not in sys.path:
    sys.path.insert(0, project)
load_dotenv(os.path.join(project, '.env'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
