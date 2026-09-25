from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from .models import Article, Comment, Series
from .serializers import ArticleSerializer, ArticleDetailSerializer, CommentSerializer, SeriesSerializer

@api_view(['GET'])
def health(request):
    return Response({'status': 'ok'})

class SeriesList(generics.ListAPIView):
    serializer_class = SeriesSerializer
    def get_queryset(self):
        return Series.objects.annotate(article_count=Count('articles', filter=Q(
            articles__status='published', articles__published_at__lte=timezone.now()
        ))).order_by('order', 'name', 'id')

class ArticleList(generics.ListAPIView):
    serializer_class = ArticleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'title_en', 'description', 'description_en', 'body', 'body_en']
    def get_queryset(self):
        queryset = Article.objects.published().select_related('series')
        series = self.request.query_params.get('series')
        return queryset.filter(series__slug=series) if series else queryset

class ArticleDetail(generics.RetrieveAPIView):
    serializer_class = ArticleDetailSerializer
    lookup_field = 'slug'
    def get_queryset(self):
        return Article.objects.published().select_related('series')

class CommentThrottle(AnonRateThrottle):
    scope = 'comments'

class Comments(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    def get_throttles(self):
        return [CommentThrottle()] if self.request.method == 'POST' else []

    def get_article(self):
        return get_object_or_404(Article.objects.published(), slug=self.kwargs['slug'])

    def get_queryset(self):
        return Comment.objects.filter(article=self.get_article(), approved=True)

    def create(self, request, *args, **kwargs):
        article = self.get_article()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(article=article, approved=False)
        return Response({'status': 'pending', 'message': '评论已提交，审核后显示。'}, status=status.HTTP_201_CREATED)
