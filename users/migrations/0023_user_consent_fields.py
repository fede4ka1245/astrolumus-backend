from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_applanguage_user_app_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='consent_personal_data',
            field=models.BooleanField(default=False, verbose_name='Согласие на обработку персональных данных'),
        ),
        migrations.AddField(
            model_name='user',
            name='consent_marketing',
            field=models.BooleanField(default=False, verbose_name='Согласие на маркетинговую рассылку'),
        ),
        migrations.AddField(
            model_name='user',
            name='consent_marketing_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата согласия на рассылку'),
        ),
    ]
