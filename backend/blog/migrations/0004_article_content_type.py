from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('blog', '0003_bilingual_content')]

    operations = [
        migrations.AddField(
            model_name='article',
            name='content_type',
            field=models.CharField(
                choices=[('article', '文章'), ('project', '项目报告')],
                default='article',
                max_length=12,
            ),
        ),
        migrations.AddIndex(
            model_name='article',
            index=models.Index(
                fields=['content_type', 'status', 'published_at'],
                name='blog_articl_content_f2b8bf_idx',
            ),
        ),
    ]
