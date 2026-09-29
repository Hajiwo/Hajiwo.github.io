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
    body_en = serializers.SerializerMethodField()

    def get_body_en(self, obj):
        return obj.body_en.strip() or 'Sorry, this article is currently only available in Chinese.'

    class Meta(ArticleSerializer.Meta):
        fields = ArticleSerializer.Meta.fields + ['body', 'body_en']

class CommentSerializer(serializers.ModelSerializer):
    verified_reader = serializers.SerializerMethodField()

    def get_verified_reader(self, obj):
        return bool(obj.subscriber_id)

    parent_author = serializers.SerializerMethodField()

    def get_parent_author(self, obj):
        return obj.parent.author if obj.parent and obj.parent.approved else None

    def validate_parent(self, parent):
        if parent and (parent.article_id != self.context['article'].pk or not parent.approved):
            raise serializers.ValidationError('Choose a visible comment in this article.')
        return parent

    class Meta:
        model = Comment
        fields = ['id', 'author', 'body', 'parent', 'parent_author', 'verified_reader', 'created_at']
        read_only_fields = ['id', 'created_at']
