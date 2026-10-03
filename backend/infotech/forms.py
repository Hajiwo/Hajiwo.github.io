from django import forms
from .models import Course, UsefulLink, Tip
from .i18n import text
class CourseForm(forms.ModelForm):
    capacity_limited = forms.TypedChoiceField(label='Capacity limited', choices=[('True','Yes'), ('False','No')], coerce=lambda value: value == 'True', initial=False)
    class Meta:
        model = Course
        fields = ['name','category','difficulty','exam_form','description','semester','capacity_limited']
        widgets = {'name':forms.TextInput(attrs={'autofocus':True}), 'description':forms.Textarea(attrs={'rows':4})}
    def __init__(self, *args, language='zh', **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language
        for field in self.fields.values():
            field.label = text(field.label, language)
            if hasattr(field, 'choices'):
                field.choices = [(value, text(label, language) if value != '' else ('请选择' if language == 'zh' else 'Select')) for value,label in field.choices]
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise forms.ValidationError(text('Enter a course name.', self.language))
        return name


class CardForm(forms.ModelForm):
    def __init__(self, *args, language='zh', **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.label = text(field.label, language)

class UsefulLinkForm(CardForm):
    url = forms.URLField(label='Website URL', max_length=2000, assume_scheme='https')
    class Meta:
        model = UsefulLink
        fields = ['name', 'url', 'description']
        widgets = {'name':forms.TextInput(attrs={'autofocus':True}), 'description':forms.Textarea(attrs={'rows':4})}
    def clean_url(self):
        url = self.cleaned_data['url']
        from urllib.parse import urlsplit
        if urlsplit(url).scheme not in ('http', 'https'):
            raise forms.ValidationError(text('Use an HTTP or HTTPS URL.', self.language))
        return url
    def __init__(self, *args, language='zh', **kwargs):
        self.language = language
        super().__init__(*args, language=language, **kwargs)

class TipForm(CardForm):
    class Meta:
        model = Tip
        fields = ['title', 'body']
        widgets = {'title':forms.TextInput(attrs={'autofocus':True}), 'body':forms.Textarea(attrs={'rows':8})}

