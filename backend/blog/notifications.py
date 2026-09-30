"""Durable outbox: run send_notifications --watch to deliver and retry email."""
import uuid
from datetime import timedelta
from urllib.parse import quote
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone
from .models import Article, Subscriber, SubscriberLogin, Notification, Topic


def recipients(kind):
    return Subscriber.objects.filter(active=True, verified_at__isnull=False, **{kind: True})


def enqueue(subscribers, key, kind, title, path, **source):
    for subscriber in subscribers:
        Notification.objects.get_or_create(subscriber=subscriber, event_key=key,
            defaults={'kind': kind, 'title': title[:200], 'path': path, **source})


def collect_articles():
    # This also handles scheduled publication and bulk admin actions.
    for article in Article.objects.published().filter(content_type='article', notification_sent_at__isnull=True):
        with transaction.atomic():
            if Article.objects.filter(pk=article.pk, notification_sent_at__isnull=True).update(notification_sent_at=timezone.now()):
                enqueue(recipients('articles'), f'article:{article.pk}', 'articles', article.title,
                        f'/article/?slug={quote(article.slug)}', article=article)


def topic_changed(topic, post=None, edited=False):
    if not topic.visible or (post and not post.visible):
        return
    actor = post.subscriber_id if post else topic.subscriber_id
    event = f'post:{post.pk}' if post else (f'topic:{topic.pk}:{topic.updated_at.isoformat()}' if edited else f'topic:{topic.pk}')
    path = f'/discussion/topic/?id={topic.pk}' + (f'#post-{post.pk}' if post else '')
    audience = recipients('discussions').exclude(pk=actor)
    enqueue(audience, event, 'discussions', topic.title, path, topic=topic, post=post)
    target = post.parent.subscriber if post and post.parent and post.parent.visible else None
    if target and target.pk != actor and target.active and target.verified_at and target.replies:
        enqueue([target], event, 'replies', topic.title, path, topic=topic, post=post)


def comment_created(comment):
    if not comment.approved or comment.article.content_type != 'article' or not comment.parent or not comment.parent.approved:
        return
    target = comment.parent.subscriber
    if target and target.pk != comment.subscriber_id and target.active and target.verified_at and target.replies:
        enqueue([target], f'comment:{comment.pk}', 'replies', comment.article.title,
                f'/article/?slug={quote(comment.article.slug)}#comment-{comment.pk}', article=comment.article, comment=comment)


def deliver_verifications(limit=20):
    """Deliver queued verification links through the server SMTP connection."""
    if not settings.SUBSCRIPTIONS_ENABLED or settings.MAIL_DELIVERY_MODE != 'smtp':
        return 0
    now = timezone.now()
    eligible = Q(claimed_at__isnull=True) | Q(claimed_at__lt=now - timedelta(minutes=10))
    SubscriberLogin.objects.filter(expires_at__lte=now).exclude(delivery_token='').update(delivery_token='')
    ids = list(SubscriberLogin.objects.filter(
        eligible, used_at__isnull=True, sent_at__isnull=True, expires_at__gt=now,
        next_attempt_at__lte=now,
    ).exclude(delivery_token='').values_list('pk', flat=True)[:limit])
    sent = 0
    for pk in ids:
        lease = uuid.uuid4()
        if not SubscriberLogin.objects.filter(
            eligible, pk=pk, used_at__isnull=True, sent_at__isnull=True,
        ).exclude(delivery_token='').update(claimed_at=now, lease_token=lease, attempts=F('attempts') + 1):
            continue
        login = SubscriberLogin.objects.select_related('subscriber').get(pk=pk)
        subject, body = verification_message(login.delivery_token)
        try:
            if EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [login.subscriber.email]).send() != 1:
                raise RuntimeError('Email backend returned no delivery')
            updated = SubscriberLogin.objects.filter(pk=pk, lease_token=lease, sent_at__isnull=True).update(
                sent_at=timezone.now(), expires_at=timezone.now() + timedelta(minutes=30),
                delivery_token='', claimed_at=None, lease_token=None, last_error='',
            )
            sent += updated
        except Exception as exc:
            SubscriberLogin.objects.filter(pk=pk, lease_token=lease, sent_at__isnull=True).update(
                claimed_at=None, lease_token=None, last_error=type(exc).__name__,
                next_attempt_at=timezone.now() + timedelta(minutes=min(60, 2 ** min(login.attempts, 6))),
            )
    return sent


def deliver_pending(limit=100):
    if not settings.SUBSCRIPTIONS_ENABLED:
        return 0
    now = timezone.now()
    eligible = Q(claimed_at__isnull=True) | Q(claimed_at__lt=now - timedelta(minutes=10))
    ids = list(Notification.objects.filter(eligible, sent_at__isnull=True, cancelled=False, next_attempt_at__lte=now).values_list('pk', flat=True)[:limit])
    sent = 0
    for pk in ids:
        if not Notification.objects.filter(eligible, pk=pk, sent_at__isnull=True).update(claimed_at=now, attempts=F('attempts') + 1):
            continue
        item = Notification.objects.select_related('subscriber', 'article', 'topic', 'comment', 'post').get(pk=pk)
        payload = notification_message(item)
        if not payload:
            Notification.objects.filter(pk=pk).update(cancelled=True, claimed_at=None)
            continue
        subscriber = item.subscriber
        subject, body = payload
        try:
            if EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [subscriber.email]).send() != 1:
                raise RuntimeError('Email backend returned no delivery')
            Notification.objects.filter(pk=pk).update(sent_at=timezone.now(), claimed_at=None, last_error='')
            sent += 1
        except Exception as exc:
            # Do not store SMTP credentials or server responses in the admin/logs.
            Notification.objects.filter(pk=pk).update(claimed_at=None, last_error=type(exc).__name__,
                next_attempt_at=timezone.now() + timedelta(minutes=min(60, 2 ** min(item.attempts, 6))))
    return sent


def notification_message(item):
    subscriber = item.subscriber
    now = timezone.now()
    unsubscribe = f'{settings.ARTICLES_SITE_URL}/subscribe/#unsubscribe={subscriber.unsubscribe_token}'
    if item.kind == 'welcome':
        if not subscriber.active or not subscriber.verified_at:
            return None
        if subscriber.language == 'en':
            return ('Subscription successful · Articles',
                    f'Hi {subscriber.name}, your subscription is active.\n\nManage notification preferences:\n{settings.ARTICLES_SITE_URL}/subscribe/\n\nUnsubscribe:\n{unsubscribe}')
        return ('订阅成功 · Articles',
                f'{subscriber.name}，你已成功订阅并登录。\n\n管理通知偏好：\n{settings.ARTICLES_SITE_URL}/subscribe/\n\n退订：\n{unsubscribe}')
    visible = (not item.article_id or (item.article.status == 'published' and item.article.published_at <= now and item.article.content_type == 'article')) and (not item.topic_id or item.topic.visible) and (not item.comment_id or item.comment.approved) and (not item.post_id or item.post.visible)
    if not visible or not subscriber.active or not subscriber.verified_at or not getattr(subscriber, item.kind):
        return None
    labels = {'articles': ('新文章', 'New article'), 'discussions': ('讨论更新', 'Discussion update'), 'replies': ('你收到了回复', 'You received a reply')}
    label = labels[item.kind][subscriber.language == 'en']
    subject = ' '.join(f'{label} · {item.title}'.splitlines())[:240]
    body = f'{label}: {item.title}\n\n{settings.ARTICLES_SITE_URL}{item.path}\n\n退订 / Unsubscribe:\n{unsubscribe}'
    return subject, body


def verification_message(token):
    login = token.startswith('login_')
    mode = '&mode=login' if login else '&mode=subscribe'
    link = f'{settings.ARTICLES_SITE_URL}/subscribe/#verify={token}{mode}'
    if login:
        return ('登录 Articles / Sign in to Articles',
                f'点击链接验证邮箱并登录（30 分钟内有效）：\nVerify your email and sign in (valid for 30 minutes):\n{link}\n\n未申请请忽略。If you did not request this, ignore this email.')
    return ('确认订阅 Articles / Confirm your Articles subscription',
            f'点击链接验证邮箱并订阅（30 分钟内有效）：\nVerify your email and subscribe (valid for 30 minutes):\n{link}\n\n未申请请忽略。If you did not request this, ignore this email.')
