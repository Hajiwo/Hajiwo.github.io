from django.urls import path
from . import views
app_name = 'infotech'
urlpatterns = [path('language/', views.language, name='language'), path('', views.course_list, name='courses'), path('enter/', views.enter, name='enter'), path('lock/', views.lock, name='lock'), path('courses/add/', views.course_form, name='course_add'), path('courses/<int:pk>/edit/', views.course_form, name='course_edit'), path('section/<slug:section>/add/', views.card_form, name='card_add'), path('section/<slug:section>/<int:pk>/edit/', views.card_form, name='card_edit'), path('section/<slug:section>/', views.section, name='section')]

