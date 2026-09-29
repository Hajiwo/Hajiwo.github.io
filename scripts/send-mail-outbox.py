"""Send leased mail jobs. Logs contain counts only, never recipients or tokens."""
import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(path, payload):
    base = os.environ['MAIL_API_BASE'].rstrip('/')
    if not base.startswith('https://'):
        raise ValueError('HTTPS required')
    req = Request(base + path, data=json.dumps(payload).encode(), method='POST', headers={
        'Authorization': 'Bearer ' + os.environ['MAIL_WORKER_TOKEN'], 'Content-Type':'application/json', 'Accept':'application/json'})
    with build_opener(NoRedirect).open(req, timeout=30) as response:
        return json.load(response)


def main():
    sent = failed = 0
    try:
        # Limit runtime and exposure; later runs continue any remaining backlog.
        for _ in range(5):
            jobs = api('/mail-worker/claim/', {})['jobs']
            if not jobs:
                break
            for job in jobs:
                delivered = False
                try:
                    message = EmailMessage()
                    message['From'] = os.environ['MAIL_FROM']
                    message['To'] = job['to']
                    message['Subject'] = job['subject']
                    message.set_content(job['body'])
                    with smtplib.SMTP(os.environ['MAIL_SMTP_HOST'], int(os.environ.get('MAIL_SMTP_PORT','587')), timeout=15) as smtp:
                        smtp.starttls(context=ssl.create_default_context())
                        smtp.login(os.environ['MAIL_SMTP_USER'], os.environ['MAIL_SMTP_PASSWORD'])
                        smtp.send_message(message)
                    delivered = True
                    sent += 1
                except Exception:
                    failed += 1
                api('/mail-worker/ack/', {key:job[key] for key in ('kind','id','lease')} | {'sent':delivered})
            if failed:
                break
    except Exception as exc:
        print(f'Mail worker unavailable ({type(exc).__name__}). Details withheld to protect recipients.')
        return 1
    print(f'Mail delivery: {sent} accepted by SMTP; {failed} failed.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
