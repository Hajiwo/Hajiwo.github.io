from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Article, Comment, Topic, DiscussionPost
from .notifications import collect_articles, topic_changed, comment_created


@receiver(post_save, sender=Article)
def published(sender, instance, **kwargs):
    if instance.status == 'published' and instance.content_type == 'article':
        transaction.on_commit(collect_articles)


@receiver(post_save, sender=Comment)
def comment(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: comment_created(instance))


@receiver(pre_save, sender=Topic)
def topic_before_save(sender, instance, **kwargs):
    old = Topic.objects.filter(pk=instance.pk).first() if instance.pk else None
    instance._content_changed = bool(old and (old.title != instance.title or old.body != instance.body))
    if instance._content_changed:
        instance.updated_at = timezone.now()


@receiver(post_save, sender=Topic)
def topic(sender, instance, created, **kwargs):
    if created or getattr(instance, '_content_changed', False):
        transaction.on_commit(lambda: topic_changed(instance, edited=not created))


@receiver(post_save, sender=DiscussionPost)
def post(sender, instance, created, **kwargs):
    if created:
        Topic.objects.filter(pk=instance.topic_id).update(updated_at=timezone.now())
        transaction.on_commit(lambda: topic_changed(instance.topic, instance))
