from rest_framework import serializers
from .models import Article, Comment, Series

class SeriesSerializer(serializers.ModelSerializer):
    article_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Series
        fields = ['name', 'name_en', 'slug', 'description', 'description_en', 'article_count']

class ArticleSerializer(serializers.ModelSerializer):
    series = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    series_name = serializers.CharField(source='series.name', read_only=True)
    series_name_en = serializers.CharField(source='series.name_en', read_only=True)
    class Meta:
        model = Article
        fields = [
            'title', 'title_en', 'slug', 'description', 'description_en', 'content_type',
            'series', 'series_name', 'series_name_en', 'published_at', 'updated_at',
        ]

class ArticleDetailSerializer(ArticleSerializer):
    class Meta(ArticleSerializer.Meta):
        fields = ArticleSerializer.Meta.fields + ['body', 'body_en']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'author', 'body', 'created_at']
        read_only_fields = ['id', 'created_at']
