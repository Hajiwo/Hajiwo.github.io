from django.urls import path
from . import views, community, mail_worker
urlpatterns = [
    path('mail-worker/claim/', mail_worker.claim),
    path('mail-worker/ack/', mail_worker.acknowledge),
    path('subscriptions/account/', community.subscription_account),
    path('subscriptions/', community.subscribe),
    path('subscriptions/login/', community.login),
    path('subscriptions/verify/', community.verify),
    path('subscriptions/me/', community.subscription_me),
    path('subscriptions/unsubscribe/', community.unsubscribe),
    path('topics/', community.Topics.as_view()),
    path('topics/<int:pk>/', community.TopicDetail.as_view()),
    path('topics/<int:pk>/posts/', community.TopicPosts.as_view()),
    path('health/', views.health),
    path('series/', views.SeriesList.as_view()),
    path('articles/', views.ArticleList.as_view()),
    path('articles/<slug:slug>/', views.ArticleDetail.as_view()),
    path('articles/<slug:slug>/comments/', views.Comments.as_view()),
]
