from django.test import TestCase, Client, override_settings
from django.urls import reverse
from .models import Course, UsefulLink, Tip
from django.db import connections
from django.contrib.auth import get_user_model
from django.utils import translation
from django.urls import resolve

@override_settings(INFOTECH_PASSWORD='infotech')
class CourseGuideTests(TestCase):
    databases = {'default', 'infotech'}
    def setUp(self):
        session = self.client.session
        session['infotech_language'] = 'en'
        session.save()
        self.data = dict(name='Test course', category='ee', difficulty='medium', exam_form='open', description='Student experience', semester='winter', capacity_limited='False')
    def enter(self):
        self.client.post(reverse('infotech:enter'), {'password':'infotech'})
    def test_gate_protects_all_routes(self):
        course=Course.objects.create(**self.data)
        for url in ['/infotech/', '/infotech/courses/add/', f'/infotech/courses/{course.pk}/edit/', '/infotech/section/links/', '/infotech/section/work/', '/infotech/section/tips/']:
            self.assertRedirects(self.client.get(url), reverse('infotech:enter'))
        response=self.client.post('/infotech/courses/add/',self.data)
        self.assertRedirects(response,reverse('infotech:enter'))
        self.assertEqual(Course.objects.count(),1)
    def test_password_and_lock(self):
        response=self.client.post(reverse('infotech:enter'),{'password':'wrong'})
        self.assertContains(response,'Password incorrect')
        self.assertNotIn('infotech_access',self.client.session)
        self.enter()
        self.assertTrue(self.client.session['infotech_access'])
        self.assertContains(self.client.get('/infotech/'),'Course Recommendation')
        self.assertEqual(self.client.get('/infotech/lock/').status_code,405)
        self.client.post('/infotech/lock/')
        self.assertRedirects(self.client.get('/infotech/'),'/infotech/enter/')
    def test_create_edit_and_filters(self):
        self.enter()
        self.assertRedirects(self.client.post('/infotech/courses/add/',self.data),'/infotech/')
        course=Course.objects.get()
        self.assertContains(self.client.get('/infotech/'),'Test course')
        self.assertContains(self.client.get('/infotech/?q=unmatched'),'No matching courses')
        self.assertContains(self.client.get('/infotech/?category=cs'),'No matching courses')
        self.assertContains(self.client.get('/infotech/?semester=summer'),'No matching courses')
        self.assertContains(self.client.get('/infotech/?q=experience&category=ee&semester=winter'),'Test course')
        self.assertRedirects(self.client.post(f'/infotech/courses/{course.pk}/edit/',{**self.data,'name':'Updated course','exam_form':'oral'}),'/infotech/')
        course.refresh_from_db()
        self.assertEqual(course.name,'Updated course')
        self.assertEqual(course.exam_form,'oral')
    def test_invalid_choices_and_missing_fields(self):
        self.enter()
        response=self.client.post('/infotech/courses/add/',{**self.data,'category':'invalid'})
        self.assertContains(response,'Select a valid choice')
        self.assertEqual(Course.objects.count(),0)
        response=self.client.post('/infotech/courses/add/',{'name':' '})
        self.assertContains(response,'This field is required')
        self.assertEqual(Course.objects.count(),0)
    def test_content_escaped_and_pages_not_cached(self):
        self.enter()
        Course.objects.create(**{**self.data,'description':'<script>alert(1)</script>'})
        response=self.client.get('/infotech/')
        self.assertContains(response,'&lt;script&gt;')
        self.assertNotContains(response,'<script>alert(1)</script>')
        self.assertIn('no-store',response.headers['Cache-Control'])
        self.assertEqual(self.client.get('/infotech/section/missing/').status_code,404)
    def test_csrf_enforced(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/infotech/enter/',{'password':'infotech'}).status_code,403)
        client.get('/infotech/enter/')
        token=client.cookies['csrftoken'].value
        self.assertEqual(client.post('/infotech/enter/',{'password':'infotech','csrfmiddlewaretoken':token}).status_code,302)
        self.assertEqual(client.post('/infotech/courses/add/',self.data).status_code,403)

    def test_chinese_default_and_language_switch(self):
        client=Client()
        self.assertContains(client.get('/infotech/enter/'), '密码')
        client.post('/infotech/enter/', {'password':'infotech'})
        self.assertContains(client.get('/infotech/'), '需要抢课')
        self.assertNotContains(client.get('/infotech/'), 'Find your next course')
        client.post('/infotech/language/', {'language':'en', 'next':'/infotech/?category=ee'})
        self.assertContains(client.get('/infotech/'), 'Capacity limited')
        self.assertContains(client.get('/infotech/courses/add/'), 'Capacity limited')
        response=client.post('/infotech/language/', {'language':'zh', 'next':'https://example.com'})
        self.assertRedirects(response, '/infotech/')
        self.assertContains(client.get('/infotech/courses/add/'), '需要抢课')
    def test_capacity_limited_persists(self):
        self.enter()
        self.client.post('/infotech/courses/add/', {**self.data, 'capacity_limited':'True'})
        course=Course.objects.get()
        self.assertTrue(course.capacity_limited)
        self.assertContains(self.client.get('/infotech/'), 'Yes')
        self.client.post(f'/infotech/courses/{course.pk}/edit/', {**self.data, 'capacity_limited':'False'})
        course.refresh_from_db()
        self.assertFalse(course.capacity_limited)
        self.assertContains(self.client.get('/infotech/'), 'No')

    def test_lock_preserves_blog_admin_login_and_language(self):
        user = get_user_model().objects.create_user(username='integration-admin', is_staff=True)
        self.client.force_login(user)
        session = self.client.session
        session['language'] = 'en'
        session.save()
        self.enter()
        self.client.post('/infotech/language/', {'language': 'zh', 'next': '/admin/'})
        self.client.post('/infotech/lock/')
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))
        self.assertEqual(self.client.session['language'], 'en')
        self.assertNotIn('infotech_access', self.client.session)

    def test_language_redirect_stays_within_infotech(self):
        self.assertRedirects(self.client.post('/infotech/language/', {
            'language': 'en', 'next': '/admin/',
        }), '/infotech/', fetch_redirect_response=False)
        self.assertRedirects(self.client.post('/infotech/language/', {
            'language': 'en', 'next': 'https://example.com/infotech/',
        }), '/infotech/', fetch_redirect_response=False)

    def test_database_and_routes_are_isolated(self):
        self.assertNotIn('courses_course', connections['default'].introspection.table_names())
        tables = connections['infotech'].introspection.table_names()
        self.assertIn('courses_course', tables)
        self.assertNotIn('blog_article', tables)
        self.assertEqual(resolve('/infotech/').namespace, 'infotech')
        self.assertEqual(resolve('/admin/').namespace, 'blog_admin')
        language = translation.get_language()
        self.client.get('/infotech/enter/')
        self.assertEqual(translation.get_language(), language)
        response = self.client.get('/api/v1/articles/')
        self.assertEqual(response.status_code, 200)

    @override_settings(INFOTECH_PASSWORD='')
    def test_missing_password_does_not_grant_access(self):
        self.assertEqual(self.client.post('/infotech/enter/', {'password': ''}).status_code, 503)
        self.assertNotIn('infotech_access', self.client.session)


@override_settings(INFOTECH_PASSWORD='infotech')
class CardTests(TestCase):
    databases = {'default', 'infotech'}
    def login(self):
        self.client.post('/infotech/enter/', {'password':'infotech'})
    def test_card_routes_protected(self):
        link = UsefulLink.objects.create(name='Test', url='https://example.com', description='Description')
        tip = Tip.objects.create(title='Title', body='Body')
        for section, item in [('links',link), ('tips',tip)]:
            for route in [f'/infotech/section/{section}/', f'/infotech/section/{section}/add/', f'/infotech/section/{section}/{item.pk}/edit/']:
                self.assertRedirects(self.client.get(route), '/infotech/enter/')
            self.assertRedirects(self.client.post(f'/infotech/section/{section}/add/', {}), '/infotech/enter/')
    def test_links_create_edit_and_url_validation(self):
        self.login()
        data = {'name':'CAMPUS', 'url':'https://example.com', 'description':'课程信息'}
        self.assertRedirects(self.client.post('/infotech/section/links/add/',data), '/infotech/section/links/')
        link = UsefulLink.objects.get()
        self.assertContains(self.client.get('/infotech/section/links/'), '课程信息')
        self.assertContains(self.client.get('/infotech/section/links/'), 'href="https://example.com"')
        self.assertRedirects(self.client.post(f'/infotech/section/links/{link.pk}/edit/',{**data, 'name':'Updated'}), '/infotech/section/links/')
        link.refresh_from_db()
        self.assertEqual(link.name,'Updated')
        for url in ['javascript:alert(1)', 'ftp://example.com', 'invalid']:
            self.client.post('/infotech/section/links/add/',{**data,'url':url})
        self.assertEqual(UsefulLink.objects.count(),1)
        self.client.post('/infotech/section/links/add/',{})
        self.assertEqual(UsefulLink.objects.count(),1)
    def test_tips_create_edit_escape_and_language(self):
        self.login()
        data={'title':'research project怎么找', 'body':'第一行\n第二行<script>alert(1)</script>'}
        self.assertRedirects(self.client.post('/infotech/section/tips/add/',data), '/infotech/section/tips/')
        tip=Tip.objects.get()
        response=self.client.get('/infotech/section/tips/')
        self.assertContains(response,'research project怎么找')
        self.assertContains(response,'&lt;script&gt;')
        self.assertContains(response,'<br>')
        self.assertRedirects(self.client.post(f'/infotech/section/tips/{tip.pk}/edit/',{**data,'body':'Updated body'}), '/infotech/section/tips/')
        tip.refresh_from_db()
        self.assertEqual(tip.body,'Updated body')
        self.client.post('/infotech/language/',{'language':'en'})
        self.assertContains(self.client.get('/infotech/section/tips/add/'),'Title')
        self.assertContains(self.client.get('/infotech/section/links/add/'),'Website URL')
        self.client.post('/infotech/section/tips/add/',{'title':' '})
        self.assertEqual(Tip.objects.count(),1)
    def test_work_removed_and_missing_card(self):
        self.login()
        self.assertNotContains(self.client.get('/infotech/'), '工作机会')
        self.assertEqual(self.client.get('/infotech/section/work/').status_code,404)
        self.assertEqual(self.client.get('/infotech/section/work/add/').status_code,404)
        self.assertEqual(self.client.get('/infotech/section/links/9999/edit/').status_code,404)
        self.assertEqual(self.client.get('/infotech/section/tips/9999/edit/').status_code,404)
