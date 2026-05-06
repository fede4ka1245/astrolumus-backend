from django.db import migrations


def update_contacts(apps, schema_editor):
    Info = apps.get_model('info', 'Info')
    # Update existing Info record or create one with correct contacts
    info = Info.objects.first()
    if info:
        info.email = 'deepsky.astrology@gmail.com'
        info.telegram = 'https://t.me/DeepSkySchoolBot'
        info.save()
    else:
        Info.objects.create(
            email='deepsky.astrology@gmail.com',
            telegram='https://t.me/DeepSkySchoolBot',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('info', '0009_alter_documents_description_alter_documents_title'),
    ]

    operations = [
        migrations.RunPython(update_contacts, migrations.RunPython.noop),
    ]
