from django.conf import settings


def access_mode(request):
    return {'infotech_require_password': settings.INFOTECH_REQUIRE_PASSWORD}
