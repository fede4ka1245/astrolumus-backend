from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advertising', '0007_tag_banner_date_from_banner_date_to_banner_tag'),
        ('bootcamp', '0014_advcoursecard_target_languages'),
    ]

    operations = [
        migrations.AddField(
            model_name='advcoursecard',
            name='localized_images',
            field=models.ManyToManyField(
                blank=True,
                related_name='adv_course_cards',
                to='advertising.bannerimage',
                verbose_name='Баннеры на разных языках',
            ),
        ),
        migrations.AlterModelOptions(
            name='advcoursecard',
            options={'verbose_name': 'Баннер', 'verbose_name_plural': 'Баннеры'},
        ),
    ]
