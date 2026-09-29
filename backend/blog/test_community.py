from datetime import timedelta
from unittest.mock import patch
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from .models import Article, Comment, Subscriber, SubscriberLogin, SubscriberSession, Topic, DiscussionPost, Notification
from .community import digest
from .notifications import collect_articles, deliver_pending, deliver_verifications, topic_changed


@override_settings(SECURE_SSL_REDIRECT=False, SUBSCRIPTIONS_ENABLED=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CommunityTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.article = Article.objects.create(title='中文文章', slug='example', status='published')
        self.reader = Subscriber.objects.create(email='reader@example.com', name='Reader', active=True, verified_at=timezone.now())
        self.other = Subscriber.objects.create(email='other@example.com', name='Other', active=True, verified_at=timezone.now())
        SubscriberSession.objects.create(subscriber=self.reader, token_hash=digest('test-session'), expires_at=timezone.now()+timedelta(days=1))
        self.comments = '/api/v1/articles/example/comments/'

    def sign_in(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer test-session')

    def test_comments_publish_and_reply_immediately(self):
        response = self.client.post(self.comments, {'author': 'Guest', 'body': '**hello**', 'approved': False})
        self.assertEqual(response.status_code, 201)
        comment = Comment.objects.get()
        self.assertTrue(comment.approved)
        self.assertIsNone(comment.subscriber)
        reply = self.client.post(self.comments, {'author': 'Second', 'body': 'reply', 'parent': comment.pk})
        self.assertEqual(reply.status_code, 201)
        self.assertEqual(reply.json()['parent_author'], 'Guest')
        self.assertEqual(self.client.get(self.comments).json()['count'], 2)
        self.assertFalse(Notification.objects.exists())

    def test_reply_cannot_cross_articles_or_hidden_comments(self):
        another = Article.objects.create(title='Other', slug='other', status='published')
        parent = Comment.objects.create(article=another, author='A', body='B', approved=True)
        self.assertEqual(self.client.post(self.comments, {'author':'B', 'body':'reply', 'parent':parent.pk}).status_code, 400)
        parent.article = self.article; parent.approved = False; parent.save()
        self.assertEqual(self.client.post(self.comments, {'author':'B', 'body':'reply', 'parent':parent.pk}).status_code, 400)

    def test_identity_is_server_verified_and_email_not_public(self):
        self.sign_in()
        response = self.client.post(self.comments, {'author':'Spoof', 'body':'hello', 'subscriber':self.other.pk})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['author'], 'Reader')
        self.assertEqual(Comment.objects.get().subscriber, self.reader)
        self.assertNotIn('email', response.json())
        self.assertNotIn('subscriber', response.json())
        self.client.credentials(HTTP_AUTHORIZATION='Bearer forged')
        self.assertIn(self.client.post(self.comments, {'author':'A','body':'B'}).status_code, [401,403])
        self.assertEqual(Comment.objects.count(), 1)

    def test_verification_one_use_and_case_insensitive_email(self):
        response = self.client.post('/api/v1/subscriptions/', {'email':'Reader@Example.com','name':'New name','language':'en'})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {'status': 'verification_queued'})
        self.assertEqual(Subscriber.objects.count(), 2)
        self.reader.refresh_from_db(); self.assertEqual(self.reader.name, 'Reader')
        self.assertEqual(deliver_verifications(), 1)
        token = mail.outbox[-1].body.split('#verify=')[1].split()[0]
        verified = self.client.post('/api/v1/subscriptions/verify/', {'token':token})
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified['Cache-Control'], 'no-store')
        self.assertEqual(verified.json()['subscriber']['name'], 'New name')
        self.assertEqual(self.client.post('/api/v1/subscriptions/verify/', {'token':token}).status_code, 400)
        self.assertFalse(SubscriberSession.objects.filter(token_hash=verified.json()['token']).exists())
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+verified.json()['token'])
        self.assertEqual(self.client.get('/api/v1/subscriptions/me/').status_code, 200)
        self.assertEqual(self.client.delete('/api/v1/subscriptions/me/').status_code, 204)
        self.assertIn(self.client.get('/api/v1/subscriptions/me/').status_code, [401,403])

    def test_unverified_and_expired_links_and_email_failure(self):
        self.assertEqual(self.client.post('/api/v1/subscriptions/', {'email':'new@example.com','name':'N'}).status_code, 202)
        with patch('blog.notifications.EmailMessage.send', side_effect=RuntimeError('SMTP failure')):
            self.assertEqual(deliver_verifications(), 0)
        pending = Subscriber.objects.get(email='new@example.com')
        self.assertFalse(pending.active)
        self.assertIsNone(pending.verified_at)
        queued = SubscriberLogin.objects.get()
        self.assertEqual(queued.last_error, 'RuntimeError')
        self.assertEqual(queued.attempts, 1)
        SubscriberLogin.objects.create(subscriber=pending, token_hash=digest('expired'), name='N', expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.client.post('/api/v1/subscriptions/verify/', {'token':'expired'}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/subscriptions/verify/', {'token':['bad']}, format='json').status_code, 400)

    def test_topics_create_reply_paginate_lock_hide_and_admin_boundary(self):
        self.sign_in()
        created = self.client.post('/api/v1/topics/', {'title':'Topic A','author':'Spoof','body':'# Hello','locked':True})
        self.assertEqual(created.status_code, 201)
        topic = Topic.objects.get()
        self.assertFalse(topic.locked)
        self.assertEqual(topic.author, 'Reader')
        self.client.credentials()
        url = f'/api/v1/topics/{topic.pk}/posts/'
        response = self.client.post(url, {'author':'Guest','body':'```python\nprint(1)\n```'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.post(url, {'author':'B','body':'Reply','parent':response.json()['id']}).status_code, 201)
        self.assertEqual(self.client.get('/api/v1/topics/').json()['results'][0]['post_count'], 2)
        self.assertEqual(self.client.patch(f'/api/v1/topics/{topic.pk}/', {'title':'Hacked'}).status_code, 405)
        self.assertEqual(self.client.delete(f'/api/v1/topics/{topic.pk}/').status_code, 405)
        for _ in range(21): DiscussionPost.objects.create(topic=topic, author='A', body='test')
        self.assertEqual(len(self.client.get(url).json()['results']), 20)
        self.assertEqual(len(self.client.get(url+'?page=2').json()['results']), 3)
        topic.locked=True;topic.save()
        self.assertEqual(self.client.post(url, {'author':'A','body':'no'}).status_code, 400)
        topic.visible=False;topic.save()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get('/api/v1/topics/').json()['count'], 0)

    def test_reply_cannot_cross_topics(self):
        a = Topic.objects.create(title='A',author='A',body='A')
        b = Topic.objects.create(title='B',author='B',body='B')
        post = DiscussionPost.objects.create(topic=b,author='B',body='B')
        self.assertEqual(self.client.post(f'/api/v1/topics/{a.pk}/posts/', {'author':'A','body':'A','parent':post.pk}).status_code, 400)

    def test_notifications_publication_scope_and_idempotency(self):
        self.article.status = 'draft'; self.article.save()
        collect_articles(); self.assertEqual(Notification.objects.count(), 0)
        self.article.status = 'published'; self.article.published_at = timezone.now()+timedelta(days=1); self.article.save()
        Article.objects.create(title='Blog',slug='blog',status='published',content_type='project')
        collect_articles(); self.assertEqual(Notification.objects.count(), 0)
        Article.objects.filter(pk=self.article.pk).update(published_at=timezone.now())
        collect_articles(); collect_articles()
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(deliver_pending(), 2)
        self.assertEqual(deliver_pending(), 0)
        self.assertIn('/articles/article/?slug=example',mail.outbox[-1].body)
        self.assertIn('unsubscribe=',mail.outbox[-1].body)
        self.assertEqual(len(mail.outbox[-1].to), 1)

    def test_reply_notification_not_guest_or_self(self):
        parent = Comment.objects.create(article=self.article,author='Reader',body='parent',subscriber=self.reader,approved=True)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.comments, {'author':'Guest','body':'reply','parent':parent.pk})
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(Notification.objects.get().subscriber,self.reader)
        self.sign_in()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.comments, {'author':'Reader','body':'self reply','parent':parent.pk})
        self.assertEqual(Notification.objects.count(), 1)

    def test_discussion_notifications_deduplicate_and_honor_preferences(self):
        topic = Topic.objects.create(title='A',author='Reader',body='A',subscriber=self.reader)
        topic_changed(topic)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(Notification.objects.get().subscriber,self.other)
        parent = DiscussionPost.objects.create(topic=topic,author='Reader',body='A',subscriber=self.reader)
        post = DiscussionPost.objects.create(topic=topic,author='Other',body='B',parent=parent,subscriber=self.other)
        topic_changed(topic,post);topic_changed(topic,post)
        self.assertEqual(Notification.objects.filter(event_key=f'post:{post.pk}').count(), 1)
        self.reader.discussions=False;self.reader.save()
        next_post = DiscussionPost.objects.create(topic=topic,author='Other',body='C',parent=parent,subscriber=self.other)
        topic_changed(topic,next_post)
        self.assertEqual(Notification.objects.get(event_key=f'post:{next_post.pk}').kind,'replies')

    def test_unsubscribe_cancels_queued_delivery_and_preferences_require_identity(self):
        collect_articles()
        response = self.client.post('/api/v1/subscriptions/unsubscribe/', {'token':str(self.reader.unsubscribe_token)})
        self.assertEqual(response.status_code,200)
        self.assertEqual(deliver_pending(),1)
        self.assertTrue(Notification.objects.get(subscriber=self.reader).cancelled)
        self.assertIn(self.client.patch('/api/v1/subscriptions/me/', {'active':True}).status_code,[401,403])
        self.sign_in()
        self.assertEqual(self.client.patch('/api/v1/subscriptions/me/', {'active':True,'articles':False}).status_code,200)
        self.reader.refresh_from_db(); self.assertTrue(self.reader.active);self.assertFalse(self.reader.articles)

    def test_delivery_failure_retries_and_hidden_content_is_not_sent(self):
        collect_articles()
        with patch('blog.notifications.EmailMessage.send',side_effect=RuntimeError('secret smtp detail')):
            self.assertEqual(deliver_pending(),0)
        self.assertEqual(Notification.objects.first().last_error,'RuntimeError')
        self.assertIsNone(Notification.objects.first().sent_at)
        self.assertEqual(deliver_pending(),0)
        Notification.objects.update(next_attempt_at=timezone.now())
        Article.objects.filter(pk=self.article.pk).update(status='draft')
        self.assertEqual(deliver_pending(),0)
        self.assertEqual(Notification.objects.filter(cancelled=True).count(),2)

    def test_admin_manages_community(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_superuser('owner',password='test-password'))
        for model in ['topic','discussionpost','subscriber','subscriberlogin','notification']:
            self.assertEqual(self.client.get(f'/admin/blog/{model}/').status_code,200)
        topic=Topic.objects.create(title='A',author='A',body='hello')
        self.assertEqual(self.client.post(f'/admin/blog/topic/{topic.pk}/change/', {'title':'Edited','author':'Admin','body':'new','locked':'on','_save':'Save'}).status_code,302)
        topic.refresh_from_db();self.assertTrue(topic.locked);self.assertFalse(topic.visible)

    @override_settings(SUBSCRIPTIONS_ENABLED=False)
    def test_unconfigured_email_fails_honestly(self):
        self.assertEqual(self.client.post('/api/v1/subscriptions/', {'email':'x@example.com','name':'X'}).status_code,503)

    def test_hidden_parent_and_input_limits(self):
        topic = Topic.objects.create(title='A', author='A', body='A')
        hidden = DiscussionPost.objects.create(topic=topic, author='A', body='A', visible=False)
        url = f'/api/v1/topics/{topic.pk}/posts/'
        self.assertEqual(self.client.post(url, {'author':'A','body':'B','parent':hidden.pk}).status_code,400)
        self.assertEqual(self.client.post(url, {'author':'A','body':'B'*20001}).status_code,400)
        self.assertEqual(self.client.post('/api/v1/topics/', {'author':'A','title':' ', 'body':'B'}).status_code,400)
        self.assertEqual(self.client.post('/api/v1/topics/', {'author':'A','title':'T', 'body':' '} ).status_code,400)

    def test_admin_topic_edit_notifies_and_hiding_does_not(self):
        topic = Topic.objects.create(title='A',author='A',body='A')
        with self.captureOnCommitCallbacks(execute=True):
            topic.body='Updated';topic.save()
        self.assertEqual(Notification.objects.count(),2)
        with self.captureOnCommitCallbacks(execute=True):
            topic.visible=False;topic.save()
        self.assertEqual(Notification.objects.count(),2)
        self.assertEqual(deliver_pending(),0)

    def test_bulk_publish_enqueues_after_commit(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_superuser('publisher',password='test-password'))
        self.article.status='draft';self.article.save()
        with self.captureOnCommitCallbacks(execute=True):
            response=self.client.post('/admin/blog/article/', {'action':'publish','_selected_action':[self.article.pk]})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Notification.objects.filter(article=self.article).count(),2)


@override_settings(SECURE_SSL_REDIRECT=False, SUBSCRIPTIONS_ENABLED=True, MAIL_DELIVERY_MODE='remote', MAIL_WORKER_TOKEN='worker-test-key-with-at-least-32-characters')
class RemoteMailTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.worker_key = 'Bearer worker-test-key-with-at-least-32-characters'

    def worker(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.worker_key)

    def subscribe(self):
        return self.client.post('/api/v1/subscriptions/', {'name':'Remote reader', 'email':'remote@example.com'})

    def test_worker_requires_secret_and_rejects_get(self):
        self.assertEqual(self.client.post('/api/v1/mail-worker/claim/', {}).status_code,403)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer wrong')
        self.assertEqual(self.client.post('/api/v1/mail-worker/claim/', {}).status_code,403)
        self.worker()
        self.assertEqual(self.client.get('/api/v1/mail-worker/claim/').status_code,405)

    def test_queued_verification_and_single_lease(self):
        response=self.subscribe()
        self.assertEqual(response.status_code,202)
        self.assertEqual(response.json(),{'status':'verification_queued'})
        self.assertEqual(len(mail.outbox),0)
        self.worker()
        claimed=self.client.post('/api/v1/mail-worker/claim/', {})
        self.assertEqual(claimed['Cache-Control'],'no-store, private')
        job=claimed.json()['jobs'][0]
        self.assertEqual(job['kind'],'verification')
        self.assertEqual(self.client.post('/api/v1/mail-worker/claim/',{}).json()['jobs'],[])
        token=job['body'].split('#verify=')[1].split()[0]
        receipt={key:job[key] for key in ['kind','id','lease']}
        receipt['sent']=True
        self.assertEqual(self.client.post('/api/v1/mail-worker/ack/',receipt,format='json').status_code,200)
        login=SubscriberLogin.objects.get()
        self.assertEqual(login.delivery_token,'')
        self.assertIsNotNone(login.sent_at)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/v1/subscriptions/verify/',{'token':token}).status_code,200)

    def test_failed_delivery_retries_and_stale_ack_rejected(self):
        self.subscribe();self.worker()
        job=self.client.post('/api/v1/mail-worker/claim/',{}).json()['jobs'][0]
        receipt={key:job[key] for key in ['kind','id','lease']};receipt['sent']=False
        self.assertEqual(self.client.post('/api/v1/mail-worker/ack/',receipt,format='json').status_code,200)
        self.assertEqual(self.client.post('/api/v1/mail-worker/claim/',{}).json()['jobs'],[])
        SubscriberLogin.objects.update(next_attempt_at=timezone.now())
        retried=self.client.post('/api/v1/mail-worker/claim/',{}).json()['jobs'][0]
        self.assertNotEqual(job['lease'],retried['lease'])
        receipt['sent']=True
        self.assertEqual(self.client.post('/api/v1/mail-worker/ack/',receipt,format='json').status_code,409)

    def test_notifications_recheck_visibility_and_preferences(self):
        subscriber=Subscriber.objects.create(email='reader@example.com',name='Reader',active=True,verified_at=timezone.now())
        article=Article.objects.create(title='A',slug='a',status='published')
        collect_articles();subscriber.active=False;subscriber.save()
        self.worker()
        self.assertEqual(self.client.post('/api/v1/mail-worker/claim/',{}).json()['jobs'],[])
        self.assertTrue(Notification.objects.get().cancelled)

    def test_abandoned_claim_is_recovered(self):
        self.subscribe();self.worker()
        job=self.client.post('/api/v1/mail-worker/claim/',{}).json()['jobs'][0]
        SubscriberLogin.objects.update(claimed_at=timezone.now()-timedelta(minutes=11))
        retried=self.client.post('/api/v1/mail-worker/claim/',{}).json()['jobs'][0]
        self.assertEqual(job['id'],retried['id'])
        self.assertNotEqual(job['lease'],retried['lease'])
