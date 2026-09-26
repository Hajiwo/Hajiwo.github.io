from django import forms
from django.utils import timezone
from django.utils.text import slugify

from .models import Article


class ArticleAdminForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'
        labels = {
            'title': '中文标题',
            'title_en': 'English title',
            'slug': 'URL 标识',
            'description': '中文简介',
            'description_en': 'English summary',
            'body': '中文正文',
            'body_en': 'English body',
            'series': '所属系列',
            'content_type': '内容类型',
            'status': '状态',
            'published_at': '发布时间',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '输入清晰、具体的文章标题'}),
            'title_en': forms.TextInput(attrs={'placeholder': 'Enter the English article title'}),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'maxlength': 500,
                'placeholder': '用于文章列表和搜索摘要，建议控制在 120 字以内',
            }),
            'description_en': forms.Textarea(attrs={
                'rows': 3,
                'maxlength': 500,
                'placeholder': 'English summary shown in the article list',
            }),
            'body': forms.Textarea(attrs={
                'rows': 28,
                'spellcheck': 'true',
                'placeholder': '# 从一个标题开始…',
            }),
            'body_en': forms.Textarea(attrs={
                'rows': 28,
                'spellcheck': 'true',
                'placeholder': '# Start with a heading…',
            }),
        }
        help_texts = {
            'slug': '文章 URL 中的唯一标识；留空时根据标题生成。',
            'description': '最多 500 个字符。',
            'description_en': 'Up to 500 characters.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False

    def clean_slug(self):
        supplied = self.cleaned_data.get('slug', '').strip()
        if supplied:
            return supplied
        generated = slugify(self.cleaned_data.get('title', ''))
        return generated or f'article-{timezone.now():%Y%m%d%H%M%S}'

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('status') == Article.Status.PUBLISHED:
            required_translations = {
                'title_en': '发布前请填写英文标题。',
                'description_en': '发布前请填写英文简介。',
                'body_en': '发布前请填写英文正文。',
            }
            for field, message in required_translations.items():
                if not str(cleaned_data.get(field) or '').strip():
                    self.add_error(field, message)
            series = cleaned_data.get('series')
            if series and not series.name_en.strip():
                self.add_error('series', '所选系列缺少英文名称，请先在“文章系列”中补充。')
        return cleaned_data
