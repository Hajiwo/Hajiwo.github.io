from django.utils import translation


class GuideLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path_info.startswith('/infotech/'):
            return self.get_response(request)
        language = request.session.get('infotech_language', 'zh')
        with translation.override('zh-hans' if language == 'zh' else 'en'):
            return self.get_response(request)

