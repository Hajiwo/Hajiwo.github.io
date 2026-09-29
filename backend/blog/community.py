"""Subscriber identity is proved by a one-use email link, never by a posted email."""
import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from .models import Subscriber, SubscriberLogin, SubscriberSession, Topic, DiscussionPost


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def reader(request):
    authorization = request.headers.get('Authorization', '')
    if not authorization:
        return None
    if not authorization.startswith('Bearer '):
        raise AuthenticationFailed('Please sign in again.')
    session = SubscriberSession.objects.select_related('subscriber').filter(
        token_hash=digest(authorization[7:]), expires_at__gt=timezone.now(), subscriber__verified_at__isnull=False,
    ).first()
    if not session:
        raise AuthenticationFailed('Your saved sign-in expired. Please sign in again.')
    return session.subscriber


class SubscriptionThrottle(AnonRateThrottle):
    scope = 'subscriptions'


class VerifyThrottle(AnonRateThrottle):
    scope = 'verify'


class CommunityThrottle(AnonRateThrottle):
    scope = 'community'


class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        fields = ['name', 'email', 'active', 'articles', 'discussions', 'replies', 'language']
        read_only_fields = ['email']


class SubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    name = serializers.CharField(max_length=80)
    language = serializers.ChoiceField(choices=['zh', 'en'], default='zh')


@api_view(['POST'])
@throttle_classes([SubscriptionThrottle])
def subscribe(request):
    data = SubscribeSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    email = values['email'].casefold()
    if not settings.SUBSCRIPTIONS_ENABLED:
        return Response({'detail': 'Email subscriptions are not configured yet.'}, status=503)
    key = f'subscribe:{digest(email)}'
    if not cache.add(key, True, 60):
        return Response({'detail': 'Please wait one minute before requesting another email.'}, status=429)
    subscriber, _ = Subscriber.objects.get_or_create(email=email, defaults={'name': values['name']})
    token = secrets.token_urlsafe(32)
    login = SubscriberLogin.objects.create(subscriber=subscriber, token_hash=digest(token),
        name=values['name'], language=values['language'], expires_at=timezone.now() + timedelta(minutes=30))
    link = f'{settings.ARTICLES_SITE_URL}/subscribe/#verify={token}'
    subject = '确认订阅 Articles / Confirm your Articles subscription'
    body = f'点击链接验证邮箱并订阅（30 分钟内有效）：\nVerify your email and subscribe (valid for 30 minutes):\n{link}\n\n未申请请忽略。If you did not request this, ignore this email.'
    try:
        if send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email]) != 1:
            raise RuntimeError('Mail delivery unavailable')
    except Exception:
        login.delete()
        cache.delete(key)
        return Response({'detail': 'Could not send verification email. Please try again later.'}, status=503)
    return Response({'status': 'verification_sent'}, status=202)


@api_view(['POST'])
@throttle_classes([VerifyThrottle])
def verify(request):
    token = request.data.get('token', '')
    if not isinstance(token, str) or len(token) > 200:
        raise ValidationError('Invalid link.')
    now = timezone.now()
    with transaction.atomic():
        login = SubscriberLogin.objects.filter(token_hash=digest(token), used_at__isnull=True, expires_at__gt=now).first()
        if not login or not SubscriberLogin.objects.filter(pk=login.pk, used_at__isnull=True).update(used_at=now):
            raise ValidationError('This link has expired or was already used. Request a new email.')
        subscriber = login.subscriber
        subscriber.name, subscriber.language = login.name, login.language
        subscriber.verified_at, subscriber.active = now, True
        subscriber.save(update_fields=['name', 'language', 'verified_at', 'active'])
        session_token = secrets.token_urlsafe(32)
        SubscriberSession.objects.create(subscriber=subscriber, token_hash=digest(session_token), expires_at=now + timedelta(days=180))
    response = Response({'token': session_token, 'subscriber': SubscriberSerializer(subscriber).data})
    response['Cache-Control'] = 'no-store'
    return response


@api_view(['GET', 'PATCH', 'DELETE'])
def subscription_me(request):
    subscriber = reader(request)
    if not subscriber:
        raise AuthenticationFailed('Sign in with your email first.')
    if request.method == 'DELETE':
        SubscriberSession.objects.filter(token_hash=digest(request.headers['Authorization'][7:])).delete()
        return Response(status=204)
    if request.method == 'PATCH':
        serializer = SubscriberSerializer(subscriber, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    response = Response(SubscriberSerializer(subscriber).data)
    response['Cache-Control'] = 'no-store'
    return response


@api_view(['POST'])
@throttle_classes([VerifyThrottle])
def unsubscribe(request):
    from uuid import UUID
    try:
        token = UUID(str(request.data.get('token', '')))
    except ValueError:
        raise ValidationError('Invalid unsubscribe link.')
    subscriber = get_object_or_404(Subscriber, unsubscribe_token=token)
    subscriber.active = False
    subscriber.save(update_fields=['active'])
    return Response({'status': 'unsubscribed'})


class TopicSerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Topic
        fields = ['id', 'title', 'author', 'body', 'locked', 'created_at', 'updated_at', 'post_count']
        read_only_fields = ['id', 'locked', 'created_at', 'updated_at']


class PostSerializer(serializers.ModelSerializer):
    verified_reader = serializers.SerializerMethodField()

    def get_verified_reader(self, obj):
        return bool(obj.subscriber_id)

    parent_author = serializers.SerializerMethodField()
    class Meta:
        model = DiscussionPost
        fields = ['id', 'author', 'body', 'parent', 'parent_author', 'verified_reader', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_parent_author(self, obj):
        return obj.parent.author if obj.parent and obj.parent.visible else None

    def validate_parent(self, parent):
        if parent and (parent.topic_id != self.context['topic'].pk or not parent.visible):
            raise serializers.ValidationError('Choose a visible reply in this topic.')
        return parent


class Topics(generics.ListCreateAPIView):
    serializer_class = TopicSerializer
    def get_queryset(self):
        return Topic.objects.filter(visible=True).annotate(post_count=Count('posts', filter=Q(posts__visible=True))).order_by('-updated_at', '-id')
    def get_throttles(self):
        return [CommunityThrottle()] if self.request.method == 'POST' else []
    def perform_create(self, serializer):
        subscriber = reader(self.request)
        serializer.save(subscriber=subscriber, **({'author': subscriber.name} if subscriber else {}))


class TopicDetail(generics.RetrieveAPIView):
    serializer_class = TopicSerializer
    queryset = Topic.objects.filter(visible=True).annotate(post_count=Count('posts', filter=Q(posts__visible=True)))


class TopicPosts(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    def get_topic(self):
        return get_object_or_404(Topic, pk=self.kwargs['pk'], visible=True)
    def get_queryset(self):
        return self.get_topic().posts.filter(visible=True).select_related('parent')
    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'topic': self.get_topic()}
    def get_throttles(self):
        return [CommunityThrottle()] if self.request.method == 'POST' else []
    def perform_create(self, serializer):
        topic = self.get_topic()
        if topic.locked:
            raise ValidationError('This topic is closed to new replies.')
        subscriber = reader(self.request)
        serializer.save(topic=topic, subscriber=subscriber, **({'author': subscriber.name} if subscriber else {}))
