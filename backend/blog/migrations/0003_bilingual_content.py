from django.db import migrations, models


def populate_known_series_translations(apps, schema_editor):
    Series = apps.get_model('blog', 'Series')
    translations = {
        '学习笔记': (
            'Study Notes',
            'Courses and resources worth revisiting, with notes from exploring computer science and AI.',
        ),
        '知乎': (
            'Zhihu Essays',
            'Essays originally published on Zhihu, collected here for easier reading.',
        ),
    }
    for name, (name_en, description_en) in translations.items():
        Series.objects.filter(name=name).update(name_en=name_en, description_en=description_en)


class Migration(migrations.Migration):
    dependencies = [('blog', '0002_model_verbose_names')]

    operations = [
        migrations.AddField(
            model_name='series',
            name='name_en',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='series',
            name='description_en',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='article',
            name='title_en',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='article',
            name='description_en',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='article',
            name='body_en',
            field=models.TextField(blank=True, help_text='English Markdown source; MDX and raw HTML are not executed.'),
        ),
        migrations.RunPython(populate_known_series_translations, migrations.RunPython.noop),
    ]
