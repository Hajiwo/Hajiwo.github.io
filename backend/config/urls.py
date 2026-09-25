from django.urls import include, path
from blog.admin import blog_admin
urlpatterns = [path('admin/', blog_admin.urls), path('api/v1/', include('blog.urls'))]
