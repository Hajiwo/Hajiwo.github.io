from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('blog', '0007_notification_lease_token_subscriberlogin_attempts_and_more')]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='kind',
            field=models.CharField(choices=[
                ('welcome', '订阅成功'),
                ('articles', '新文章'),
                ('discussions', '讨论更新'),
                ('replies', '回复'),
            ], max_length=16),
        ),
    ]
