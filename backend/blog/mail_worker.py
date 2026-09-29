"""Private, leased mail outbox for the trusted GitHub Actions sender."""
import uuid
from datetime import timedelta
from django.conf import settings
from django.db.models import Q, F
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from .models import SubscriberLogin, Notification
from .notifications import collect_articles, notification_message, verification_message


def authenticate_worker(request):
    expected = settings.MAIL_WORKER_TOKEN
    supplied = request.headers.get('Authorization', '')
    if (settings.MAIL_DELIVERY_MODE != 'remote' or not settings.SUBSCRIPTIONS_ENABLED
            or len(expected) < 32 or not constant_time_compare(supplied, f'Bearer {expected}')):
        raise PermissionDenied('Unavailable.')


def no_store(payload, status=200):
    response = Response(payload, status=status)
    response['Cache-Control'] = 'no-store, private'
    return response


@api_view(['POST'])
def claim(request):
    authenticate_worker(request)
    now = timezone.now()
    expired = Q(claimed_at__isnull=True) | Q(claimed_at__lt=now - timedelta(minutes=10))
    jobs = []
    # Erase unused authentication material after expiry.
    SubscriberLogin.objects.filter(expires_at__lte=now).exclude(delivery_token='').update(delivery_token='')
    for login in SubscriberLogin.objects.filter(expired, used_at__isnull=True, sent_at__isnull=True,
            expires_at__gt=now, next_attempt_at__lte=now).exclude(delivery_token='').select_related('subscriber').order_by('pk')[:20]:
        lease = uuid.uuid4()
        if not SubscriberLogin.objects.filter(expired, pk=login.pk, used_at__isnull=True, sent_at__isnull=True).update(
                claimed_at=now, lease_token=lease, attempts=F('attempts')+1, expires_at=now+timedelta(minutes=30)):
            continue
        subject, body = verification_message(login.delivery_token)
        jobs.append({'kind':'verification', 'id':login.pk, 'lease':str(lease), 'to':login.subscriber.email, 'subject':subject, 'body':body})
    collect_articles()
    for item in Notification.objects.filter(expired, sent_at__isnull=True, cancelled=False, next_attempt_at__lte=now).select_related(
            'subscriber', 'article', 'topic', 'comment', 'post')[:20-len(jobs)]:
        lease = uuid.uuid4()
        if not Notification.objects.filter(expired, pk=item.pk, sent_at__isnull=True, cancelled=False).update(
                claimed_at=now, lease_token=lease, attempts=F('attempts')+1):
            continue
        payload = notification_message(item)
        if not payload:
            Notification.objects.filter(pk=item.pk, lease_token=lease).update(cancelled=True, claimed_at=None, lease_token=None)
            continue
        subject, body = payload
        jobs.append({'kind':'notification', 'id':item.pk, 'lease':str(lease), 'to':item.subscriber.email, 'subject':subject, 'body':body})
    return no_store({'jobs':jobs})


@api_view(['POST'])
def acknowledge(request):
    authenticate_worker(request)
    kind = request.data.get('kind')
    if kind not in ['verification', 'notification'] or type(request.data.get('sent')) is not bool:
        raise ValidationError('Invalid receipt.')
    try:
        pk = int(request.data.get('id'))
        lease = uuid.UUID(str(request.data.get('lease')))
    except (TypeError, ValueError):
        raise ValidationError('Invalid receipt.')
    model = SubscriberLogin if kind == 'verification' else Notification
    item = model.objects.filter(pk=pk, lease_token=lease, sent_at__isnull=True).first()
    if not item:
        return no_store({'status':'stale_receipt'}, status=409)
    values = {'claimed_at':None, 'lease_token':None}
    if request.data['sent']:
        values.update(sent_at=timezone.now(), last_error='')
        if kind == 'verification':
            values['delivery_token'] = ''
    else:
        values.update(last_error='SMTP delivery failed', next_attempt_at=timezone.now()+timedelta(minutes=min(60, 2**min(item.attempts,6))))
    model.objects.filter(pk=pk, lease_token=lease, sent_at__isnull=True).update(**values)
    return no_store({'status':'recorded'})
