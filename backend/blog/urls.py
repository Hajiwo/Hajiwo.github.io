from django.urls import path
from . import views
urlpatterns = [
    path('health/', views.health),
    path('series/', views.SeriesList.as_view()),
    path('articles/', views.ArticleList.as_view()),
    path('articles/<slug:slug>/', views.ArticleDetail.as_view()),
    path('articles/<slug:slug>/comments/', views.Comments.as_view()),
]
