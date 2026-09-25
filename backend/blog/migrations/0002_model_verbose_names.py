from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('blog', '0001_initial')]

    operations = [
        migrations.AlterModelOptions(
            name='article',
            options={
                'ordering': ['-published_at', '-id'],
                'verbose_name': '文章',
                'verbose_name_plural': '文章',
            },
        ),
        migrations.AlterModelOptions(
            name='comment',
            options={
                'ordering': ['created_at', 'id'],
                'verbose_name': '评论',
                'verbose_name_plural': '评论',
            },
        ),
        migrations.AlterModelOptions(
            name='series',
            options={
                'ordering': ['order', 'name'],
                'verbose_name': '文章系列',
                'verbose_name_plural': '文章系列',
            },
        ),
    ]
