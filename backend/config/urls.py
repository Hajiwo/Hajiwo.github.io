from django.urls import include, path
from django.conf import settings
from blog.admin import blog_admin
urlpatterns = [path('admin/', blog_admin.urls), path('api/v1/', include('blog.urls'))]
if settings.INFOTECH_ENABLED:
    urlpatterns.append(path('infotech/', include('infotech.urls')))
