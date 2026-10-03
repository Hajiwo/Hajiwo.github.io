from functools import wraps
from secrets import compare_digest
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.urls import reverse
from urllib.parse import urlsplit
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.db.models import Q
from .models import Course, UsefulLink, Tip
from .forms import CourseForm, UsefulLinkForm, TipForm
from .i18n import text
from django.utils.http import url_has_allowed_host_and_scheme

def protected(view):
    @wraps(view)
    @never_cache
    def wrapper(request, *args, **kwargs):
        if settings.INFOTECH_REQUIRE_PASSWORD and not request.session.get('infotech_access'):
            return redirect('infotech:enter')
        return view(request, *args, **kwargs)
    return wrapper

@never_cache
def enter(request):
    if not settings.INFOTECH_REQUIRE_PASSWORD:
        return redirect('infotech:courses')
    if request.session.get('infotech_access'):
        return redirect('infotech:courses')
    if not settings.INFOTECH_PASSWORD:
        return HttpResponse('InfoTech access is not configured.', status=503)
    error = ''
    if request.method == 'POST':
        if compare_digest(request.POST.get('password','').encode(), settings.INFOTECH_PASSWORD.encode()):
            request.session.cycle_key()
            request.session['infotech_access'] = True
            return redirect('infotech:courses')
        error = text('Password incorrect', request.session.get('infotech_language', 'zh'))
    return render(request, 'infotech/enter.html', {'error':error})

@require_POST
def lock(request):
    language = request.session.get('infotech_language', 'zh')
    request.session.pop('infotech_access', None)
    request.session['infotech_language'] = language
    return redirect('infotech:enter' if settings.INFOTECH_REQUIRE_PASSWORD else 'infotech:courses')

@protected
def course_list(request):
    courses = Course.objects.all()
    query = request.GET.get('q','').strip()
    category = request.GET.get('category','')
    semester = request.GET.get('semester','')
    if query:
        courses = courses.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category in Course.Category.values:
        courses = courses.filter(category=category)
    if semester in Course.Semester.values:
        courses = courses.filter(semester=semester)
    return render(request, 'infotech/courses.html', {'courses':courses,'total':Course.objects.count(),'query':query,'category':category,'semester':semester,'categories':Course.Category.choices,'semesters':Course.Semester.choices,'active':'courses'})

@protected
def course_form(request, pk=None):
    course = get_object_or_404(Course, pk=pk) if pk else None
    form = CourseForm(request.POST if request.method == 'POST' else None, instance=course, language=request.session.get('infotech_language', 'zh'))
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, text('Course updated' if course else 'Course added', request.session.get('infotech_language', 'zh')))
        return redirect('infotech:courses')
    return render(request, 'infotech/form.html', {'form':form,'editing':bool(course),'active':'courses'})

CARD_SECTIONS = {
    'links': (UsefulLink, UsefulLinkForm, 'Useful Links', 'Add link', 'Edit link'),
    'tips': (Tip, TipForm, 'Tips', 'Add tip', 'Edit tip'),
}

@protected
def section(request, section):
    if section not in CARD_SECTIONS:
        raise Http404
    model, _, title, add_title, _ = CARD_SECTIONS[section]
    return render(request, 'infotech/cards.html', {'items':model.objects.all(), 'title':title, 'add_title':add_title, 'active':section, 'section':section})

@protected
def card_form(request, section, pk=None):
    if section not in CARD_SECTIONS:
        raise Http404
    model, form_type, title, add_title, edit_title = CARD_SECTIONS[section]
    item = get_object_or_404(model, pk=pk) if pk else None
    form = form_type(request.POST if request.method == 'POST' else None, instance=item, language=request.session.get('infotech_language', 'zh'))
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('infotech:section', section=section)
    return render(request, 'infotech/card_form.html', {'form':form, 'title':edit_title if item else add_title, 'section_title':title, 'editing':bool(item), 'section':section, 'active':section})

@require_POST
def language(request):
    selected = request.POST.get('language')
    if selected in ('zh', 'en'):
        request.session['infotech_language'] = selected
    home = reverse('infotech:courses')
    target = request.POST.get('next', home)
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()) or not urlsplit(target).path.startswith(home):
        target = home
    return redirect(target)
